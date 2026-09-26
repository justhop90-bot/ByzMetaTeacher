"""Semantic adapters backed by the checked-in AIRef native command schema."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path

from .native_schema import NativeCommandRegistry, load_default_native_schema
from .engine_semantics import (
    EngineSemanticMappingRegistry,
    default_engine_semantic_mapping_registry,
)
from .native_hygiene import (
    AIRefProvenance,
    ConfidenceBasis,
    ConfidenceLevel,
    EvidenceKind,
    NativeContractCatalog,
    NativeGoalParameterRangeContract,
    NativeGoalSpanContract,
    NativeGoalStorageContract,
    NativeStorageClass,
    NativeStorageKind,
    NativeStorageUse,
    NativeWitness,
    NativeWitnessKind,
    PassConstraintScope,
    PassExecutionConstraint,
    PassFailureMode,
)



class NativeSupportState(str, Enum):
    NATIVE_KNOWN = "native-known"
    NATIVE_TYPED = "native-typed"
    SEMANTICALLY_ADAPTED = "semantically-adapted"
    ENGINE_SEMANTICS_MAPPED = "engine-semantics-mapped"
    EXECUTABLE_SAFE = "executable-safe"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class NativeSupportDiagnostic:
    command: str
    state: NativeSupportState
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class NativeSupportAssessment:
    command: str
    state: NativeSupportState
    message: str
    diagnostics: tuple[NativeSupportDiagnostic, ...]


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
    ):
        self._items = {p.name: p for p in primitives}
        self._native = native_registry
        self._semantic_mappings = semantic_mappings or default_engine_semantic_mapping_registry()
        self._native_contracts = native_contracts or default_native_contract_catalog()



    @property
    def native_contracts(self) -> NativeContractCatalog:
        return self._native_contracts

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
        diagnostics: list[NativeSupportDiagnostic] = []
        native = self.native(name)
        if native is None:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-SUPPORT-006",
                "error",
                "command is not present in the checked-in native schema",
            )
            return NativeSupportAssessment(
                command=name,
                state=NativeSupportState.UNSUPPORTED,
                message=diagnostic.message,
                diagnostics=(diagnostic,),
            )

        diagnostics.append(
            self._diagnostic(
                name,
                NativeSupportState.NATIVE_KNOWN,
                "NATIVE-SUPPORT-001",
                "info",
                "command is present in the checked-in native schema",
            )
        )

        if not self._native_typed(native):
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-SUPPORT-006",
                "error",
                "native metadata is not typed",
            )
            diagnostics.append(diagnostic)
            return NativeSupportAssessment(
                command=name,
                state=NativeSupportState.UNSUPPORTED,
                message=diagnostic.message,
                diagnostics=tuple(diagnostics),
            )

        diagnostics.append(
            self._diagnostic(
                name,
                NativeSupportState.NATIVE_TYPED,
                "NATIVE-SUPPORT-002",
                "info",
                "native command signature and parameter metadata are structurally typed",
            )
        )

        primitive = self.get(name)
        if primitive is None:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-SUPPORT-006",
                "error",
                "native command is known and typed but has no semantic adapter",
            )
            diagnostics.append(diagnostic)
            return NativeSupportAssessment(
                command=name,
                state=NativeSupportState.UNSUPPORTED,
                message=diagnostic.message,
                diagnostics=tuple(diagnostics),
            )

        diagnostics.append(
            self._diagnostic(
                name,
                NativeSupportState.SEMANTICALLY_ADAPTED,
                "NATIVE-SUPPORT-003",
                "info",
                "a semantic adapter is registered for the native command",
            )
        )

        try:
            self.validate_adapter_contract(primitive)
        except ValueError as exc:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-SUPPORT-006",
                "error",
                f"semantic adapter is not executable-safe: {exc}",
            )
            diagnostics.append(diagnostic)
            return NativeSupportAssessment(
                command=name,
                state=NativeSupportState.UNSUPPORTED,
                message=diagnostic.message,
                diagnostics=tuple(diagnostics),
            )

        if not primitive.engine_semantics_id:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-SUPPORT-006",
                "error",
                "native command is semantically adapted but has no engine semantic mapping",
            )
            diagnostics.append(diagnostic)
            return NativeSupportAssessment(
                command=name,
                state=NativeSupportState.UNSUPPORTED,
                message=diagnostic.message,
                diagnostics=tuple(diagnostics),
            )

        mapping_ok, mapping_message = self._semantic_mappings.validate_primitive(
            command=name,
            native_kind=native.command_type,
            identity=primitive.engine_semantics_id,
        )
        if not mapping_ok:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-SUPPORT-006",
                "error",
                mapping_message,
            )
            diagnostics.append(diagnostic)
            return NativeSupportAssessment(
                command=name,
                state=NativeSupportState.UNSUPPORTED,
                message=diagnostic.message,
                diagnostics=tuple(diagnostics),
            )

        try:
            self.validate_primitive_promotion(primitive, native)
        except (KeyError, ValueError) as exc:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-SUPPORT-006",
                "error",
                f"native primitive contract is not executable-safe: {exc}",
            )
            diagnostics.append(diagnostic)
            return NativeSupportAssessment(
                command=name,
                state=NativeSupportState.UNSUPPORTED,
                message=diagnostic.message,
                diagnostics=tuple(diagnostics),
            )

        diagnostics.append(
            self._diagnostic(
                name,
                NativeSupportState.ENGINE_SEMANTICS_MAPPED,
                "NATIVE-SUPPORT-004",
                "info",
                f"engine semantic mapping registered: {primitive.engine_semantics_id}",
            )
        )
        diagnostics.append(
            self._diagnostic(
                name,
                NativeSupportState.EXECUTABLE_SAFE,
                "NATIVE-SUPPORT-005",
                "info",
                "native signature, semantic adapter, and engine semantic mapping are executable-safe",
            )
        )
        return NativeSupportAssessment(
            command=name,
            state=NativeSupportState.EXECUTABLE_SAFE,
            message="command is executable-safe",
            diagnostics=tuple(diagnostics),
        )

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
        Primitive("building-type-count-total", "FACT", "OBSERVATION", 3, 3, completion_witness=False),
        Primitive("unit-type-count", "FACT", "OBSERVATION", 3, 3),
        Primitive("unit-type-count-total", "FACT", "OBSERVATION", 3, 3, completion_witness=False),
        Primitive("can-train", "FACT", "FEASIBILITY", 1, 1),
        Primitive("can-train-with-escrow", "FACT", "FEASIBILITY", 1, 1),
        Primitive("up-pending-objects", "FACT", "OBSERVATION", 4, 4, completion_witness=False),
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
    primitive_items = tuple(facts + actions)
    semantic_registry.validate_exact_executable_commands(
        tuple(item.name for item in primitive_items)
    )
    mapped_items = tuple(
        replace(
            item,
            engine_semantics_id=semantic_registry.for_command(item.name).identity,
        )
        for item in primitive_items
    )
    registry = PrimitiveRegistry(
        mapped_items,
        native_registry,
        semantic_mappings=semantic_registry,
        native_contracts=native_contracts,
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
        goal_storage_contracts=(
            NativeGoalStorageContract(
                identity="ordinary-persistent-goal-storage",
                minimum_id=1,
                maximum_id=512,
                provenance=_engine_provenance("airef:goal-storage"),
            ),
        ),
        goal_span_contracts=(
            NativeGoalSpanContract(
                identity="point-goal-span",
                storage_kind=NativeStorageKind.POINT_GOAL_SPAN,
                width=2,
                minimum_start=41,
                maximum_start=15998,
                provenance=_engine_provenance("airef:extended-goal-span-point"),
            ),
            NativeGoalSpanContract(
                identity="extended-4-goal-span",
                storage_kind=NativeStorageKind.SEARCH_STATE_GOAL_SPAN,
                width=4,
                minimum_start=41,
                maximum_start=15996,
                provenance=_engine_provenance("airef:extended-goal-span-4"),
            ),
            NativeGoalSpanContract(
                identity="cost-data-4-goal-span",
                storage_kind=NativeStorageKind.COST_DATA_GOAL_SPAN,
                width=4,
                minimum_start=41,
                maximum_start=15996,
                provenance=_engine_provenance("airef:extended-goal-span-4"),
            ),
            NativeGoalSpanContract(
                identity="guard-state-4-goal-span",
                storage_kind=NativeStorageKind.GUARD_STATE_GOAL_SPAN,
                width=4,
                minimum_start=41,
                maximum_start=15996,
                provenance=_engine_provenance("airef:extended-goal-span-4"),
            ),
        ),
        parameter_ranges=(
            NativeGoalParameterRangeContract(
                identity="goal-id-parameter-range",
                parameter_type="GoalId",
                minimum=1,
                maximum=16000,
                commands=("goal", "set-goal"),
                provenance=_engine_provenance("airef:goal-id-parameter-range"),
            ),
        ),
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
