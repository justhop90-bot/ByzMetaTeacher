"""Semantic adapters backed by the checked-in AIRef native command schema."""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from .native_schema import NativeCommandRegistry, load_default_native_schema
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..semantic.fact_registry import NativeFactRegistry
from .native_binder import (
    NativeSemanticBinder,
    NativeSupportAssessment,
    NativeSupportDiagnostic,
    NativeSupportState,
)
from .engine_semantics import (
    EngineSemanticMappingRegistry,
    default_engine_semantic_mapping_registry,
    default_duc_executable_commands,
    default_escrow_executable_commands,
    default_native_controller_executable_commands,
)
from .native_engine_effects import default_native_engine_effect_catalog
from ..ir.resource_control import NativeEscrowReleasePlan
from ..semantic.resource_control import validate_escrow_release_plan
from .native_hygiene import (
    AIRefProvenance,
    ConfidenceBasis,
    ConfidenceLevel,
    EvidenceKind,
    NativeContractCatalog,
    NativeStorageClass,
    NativeStorageKind,
    NativeStorageUse,
    NativeWitness,
    default_native_goal_parameter_ranges,
    default_native_goal_span_contracts,
    default_native_goal_storage_contracts,
    NativeWitnessKind,
    PassConstraintScope,
    PassExecutionConstraint,
    PassFailureMode,
)



@dataclass(frozen=True)
class Primitive:
    name: str
    kind: str
    role: str
    min_args: int
    max_args: int
    version: str = "DE"
    completion_witness: bool = True
    conflict_class: str | None = None
    engine_semantics_id: str | None = None
    native_witness_ids: tuple[str, ...] = ()
    native_storage_use_ids: tuple[str, ...] = ()
    native_pass_constraint_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "native_witness_ids",
            "native_storage_use_ids",
            "native_pass_constraint_ids",
        ):
            values = getattr(self, field_name)
            if len(values) != len(set(values)):
                raise ValueError(
                    f"{field_name} for primitive '{self.name}' must not contain duplicates"
                )

class PrimitiveRegistry:
    def __init__(
        self,
        primitives: tuple[Primitive, ...],
        native_registry: NativeCommandRegistry | None = None,
        semantic_mappings: EngineSemanticMappingRegistry | None = None,
        native_contracts: NativeContractCatalog | None = None,
        fact_registry: NativeFactRegistry | None = None,
    ):
        names = [primitive.name for primitive in primitives]
        if len(names) != len(set(names)):
            raise ValueError("duplicate primitive name")
        self._items = {primitive.name: primitive for primitive in primitives}
        self._native = native_registry
        self._semantic_mappings = semantic_mappings or default_engine_semantic_mapping_registry()
        self._native_contracts = native_contracts or default_native_contract_catalog()
        self._fact_registry = fact_registry



    @property
    def native_contracts(self) -> NativeContractCatalog:
        return self._native_contracts

    @property
    def fact_registry(self) -> NativeFactRegistry:
        if self._fact_registry is None:
            raise ValueError("native fact registry is not configured")
        return self._fact_registry

    def validate_primitive_promotion(self, primitive: Primitive, native) -> None:
        if primitive.kind != "ACTION":
            return
        if not primitive.native_witness_ids:
            raise ValueError(f"action primitive '{primitive.name}' has no native witness contract")
        if not primitive.native_storage_use_ids:
            raise ValueError(f"action primitive '{primitive.name}' has no native storage contract")
        for identity in primitive.native_witness_ids:
            try:
                witness = self._native_contracts.witness(identity)
            except KeyError as exc:
                raise ValueError(
                    f"no native witness contract '{identity}'"
                ) from exc
            if self.native(witness.primitive) is None:
                raise ValueError(f"native witness '{identity}' references unknown primitive '{witness.primitive}'")
            witness_adapter = self.get(witness.primitive)
            if witness_adapter is None or not witness_adapter.completion_witness:
                raise ValueError(f"native witness '{identity}' is not completion-capable")
            if witness.primitive == primitive.name:
                raise ValueError(f"native witness '{identity}' reuses action primitive '{primitive.name}'")
            if witness.kind is NativeWitnessKind.TIMER_STATE:
                raise ValueError(f"native witness '{identity}' cannot be timer state")
        for identity in primitive.native_storage_use_ids:
            try:
                use = self._native_contracts.storage(identity)
            except KeyError as exc:
                raise ValueError(
                    f"no native storage contract '{identity}'"
                ) from exc
            if use.request_purpose is None:
                raise ValueError(f"native storage use '{identity}' has no request purpose")
        for identity in primitive.native_pass_constraint_ids:
            try:
                constraint = self._native_contracts.pass_constraint(identity)
            except KeyError as exc:
                raise ValueError(
                    f"no native pass constraint '{identity}'"
                ) from exc
            if constraint.command != primitive.name:
                raise ValueError(
                    f"native pass constraint '{identity}' targets '{constraint.command}', not '{primitive.name}'"
                )
        declared_pass_constraints = set(primitive.native_pass_constraint_ids)
        for constraint in self._native_contracts.pass_constraints_for(primitive.name):
            if constraint.identity not in declared_pass_constraints:
                raise ValueError(
                    f"native pass constraint '{constraint.identity}' is not declared by '{primitive.name}'"
                )
            if constraint.requires_next_pass:
                raise ValueError(
                    f"native pass constraint '{constraint.identity}' requires next-pass lowering, which is not implemented"
                )
            if constraint.maximum_successes is not None and constraint.failure_mode is not None:
                if constraint.failure_mode is not PassFailureMode.NO_EFFECT:
                    raise ValueError(
                        f"native pass constraint '{constraint.identity}' uses unsupported failure mode "
                        f"'{constraint.failure_mode.value}'"
                    )

    def bind_duc_plan(self, plan):
        binder = NativeSemanticBinder(
            native_registry=self._native,
            semantic_mappings=self._semantic_mappings,
            native_contracts=self._native_contracts,
            adapter_lookup=self.get,
        )
        return binder.bind_duc_plan(plan)

    def bind_attack_plan(self, plan):
        binder = NativeSemanticBinder(
            native_registry=self._native,
            semantic_mappings=self._semantic_mappings,
            native_contracts=self._native_contracts,
            adapter_lookup=self.get,
        )
        return binder.bind_attack_plan(plan)

    def validate_escrow_release_plan(self, plan: NativeEscrowReleasePlan) -> None:
        if not isinstance(plan, NativeEscrowReleasePlan):
            raise TypeError("escrow_plan must be a NativeEscrowReleasePlan")
        report = validate_escrow_release_plan(plan)
        if not report.valid:
            summary = "; ".join(
                f"{error.code.value}: {error.message}" for error in report.errors
            )
            raise ValueError(f"escrow release plan validation failed: {summary}")
        binder = NativeSemanticBinder(
            native_registry=self._native,
            semantic_mappings=self._semantic_mappings,
            native_contracts=self._native_contracts,
            adapter_lookup=self.get,
        )
        bindings = binder.bind_escrow_plan(plan)
        binding_by_command = {binding.command: binding for binding in bindings}
        if set(plan.commands) != set(binding_by_command):
            raise ValueError(
                "escrow release plan contains a command without a dedicated native binding"
            )
        for operation in plan.operations:
            binding = binding_by_command[operation.command]
            if operation.resource not in binding.resource_domain:
                raise ValueError(
                    f"escrow release resource '{operation.resource}' is outside the "
                    f"native domain {binding.resource_domain}"
                )
            if binding.parameter_count != 1:
                raise ValueError(
                    "release-escrow dedicated native binding does not expose exactly one parameter"
                )

    def validate_attack_plan(self, plan) -> None:
        binder = NativeSemanticBinder(
            native_registry=self._native,
            semantic_mappings=self._semantic_mappings,
            native_contracts=self._native_contracts,
            adapter_lookup=self.get,
        )
        bindings = binder.bind_attack_plan(plan)
        binding_by_command = {binding.command: binding for binding in bindings}
        for rule in plan.rules:
            for expression in rule.facts:
                native = self.require_native(expression.head)
                if len(expression.args) != native.parameter_count:
                    raise ValueError(
                        f"attack lifecycle fact '{expression.head}' expects exactly "
                        f"{native.parameter_count} argument(s), got {len(expression.args)}"
                    )
                if native.command_type not in {"Fact", "Fact/Action"}:
                    raise ValueError(
                        f"attack lifecycle command '{expression.head}' is an Action and cannot be emitted as a Fact"
                    )
            for expression in rule.actions:
                binding = binding_by_command.get(expression.head)
                if binding is None:
                    raise ValueError(
                        f"attack lifecycle command '{expression.head}' was not promoted by the dedicated binder"
                    )
                if len(expression.args) != binding.parameter_count:
                    raise ValueError(
                        f"attack lifecycle command '{expression.head}' expects exactly "
                        f"{binding.parameter_count} argument(s), got {len(expression.args)}"
                    )
                native = self.require_native(expression.head)
                if native.command_type not in {"Action", "Fact/Action"}:
                    raise ValueError(
                        f"attack lifecycle command '{expression.head}' is a Fact and cannot be emitted as an Action"
                    )

    def validate_duc_plan(self, plan) -> None:
        binder = NativeSemanticBinder(
            native_registry=self._native,
            semantic_mappings=self._semantic_mappings,
            native_contracts=self._native_contracts,
            adapter_lookup=self.get,
        )
        duc_commands = set(self._native_contracts.duc_command_names)
        for rule in plan.rules:
            for expression in rule.facts:
                native = self.require_native(expression.head)
                if expression.head in duc_commands:
                    binding = binder.bind_duc_command(expression.head)
                    self.validate_native_signature(expression.head, len(expression.args))
                    native = self.require_native(expression.head)
                    if native.command_type not in {"Fact", "Fact/Action"}:
                        raise ValueError(
                            f"DUC rule fact '{expression.head}' is an Action and cannot be emitted as a Fact"
                        )
                    if len(expression.args) != binding.parameter_count:
                        raise ValueError(
                            f"DUC command '{expression.head}' expects exactly "
                            f"{binding.parameter_count} argument(s), got {len(expression.args)}"
                        )
                    continue
                self.validate_native_signature(expression.head, len(expression.args))
                if native.command_type not in {"Fact", "Fact/Action"}:
                    raise ValueError(
                        f"DUC rule fact '{expression.head}' is an Action and cannot be emitted as a Fact"
                    )
            for expression in rule.actions:
                if expression.head not in duc_commands:
                    raise ValueError(
                        f"DUC rule action '{expression.head}' is not a contracted DUC command"
                    )
                binding = binder.bind_duc_command(expression.head)
                if len(expression.args) != binding.parameter_count:
                    raise ValueError(
                        f"DUC command '{expression.head}' expects exactly "
                        f"{binding.parameter_count} argument(s), got {len(expression.args)}"
                    )
                native = self.require_native(expression.head)
                if native.command_type not in {"Action", "Fact/Action"}:
                    raise ValueError(
                        f"DUC command '{expression.head}' is a Fact and cannot be emitted as an Action"
                    )
        identities = tuple(rule.identity for rule in plan.rules)
        if identities != tuple(sorted(identities, key=lambda identity: next(
            rule.order for rule in plan.rules if rule.identity == identity
        ))):
            raise ValueError("DUC plan rule order is not deterministic")

    def validate_demand_lowering(self, demand, bindings) -> None:
        primitive = self.require(demand.action.expression.head)
        self.validate_primitive_promotion(primitive, self.require_native(primitive.name))
        requests = {demand.lifecycle.slot.request_id: demand.lifecycle.slot}
        if demand.action.arbitration_request is not None:
            requests[demand.action.arbitration_request.request_id] = demand.action.arbitration_request
        for identity in primitive.native_storage_use_ids:
            use = self._native_contracts.storage(identity)
            request = next((candidate for request_id, candidate in requests.items() if request_id.purpose == use.request_purpose), None)
            if request is None:
                raise ValueError(f"native storage use '{identity}' requires request purpose '{use.request_purpose}'")
            binding = bindings.binding_for(request.request_id)
            if binding.__class__.__name__ == "GoalSlot":
                start = end = binding.id.value
                kind = "GOAL_SLOT"
            elif binding.__class__.__name__ == "GoalSpan":
                start = binding.start.value
                end = start + binding.width - 1
                kind = "GOAL_SPAN"
            elif binding.__class__.__name__ == "StrategicNumberSlot":
                start = end = binding.id
                kind = "STRATEGIC_NUMBER"
            elif binding.__class__.__name__ == "TimerSlot":
                start = end = binding.id
                kind = "TIMER"
            else:
                raise ValueError(f"unsupported binding type '{type(binding).__name__}'")
            use.validate_binding_shape(binding_kind=kind, start=start, end=end)

    def pass_constraints_for(self, command: str) -> tuple[PassExecutionConstraint, ...]:
        return self._native_contracts.pass_constraints_for(command)
    @staticmethod
    def _native_typed(native) -> bool:
        if not native.version or native.command_type not in {"Fact", "Action"}:
            return False
        if native.parameter_count > 4:
            return False
        operator_parameters = {"compareOp", "mathOp", "typeOp"}
        for parameter in native.parameters:
            if not parameter.name:
                return False
            if parameter.name in operator_parameters:
                if not parameter.note:
                    return False
                continue
            if not parameter.type or not parameter.direction:
                return False
        return True

    @staticmethod
    def _diagnostic(
        command: str,
        state: NativeSupportState,
        code: str,
        severity: str,
        message: str,
    ) -> NativeSupportDiagnostic:
        return NativeSupportDiagnostic(
            command=command,
            state=state,
            code=code,
            severity=severity,
            message=message,
        )

    def assess_support(self, name: str) -> NativeSupportAssessment:
        binder = NativeSemanticBinder(
            native_registry=self._native,
            semantic_mappings=self._semantic_mappings,
            native_contracts=self._native_contracts,
            adapter_lookup=self.get,
        )
        return binder.assess(name)

    def support_state(self, name: str) -> NativeSupportState:
        return self.assess_support(name).state

    def support_diagnostics(self, names: tuple[str, ...] | None = None) -> tuple[NativeSupportDiagnostic, ...]:
        requested = names if names is not None else tuple(sorted(set(self._items) | set(self._native.names() if self._native else ())))
        assessments = tuple(self.assess_support(name) for name in requested)
        return tuple(
            diagnostic
            for assessment in sorted(assessments, key=lambda item: item.command)
            for diagnostic in assessment.diagnostics
        )

    def get(self, name: str) -> Primitive | None:
        return self._items.get(name)

    def require(self, name: str) -> Primitive:
        item = self.get(name)
        if item is None:
            raise KeyError(name)
        return item

    def native(self, name: str):
        return self._native.get(name) if self._native is not None else None

    def require_native(self, name: str):
        item = self.native(name)
        if item is None:
            raise KeyError(name)
        return item

    def validate_native_signature(self, name: str, arg_count: int) -> None:
        native = self.require_native(name)
        if arg_count != native.parameter_count:
            raise ValueError(
                f"native command '{name}' expects exactly "
                f"{native.parameter_count} argument(s), got {arg_count}"
            )

    def _resolve_production_fact(
        self,
        expression,
        *,
        semantic_family: str,
        expected_primitives: tuple[str, ...],
        target_label: str,
        target_id: int,
        expected_roles: tuple[str, ...],
    ):
        primitive_name = expression.head
        primitive = self.get(primitive_name)
        if primitive is None:
            raise ValueError(
                f"production {semantic_family} fact '{primitive_name}' is REJECTED: "
                "not a registered native fact"
            )
        native = self.native(primitive_name)
        if native is None:
            raise ValueError(
                f"production {semantic_family} fact '{primitive_name}' is REJECTED: "
                "no native schema entry"
            )
        if primitive_name not in expected_primitives:
            raise ValueError(
                f"production {semantic_family} fact '{primitive_name}' is REJECTED"
            )
        if primitive.role not in expected_roles or primitive.kind != "FACT":
            raise ValueError(
                f"production {semantic_family} fact '{primitive_name}' is REJECTED"
            )
        if native.command_type != "Fact":
            raise ValueError(
                f"production {semantic_family} fact '{primitive_name}' is REJECTED"
            )
        try:
            self.validate_native_signature(
                primitive_name,
                len(expression.args),
            )
            adapter = self.fact_registry.require(primitive_name)
        except (KeyError, ValueError) as exc:
            raise ValueError(
                f"production {semantic_family} fact '{primitive_name}' is REJECTED: "
                f"native resolution failed: {exc}"
            ) from exc
        semantic_id = primitive.engine_semantics_id
        if semantic_id is None:
            raise ValueError(
                f"production {semantic_family} fact '{primitive_name}' is REJECTED: "
                "no engine semantic mapping"
            )
        mapping = self._semantic_mappings.require(semantic_id)
        if mapping.native_command != primitive_name or mapping.native_kind != "Fact":
            raise ValueError(
                f"production {semantic_family} fact '{primitive_name}' is REJECTED: "
                "invalid engine semantic mapping"
            )
        if adapter.semantic_id != semantic_id:
            raise ValueError(
                f"production {semantic_family} fact '{primitive_name}' is REJECTED: "
                "mismatched fact semantic adapter"
            )
        target_index = 0 if primitive_name.startswith("can-train") else 1
        if (
            len(expression.args) <= target_index
            or str(expression.args[target_index]) != str(target_id)
        ):
            raise ValueError(
                f"production {semantic_family} fact '{primitive_name}' is REJECTED: "
                f"does not target {target_label} {target_id}"
            )
        return primitive_name, semantic_id

    def classify_production_target_admission(
        self,
        expression,
    ):
        from ..ir.production import ProductionFactDisposition

        if self.get(expression.head) is None:
            return ProductionFactDisposition.REJECTED
        if expression.head in {"can-train", "can-train-with-escrow"}:
            return ProductionFactDisposition.SUPPORTED
        return ProductionFactDisposition.REJECTED

    def classify_production_queue_protection(
        self,
        expression,
    ):
        from ..ir.production import ProductionFactDisposition

        if self.get(expression.head) is None:
            return ProductionFactDisposition.REJECTED
        if expression.head == "up-pending-objects":
            return ProductionFactDisposition.SUPPORTED
        if expression.head in {
            "unit-type-count-total",
            "building-type-count",
        }:
            return ProductionFactDisposition.OPEN
        return ProductionFactDisposition.REJECTED

    def resolve_production_target_admission(
        self,
        expression,
        *,
        native_unit_id: int,
    ):
        from ..ir.production import (
            ProductionFactDisposition,
            ProductionTargetAdmission,
        )

        primitive = self.get(expression.head)
        disposition = self.classify_production_target_admission(expression)
        if primitive is None:
            raise ValueError(
                f"production target-admission fact '{expression.head}' is REJECTED: "
                "not a registered native fact"
            )
        if disposition is not ProductionFactDisposition.SUPPORTED:
            raise ValueError(
                f"production target-admission fact '{expression.head}' is REJECTED"
            )
        primitive_name, semantic_id = self._resolve_production_fact(
            expression,
            semantic_family="target-admission",
            expected_primitives=("can-train", "can-train-with-escrow"),
            target_label="UnitId",
            target_id=native_unit_id,
            expected_roles=("FEASIBILITY",),
        )
        return ProductionTargetAdmission(
            disposition=ProductionFactDisposition.SUPPORTED,
            primitive=primitive_name,
            expression=expression,
            native_unit_id=native_unit_id,
            semantic_id=semantic_id,
        )

    def resolve_production_queue_protection(
        self,
        pending_fact,
        *,
        native_unit_id: int,
        queue_state=None,
        provider_state=None,
    ):
        from ..ir.production import (
            ProductionFactDisposition,
            ProductionQueueProtection,
        )

        self._resolve_production_fact(
            pending_fact,
            semantic_family="queue-protection",
            expected_primitives=("up-pending-objects",),
            target_label="UnitId",
            target_id=native_unit_id,
            expected_roles=("OBSERVATION",),
        )

        if queue_state is not None:
            disposition = self.classify_production_queue_protection(queue_state)
            if disposition is ProductionFactDisposition.OPEN:
                raise ValueError(
                    f"production queue-protection queue-state observation is OPEN: "
                    f"'{queue_state.head}' queue-capacity semantics are unresolved"
                )
            raise ValueError(
                f"production queue-protection queue-state fact "
                f"'{queue_state.head}' is REJECTED"
            )

        if provider_state is not None:
            disposition = self.classify_production_queue_protection(provider_state)
            if disposition is ProductionFactDisposition.OPEN:
                raise ValueError(
                    f"production queue-protection provider-state observation is OPEN: "
                    f"'{provider_state.head}' provider-idle semantics are unresolved"
                )
            raise ValueError(
                f"production queue-protection provider-state fact "
                f"'{provider_state.head}' is REJECTED"
            )

        return ProductionQueueProtection(
            disposition=ProductionFactDisposition.SUPPORTED,
            pending_fact=pending_fact,
            native_unit_id=native_unit_id,
        )

    def _resolve_production_observation(
        self,
        expression,
        *,
        observation_name: str,
        expected_primitive: str,
        target_label: str,
        target_id: int,
    ):
        primitive_name = expression.head
        primitive = self.get(primitive_name)
        if primitive is None:
            raise ValueError(
                f"production {observation_name} observation "
                f"'{primitive_name}' is not a registered native fact"
            )
        native = self.native(primitive_name)
        if native is None:
            raise ValueError(
                f"production {observation_name} observation "
                f"'{primitive_name}' has no native schema entry"
            )
        if primitive_name != expected_primitive:
            raise ValueError(
                f"production {observation_name} observation must use "
                f"{expected_primitive}"
            )
        if primitive.kind != "FACT" or primitive.role != "OBSERVATION":
            raise ValueError(
                f"production {observation_name} observation '{primitive_name}' "
                "is not an observation Fact"
            )
        if native.command_type != "Fact":
            raise ValueError(
                f"production {observation_name} observation '{primitive_name}' "
                "is not backed by a native Fact"
            )
        try:
            self.validate_native_signature(
                primitive_name,
                len(expression.args),
            )
            adapter = self.fact_registry.require(primitive_name)
        except KeyError as exc:
            raise ValueError(
                f"production {observation_name} observation "
                f"'{primitive_name}' has no registered native fact adapter"
            ) from exc
        except ValueError as exc:
            raise ValueError(
                f"production {observation_name} observation "
                f"'{primitive_name}' has invalid native signature: {exc}"
            ) from exc
        semantic_id = primitive.engine_semantics_id
        if semantic_id is None:
            raise ValueError(
                f"production {observation_name} observation "
                f"'{primitive_name}' has no engine semantic mapping"
            )
        mapping = self._semantic_mappings.require(semantic_id)
        if mapping.native_command != primitive_name or mapping.native_kind != "Fact":
            raise ValueError(
                f"production {observation_name} observation "
                f"'{primitive_name}' has an invalid engine semantic mapping"
            )
        if adapter.semantic_id != semantic_id:
            raise ValueError(
                f"production {observation_name} observation "
                f"'{primitive_name}' has a mismatched fact semantic adapter"
            )
        if (
            not expression.args
            or str(expression.args[0]) != str(target_id)
        ):
            raise ValueError(
                f"production {observation_name} observation "
                f"does not target {target_label} {target_id}"
            )
        return primitive_name, semantic_id


    def resolve_production_queue_capacity_control_evidence(self, expression):
        from ..ir.production import (
            ProductionFactDisposition,
            ProductionQueueCapacityControlEvidence,
        )
        from .strategic_number_catalog import default_strategic_number_catalog

        if expression.head != "up-compare-sn":
            raise ValueError(
                f"production queue-capacity control evidence must use up-compare-sn"
            )
        primitive = self.get(expression.head)
        if primitive is None:
            raise ValueError(
                f"production queue-capacity control evidence '{expression.head}' "
                "is REJECTED: not a registered native fact"
            )
        self.validate_native_signature(expression.head, len(expression.args))
        native = self.require_native(expression.head)
        if native.command_type not in {"Fact", "Fact/Action"}:
            raise ValueError(
                f"production queue-capacity control evidence '{expression.head}' "
                "is REJECTED: native command is not a fact"
            )
        if len(expression.args) != 3:
            raise ValueError(
                "production queue-capacity control evidence requires "
                "SnId, compareOp, and value"
            )

        catalog = default_strategic_number_catalog()
        expected_name = "sn-enable-training-queue"
        expected_id = 264
        if catalog.record_name(expected_id) != expected_name:
            raise ValueError(
                "production queue-capacity control evidence is REJECTED: "
                "pinned Strategic Number catalog does not identify SN 264 "
                "as sn-enable-training-queue"
            )

        target = str(expression.args[0])
        if target not in {expected_name, str(expected_id)}:
            raise ValueError(
                "production queue-capacity control evidence is REJECTED: "
                "source does not target SN 264"
            )
        if str(expression.args[1]) != "==":
            raise ValueError(
                "production queue-capacity control evidence must use exact equality"
            )
        try:
            additional_slots = int(str(expression.args[2]), 10)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "production queue-capacity control evidence value must be an integer"
            ) from exc
        if not 0 <= additional_slots <= 15:
            raise ValueError(
                "production queue-capacity control evidence additional queue "
                "slots must be in 0..15"
            )

        canonical_expression = expression.__class__(
            source=(
                f"({expression.head} {expected_id} == {additional_slots})"
            ),
            head=expression.head,
            args=(str(expected_id), "==", str(additional_slots)),
            location=expression.location,
        )
        return ProductionQueueCapacityControlEvidence(
            disposition=ProductionFactDisposition.OPEN,
            expression=canonical_expression,
            native_strategic_number_id=expected_id,
            configured_additional_queue_slots=additional_slots,
            documented_total_capacity=additional_slots + 1,
            semantic_id="controller.production.queue-capacity.sn264",
        )

    def classify_production_queue_capacity_evidence(self, expression):
        from ..ir.production import ProductionFactDisposition

        if self.get(expression.head) is None:
            return ProductionFactDisposition.REJECTED
        if expression.head == "unit-type-count-total":
            return ProductionFactDisposition.OPEN
        return ProductionFactDisposition.REJECTED

    def resolve_production_queue_capacity_evidence(
        self,
        expression,
        *,
        native_unit_id: int,
    ):
        from ..ir.production import (
            ProductionFactDisposition,
            ProductionQueueCapacityEvidence,
        )

        disposition = self.classify_production_queue_capacity_evidence(expression)
        if self.get(expression.head) is None:
            raise ValueError(
                f"production queue-capacity evidence '{expression.head}' is REJECTED: "
                "not a registered native fact"
            )
        if disposition is not ProductionFactDisposition.OPEN:
            raise ValueError(
                f"production queue-capacity evidence '{expression.head}' is REJECTED"
            )
        _, semantic_id = self._resolve_production_observation(
            expression,
            observation_name="queue-capacity evidence",
            expected_primitive="unit-type-count-total",
            target_label="UnitId",
            target_id=native_unit_id,
        )
        return ProductionQueueCapacityEvidence(
            disposition=ProductionFactDisposition.OPEN,
            expression=expression,
            native_unit_id=native_unit_id,
            source_semantic_id=semantic_id,
        )

    def classify_production_provider_availability_evidence(self, expression):
        from ..ir.production import ProductionFactDisposition

        if self.get(expression.head) is None:
            return ProductionFactDisposition.REJECTED
        if expression.head == "building-type-count":
            return ProductionFactDisposition.OPEN
        return ProductionFactDisposition.REJECTED

    def resolve_production_provider_availability_evidence(
        self,
        expression,
        *,
        native_building_id: int,
    ):
        from ..ir.production import (
            ProductionFactDisposition,
            ProductionProviderAvailabilityEvidence,
        )

        disposition = self.classify_production_provider_availability_evidence(
            expression
        )
        if self.get(expression.head) is None:
            raise ValueError(
                f"production provider-availability evidence '{expression.head}' "
                "is REJECTED: not a registered native fact"
            )
        if disposition is not ProductionFactDisposition.OPEN:
            raise ValueError(
                f"production provider-availability evidence '{expression.head}' "
                "is REJECTED"
            )
        _, semantic_id = self._resolve_production_observation(
            expression,
            observation_name="provider-availability evidence",
            expected_primitive="building-type-count",
            target_label="BuildingId",
            target_id=native_building_id,
        )
        return ProductionProviderAvailabilityEvidence(
            disposition=ProductionFactDisposition.OPEN,
            expression=expression,
            native_building_id=native_building_id,
            source_semantic_id=semantic_id,
        )

    def resolve_production_provider_readiness(
        self,
        expression,
        *,
        native_unit_id: int,
    ):
        from ..ir.production import (
            ProductionFactDisposition,
            ProductionProviderReadinessEvidence,
        )

        primitive = self.get(expression.head)
        if primitive is None:
            raise ValueError(
                f"production provider-readiness fact '{expression.head}' is REJECTED: "
                "not a registered native fact"
            )
        if expression.head != "up-train-site-ready":
            raise ValueError(
                f"production provider-readiness fact '{expression.head}' "
                "must use up-train-site-ready"
            )
        native = self.native(expression.head)
        if native is None or native.command_type != "Fact":
            raise ValueError(
                "production provider-readiness fact 'up-train-site-ready' "
                "has no native Fact schema entry"
            )
        if primitive.kind != "FACT" or primitive.role != "ADMISSIBILITY":
            raise ValueError(
                "production provider-readiness fact 'up-train-site-ready' "
                "must be an ADMISSIBILITY Fact"
            )
        self.validate_native_signature(expression.head, len(expression.args))
        if len(expression.args) != 2:
            raise ValueError(
                "production provider-readiness fact requires typeOp and UnitId"
            )
        if str(expression.args[0]) != "c:":
            raise ValueError(
                "production provider-readiness fact must use literal c:"
            )
        target = str(expression.args[1])
        if target not in {str(native_unit_id)}:
            try:
                from ..semantic.native_unit_catalog import resolve_unit_id
                resolved = resolve_unit_id(target)
            except (ImportError, KeyError, TypeError, ValueError):
                resolved = None
            if resolved != native_unit_id:
                raise ValueError(
                    f"production provider-readiness fact does not target UnitId "
                    f"{native_unit_id}"
                )
        semantic_id = self._semantic_mappings.require(
            "admissibility.train.site-ready"
        ).identity
        adapter = self.fact_registry.require(expression.head)
        if adapter.semantic_id != semantic_id:
            raise ValueError(
                "production provider-readiness fact has mismatched semantic adapter"
            )
        canonical = expression.__class__(
            source=f"(up-train-site-ready c: {native_unit_id})",
            head="up-train-site-ready",
            args=("c:", str(native_unit_id)),
            location=expression.location,
        )
        return ProductionProviderReadinessEvidence(
            disposition=ProductionFactDisposition.OPEN,
            expression=canonical,
            native_unit_id=native_unit_id,
            semantic_id=semantic_id,
        )

    def resolve_production_queue_state(
        self,
        expression,
        *,
        native_unit_id: int,
    ):
        from ..ir.production import ProductionQueueStateObservation

        primitive, semantic_id = self._resolve_production_observation(
            expression,
            observation_name="queue-state",
            expected_primitive="unit-type-count-total",
            target_label="UnitId",
            target_id=native_unit_id,
        )
        return ProductionQueueStateObservation(
            primitive=primitive,
            expression=expression,
            native_unit_id=native_unit_id,
            semantic_id=semantic_id,
        )

    def resolve_production_provider_state(
        self,
        expression,
        *,
        native_building_id: int,
    ):
        from ..ir.production import ProductionProviderStateObservation

        primitive, semantic_id = self._resolve_production_observation(
            expression,
            observation_name="provider-state",
            expected_primitive="building-type-count",
            target_label="BuildingId",
            target_id=native_building_id,
        )
        return ProductionProviderStateObservation(
            primitive=primitive,
            expression=expression,
            native_building_id=native_building_id,
            semantic_id=semantic_id,
        )

    def validate_adapter_contract(self, primitive: Primitive) -> None:
        native = self.require_native(primitive.name)
        expected = "Action" if primitive.kind == "ACTION" else "Fact"
        if native.command_type != expected:
            raise ValueError(
                f"semantic adapter kind mismatch for '{primitive.name}': "
                f"adapter={primitive.kind}, native={native.command_type}"
            )
        if not (primitive.min_args <= native.parameter_count <= primitive.max_args):
            raise ValueError(
                f"semantic adapter arity mismatch for '{primitive.name}': "
                f"native={native.parameter_count}, "
                f"semantic={primitive.min_args}..{primitive.max_args}"
            )

    def normalize_fact(
        self,
        name: str,
        args,
        *,
        provenance: tuple[AIRefProvenance, ...] | None = None,
    ):
        return self.fact_registry.normalize(
            name,
            args,
            provenance=provenance,
        )

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._items))

def default_de_registry(schema_path: Path | None = None) -> PrimitiveRegistry:
    facts = [
        Primitive("current-age", "FACT", "OBSERVATION", 2, 2),
        Primitive("food-amount", "FACT", "OBSERVATION", 2, 2),
        Primitive("wood-amount", "FACT", "OBSERVATION", 2, 2),
        Primitive("gold-amount", "FACT", "OBSERVATION", 2, 2),
        Primitive("stone-amount", "FACT", "OBSERVATION", 2, 2),
        Primitive("players-unit-type-count", "FACT", "OBSERVATION", 4, 4),
        Primitive("players-building-type-count", "FACT", "OBSERVATION", 4, 4),
        Primitive("game-time", "FACT", "TIMING", 2, 2, completion_witness=False),
        Primitive("dropsite-min-distance", "FACT", "OBSERVATION", 3, 3, completion_witness=False),
        Primitive("building-available", "FACT", "ADMISSIBILITY", 1, 1),
        Primitive("can-afford-building", "FACT", "RESOURCE_ARBITRATION", 1, 1),
        Primitive("can-build", "FACT", "FEASIBILITY", 1, 1),
        Primitive("can-build-with-escrow", "FACT", "FEASIBILITY", 1, 1),
        Primitive("building-type-count", "FACT", "OBSERVATION", 3, 3),
        Primitive("up-train-site-ready", "FACT", "ADMISSIBILITY", 2, 2),
        Primitive("building-type-count-total", "FACT", "OBSERVATION", 3, 3, completion_witness=False),
        Primitive("unit-type-count", "FACT", "OBSERVATION", 3, 3),
        Primitive("unit-type-count-total", "FACT", "OBSERVATION", 3, 3, completion_witness=False),
        Primitive("up-research-status", "FACT", "OBSERVATION", 4, 4, completion_witness=False),
        Primitive("can-train", "FACT", "FEASIBILITY", 1, 1),
        Primitive("can-train-with-escrow", "FACT", "FEASIBILITY", 1, 1),
        Primitive("up-pending-objects", "FACT", "OBSERVATION", 4, 4, completion_witness=False),
        Primitive("up-pending-placement", "FACT", "OBSERVATION", 2, 2, completion_witness=False),
        Primitive("up-compare-sn", "FACT", "PERSISTENT_STATE", 3, 3, completion_witness=False),
        Primitive("research-available", "FACT", "ADMISSIBILITY", 1, 1),
        Primitive("can-afford-research", "FACT", "RESOURCE_ARBITRATION", 1, 1),
        Primitive("can-research", "FACT", "FEASIBILITY", 1, 1),
        Primitive("can-research-with-escrow", "FACT", "FEASIBILITY", 1, 1),
        Primitive("research-completed", "FACT", "WITNESS", 1, 1, completion_witness=True),
    ]
    actions = [
        Primitive(
            "build",
            "ACTION",
            "ACTION",
            1,
            1,
            completion_witness=False,
            conflict_class="BUILD_PASS_SINGLETON",
            native_witness_ids=("build-completion-witness",),
            native_storage_use_ids=("lifecycle-goal-storage", "build-action-claim-storage"),
            native_pass_constraint_ids=("build-pass-singleton",),
        ),
        Primitive(
            "train", "ACTION", "ACTION", 1, 1,
            completion_witness=False,
            native_witness_ids=("train-completion-witness",),
            native_storage_use_ids=("lifecycle-goal-storage",),
        ),
        Primitive(
            "research", "ACTION", "ACTION", 1, 1,
            completion_witness=False,
            native_witness_ids=("research-completion-witness",),
            native_storage_use_ids=("lifecycle-goal-storage",),
        ),
    ]
    native_registry = (
        load_default_native_schema()
        if schema_path is None
        else NativeCommandRegistry.from_path(schema_path)
    )
    semantic_registry = default_engine_semantic_mapping_registry()
    native_contracts = default_native_contract_catalog()
    default_native_engine_effect_catalog().validate_native_registry(native_registry)
    primitive_items = tuple(facts + actions)
    semantic_registry.validate_exact_executable_commands(
        default_duc_executable_commands()
        + tuple(item.name for item in primitive_items)
        + default_escrow_executable_commands()
        + default_native_controller_executable_commands()
    )
    mapped_items = tuple(
        replace(
            item,
            engine_semantics_id=semantic_registry.for_command(item.name).identity,
        )
        for item in primitive_items
    )
    from ..semantic.fact_registry import NativeFactRegistry

    fact_registry = NativeFactRegistry.from_primitives(
        mapped_items,
        native_registry,
        semantic_registry,
    )
    registry = PrimitiveRegistry(
        mapped_items,
        native_registry,
        semantic_mappings=semantic_registry,
        native_contracts=native_contracts,
        fact_registry=fact_registry,
    )
    for primitive in mapped_items:
        registry.validate_adapter_contract(primitive)
    return registry

def _engine_provenance(citation_id: str) -> tuple[AIRefProvenance, ...]:
    return (
        AIRefProvenance(
            evidence_kind=EvidenceKind.DOCUMENTED_FACT,
            confidence=ConfidenceLevel.HIGH,
            confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
            citation_id=citation_id,
        ),
    )


def default_native_contract_catalog() -> NativeContractCatalog:
    return NativeContractCatalog(
        goal_storage_contracts=default_native_goal_storage_contracts(),
        goal_span_contracts=default_native_goal_span_contracts(),
        parameter_ranges=default_native_goal_parameter_ranges(),
        witnesses=(
            NativeWitness(
                identity="build-completion-witness",
                kind=NativeWitnessKind.OBJECT_COUNT,
                primitive="building-type-count",
                subject="ARG0",
                comparator=">=",
                value=1,
                provenance=_engine_provenance("airef:building-type-count"),
            ),
            NativeWitness(
                identity="train-completion-witness",
                kind=NativeWitnessKind.UNIT_COUNT,
                primitive="unit-type-count",
                subject="ARG0",
                comparator=">=",
                value=1,
                provenance=_engine_provenance("airef:unit-type-count"),
            ),
            NativeWitness(
                identity="research-completion-witness",
                kind=NativeWitnessKind.RESEARCH_STATUS,
                primitive="research-completed",
                subject="ARG0",
                state="completed",
                provenance=_engine_provenance("airef:research-completed"),
            ),
        ),
        storage_uses=(
            NativeStorageUse(
                identity="lifecycle-goal-storage",
                storage_class=NativeStorageClass.PERSISTENT_SCALAR,
                kind=NativeStorageKind.GOAL,
                request_purpose="lifecycle",
                symbolic=True,
                access="READ_WRITE",
                contract_id="ordinary-persistent-goal-storage",
                provenance=_engine_provenance("airef:goal-storage"),
            ),
            NativeStorageUse(
                identity="build-action-claim-storage",
                storage_class=NativeStorageClass.PERSISTENT_SCALAR,
                kind=NativeStorageKind.GOAL,
                request_purpose="action-claim:BUILD_PASS_SINGLETON",
                symbolic=True,
                access="READ_WRITE",
                contract_id="ordinary-persistent-goal-storage",
                provenance=_engine_provenance("airef:goal-storage"),
            ),
        ),
        pass_constraints=(
            PassExecutionConstraint(
                identity="build-pass-singleton",
                command="build",
                scope=PassConstraintScope.RULE_PASS,
                maximum_successes=1,
                failure_mode=PassFailureMode.NO_EFFECT,
                provenance=_engine_provenance("airef:build-pass-limit"),
            ),
        ),
    )
