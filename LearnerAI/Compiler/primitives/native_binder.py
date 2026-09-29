"""Bind native AoE2 command metadata to executable semantic contracts.

The binder is deliberately client-agnostic. It knows only native command metadata,
semantic adapters, engine-semantic mappings, native witnesses/storage contracts,
and pass constraints. Strategy clients consume the resulting bindings; they do
not define them.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from ..ir.native_attack import AttackLifecycleObservation
from ..ir.resource_control import (
    NATIVE_ESCROW_RELEASE_COMMAND,
    NATIVE_ESCROW_RELEASE_RESOURCES,
)
from ..semantic.native_controller import (
    NativeControlSurfaceKind,
    default_native_controller_catalog,
)
from .engine_semantics import EngineSemanticMappingStatus
from .native_engine_effects import (
    NativeEngineEffectCatalog,
    default_native_engine_effect_catalog,
)


class NativeSupportState(str, Enum):
    NATIVE_KNOWN = "native-known"
    NATIVE_TYPED = "native-typed"
    SEMANTICALLY_ADAPTED = "semantically-adapted"
    ENGINE_SEMANTICS_MAPPED = "engine-semantics-mapped"
    EXECUTABLE_SAFE = "executable-safe"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class NativeAttackSemanticBinding:
    command: str
    native_version: str
    native_kind: str
    parameter_count: int
    controller_id: str
    surface_identity: str
    semantic_mapping_id: str
    support_state: NativeSupportState
    completion_state: AttackLifecycleObservation
    evidence_sources: tuple[str, ...]


@dataclass(frozen=True)
class NativeDucSemanticBinding:
    command: str
    native_version: str
    native_kind: str
    parameter_count: int
    semantic_mapping_id: str
    mapping_status: EngineSemanticMappingStatus
    evidence_class: str
    evidence_sources: tuple[str, ...]
    support_state: NativeSupportState
    integer_range: tuple[int, int] | None = None


@dataclass(frozen=True)
class NativeOutputSemanticBinding:
    command: str
    native_version: str
    native_kind: str
    parameter_count: int
    semantic_mapping_id: str
    mapping_status: EngineSemanticMappingStatus
    evidence_class: str
    evidence_sources: tuple[str, ...]
    support_state: NativeSupportState


@dataclass(frozen=True)
class NativeEscrowSemanticBinding:
    command: str
    native_version: str
    native_kind: str
    parameter_count: int
    parameter_name: str
    parameter_type: str
    parameter_direction: str
    resource_domain: tuple[str, ...]
    semantic_mapping_id: str
    mapping_status: EngineSemanticMappingStatus
    evidence_class: str
    evidence_sources: tuple[str, ...]
    support_state: NativeSupportState


@dataclass(frozen=True)
class NativeSupportDiagnostic:
    command: str
    state: NativeSupportState
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class NativeSemanticBinding:
    command: str
    native_version: str
    native_kind: str
    parameter_count: int
    adapter_kind: str
    adapter_role: str
    adapter_name: str
    semantic_mapping_id: str
    mapping_status: EngineSemanticMappingStatus
    evidence_class: str
    evidence_sources: tuple[str, ...]
    native_witness_ids: tuple[str, ...]
    native_storage_use_ids: tuple[str, ...]
    native_pass_constraint_ids: tuple[str, ...]
    support_state: NativeSupportState


@dataclass(frozen=True)
class NativeSupportAssessment:
    command: str
    state: NativeSupportState
    message: str
    diagnostics: tuple[NativeSupportDiagnostic, ...]
    binding: NativeSemanticBinding | None = None


class NativeSemanticBinder:
    """Resolve one native command into a checked semantic binding."""

    _OPERATOR_PARAMETERS = frozenset({"compareOp", "mathOp", "typeOp"})

    def __init__(
        self,
        *,
        native_registry,
        semantic_mappings,
        native_contracts,
        adapter_lookup: Callable[[str], object | None],
        engine_effects: NativeEngineEffectCatalog | None = None,
    ) -> None:
        self.native_registry = native_registry
        self.semantic_mappings = semantic_mappings
        self.native_contracts = native_contracts
        self.adapter_lookup = adapter_lookup
        self.engine_effects = engine_effects or default_native_engine_effect_catalog()

    @classmethod
    def _native_typed(cls, native) -> bool:
        if not native.version or native.command_type not in {"Fact", "Action", "Fact/Action"}:
            return False
        if native.parameter_count > 4:
            return False
        for parameter in native.parameters:
            if not parameter.name:
                return False
            if parameter.name in cls._OPERATOR_PARAMETERS:
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

    def _validate_native_contracts(self, primitive, native) -> None:
        if primitive.kind != "ACTION":
            return
        if not primitive.native_witness_ids:
            raise ValueError(
                f"action primitive '{primitive.name}' has no native witness contract"
            )
        if not primitive.native_storage_use_ids:
            raise ValueError(
                f"action primitive '{primitive.name}' has no native storage contract"
            )

        for identity in primitive.native_witness_ids:
            try:
                witness = self.native_contracts.witness(identity)
            except KeyError as exc:
                raise ValueError(
                    f"no native witness contract '{identity}'"
                ) from exc
            witness_adapter = self.adapter_lookup(witness.primitive)
            if witness_adapter is None:
                raise ValueError(
                    f"native witness '{identity}' references unknown primitive "
                    f"'{witness.primitive}'"
                )
            if not getattr(witness_adapter, "completion_witness", False):
                raise ValueError(
                    f"native witness '{identity}' is not completion-capable"
                )
            if witness.primitive == primitive.name:
                raise ValueError(
                    f"native witness '{identity}' reuses action primitive "
                    f"'{primitive.name}'"
                )
            from .native_hygiene import NativeWitnessKind

            if witness.kind is NativeWitnessKind.TIMER_STATE:
                raise ValueError(
                    f"native witness '{identity}' cannot be timer state"
                )

        for identity in primitive.native_storage_use_ids:
            try:
                use = self.native_contracts.storage(identity)
            except KeyError as exc:
                raise ValueError(
                    f"no native storage contract '{identity}'"
                ) from exc
            if use.request_purpose is None:
                raise ValueError(
                    f"native storage use '{identity}' has no request purpose"
                )

        declared = set(primitive.native_pass_constraint_ids)
        for identity in primitive.native_pass_constraint_ids:
            try:
                constraint = self.native_contracts.pass_constraint(identity)
            except KeyError as exc:
                raise ValueError(
                    f"no native pass constraint '{identity}'"
                ) from exc
            if constraint.command != primitive.name:
                raise ValueError(
                    f"native pass constraint '{identity}' targets "
                    f"'{constraint.command}', not '{primitive.name}'"
                )

        from .native_hygiene import PassFailureMode

        for constraint in self.native_contracts.pass_constraints_for(primitive.name):
            if constraint.identity not in declared:
                raise ValueError(
                    f"native pass constraint '{constraint.identity}' is not "
                    f"declared by '{primitive.name}'"
                )
            if constraint.requires_next_pass:
                raise ValueError(
                    f"native pass constraint '{constraint.identity}' requires "
                    "next-pass lowering, which is not implemented"
                )
            if (
                constraint.maximum_successes is not None
                and constraint.failure_mode is not None
                and constraint.failure_mode is not PassFailureMode.NO_EFFECT
            ):
                raise ValueError(
                    f"native pass constraint '{constraint.identity}' uses "
                    f"unsupported failure mode "
                    f"'{constraint.failure_mode.value}'"
                )

    def _binding(self, name: str, native, primitive, mapping) -> NativeSemanticBinding:
        return NativeSemanticBinding(
            command=name,
            native_version=native.version,
            native_kind=native.command_type,
            parameter_count=native.parameter_count,
            adapter_kind=primitive.kind,
            adapter_role=primitive.role,
            adapter_name=primitive.name,
            semantic_mapping_id=mapping.identity,
            mapping_status=mapping.status,
            evidence_class=mapping.evidence_class,
            evidence_sources=tuple(mapping.evidence_sources),
            native_witness_ids=tuple(primitive.native_witness_ids),
            native_storage_use_ids=tuple(primitive.native_storage_use_ids),
            native_pass_constraint_ids=tuple(primitive.native_pass_constraint_ids),
            support_state=NativeSupportState.EXECUTABLE_SAFE,
        )

    def assess(self, name: str) -> NativeSupportAssessment:
        diagnostics: list[NativeSupportDiagnostic] = []
        native = self.native_registry.get(name)
        if native is None:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-SUPPORT-006",
                "error",
                "command is not present in the checked-in native schema",
            )
            return NativeSupportAssessment(
                name,
                NativeSupportState.UNSUPPORTED,
                diagnostic.message,
                (diagnostic,),
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
                name,
                NativeSupportState.UNSUPPORTED,
                diagnostic.message,
                tuple(diagnostics),
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

        primitive = self.adapter_lookup(name)
        if primitive is None:
            engine_effect = self.engine_effects.get(name)
            if engine_effect is not None:
                effect_ok, effect_message = self.engine_effects.validate_effect(
                    name,
                    self.native_registry,
                )
                if not effect_ok:
                    diagnostic = self._diagnostic(
                        name,
                        NativeSupportState.UNSUPPORTED,
                        "NATIVE-SUPPORT-006",
                        "error",
                        effect_message,
                    )
                    diagnostics.append(diagnostic)
                    return NativeSupportAssessment(
                        name,
                        NativeSupportState.UNSUPPORTED,
                        diagnostic.message,
                        tuple(diagnostics),
                    )
                diagnostic = self._diagnostic(
                    name,
                    NativeSupportState.ENGINE_SEMANTICS_MAPPED,
                    "NATIVE-SUPPORT-004",
                    "info",
                    f"native engine effect contract registered: {engine_effect.command}",
                )
                diagnostics.append(diagnostic)
                return NativeSupportAssessment(
                    name,
                    NativeSupportState.ENGINE_SEMANTICS_MAPPED,
                    "native command has an explicit engine-state/control effect contract",
                    tuple(diagnostics),
                    None,
                )

            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-SUPPORT-006",
                "error",
                "native command is known and typed but has no semantic adapter",
            )
            diagnostics.append(diagnostic)
            return NativeSupportAssessment(
                name,
                NativeSupportState.UNSUPPORTED,
                diagnostic.message,
                tuple(diagnostics),
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

        expected_kind = "Action" if primitive.kind == "ACTION" else "Fact"
        if native.command_type != expected_kind:
            message = (
                f"semantic adapter kind mismatch for '{name}': "
                f"adapter={primitive.kind}, native={native.command_type}"
            )
            diagnostic = self._diagnostic(
                name, NativeSupportState.UNSUPPORTED,
                "NATIVE-SUPPORT-006", "error", message,
            )
            diagnostics.append(diagnostic)
            return NativeSupportAssessment(
                name, NativeSupportState.UNSUPPORTED, message, tuple(diagnostics)
            )

        if not (primitive.min_args <= native.parameter_count <= primitive.max_args):
            message = (
                f"semantic adapter arity mismatch for '{name}': "
                f"native={native.parameter_count}, "
                f"semantic={primitive.min_args}..{primitive.max_args}"
            )
            diagnostic = self._diagnostic(
                name, NativeSupportState.UNSUPPORTED,
                "NATIVE-SUPPORT-006", "error", message,
            )
            diagnostics.append(diagnostic)
            return NativeSupportAssessment(
                name, NativeSupportState.UNSUPPORTED, message, tuple(diagnostics)
            )

        if not primitive.engine_semantics_id:
            message = (
                "native command is semantically adapted but has no engine "
                "semantic mapping"
            )
            diagnostic = self._diagnostic(
                name, NativeSupportState.UNSUPPORTED,
                "NATIVE-SUPPORT-006", "error", message,
            )
            diagnostics.append(diagnostic)
            return NativeSupportAssessment(
                name, NativeSupportState.UNSUPPORTED, message, tuple(diagnostics)
            )

        mapping = self.semantic_mappings.get(primitive.engine_semantics_id)
        if mapping is None:
            message = (
                f"engine semantic mapping '{primitive.engine_semantics_id}' "
                "is not registered"
            )
            diagnostic = self._diagnostic(
                name, NativeSupportState.UNSUPPORTED,
                "NATIVE-SUPPORT-006", "error", message,
            )
            diagnostics.append(diagnostic)
            return NativeSupportAssessment(
                name, NativeSupportState.UNSUPPORTED, message, tuple(diagnostics)
            )

        mapping_ok, mapping_message = self.semantic_mappings.validate_primitive(
            command=name,
            native_kind=native.command_type,
            identity=primitive.engine_semantics_id,
        )
        if not mapping_ok:
            diagnostic = self._diagnostic(
                name, NativeSupportState.UNSUPPORTED,
                "NATIVE-SUPPORT-006", "error", mapping_message,
            )
            diagnostics.append(diagnostic)
            return NativeSupportAssessment(
                name, NativeSupportState.UNSUPPORTED, mapping_message, tuple(diagnostics)
            )

        try:
            self._validate_native_contracts(primitive, native)
        except (KeyError, ValueError) as exc:
            message = f"native primitive contract is not executable-safe: {exc}"
            diagnostic = self._diagnostic(
                name, NativeSupportState.UNSUPPORTED,
                "NATIVE-SUPPORT-006", "error", message,
            )
            diagnostics.append(diagnostic)
            return NativeSupportAssessment(
                name, NativeSupportState.UNSUPPORTED, message, tuple(diagnostics)
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
        binding = self._binding(name, native, primitive, mapping)
        final = self._diagnostic(
            name,
            NativeSupportState.EXECUTABLE_SAFE,
            "NATIVE-SUPPORT-005",
            "info",
            "native signature, semantic adapter, and engine semantic mapping are executable-safe",
        )
        diagnostics.append(final)
        return NativeSupportAssessment(
            name,
            NativeSupportState.EXECUTABLE_SAFE,
            "command is executable-safe",
            tuple(diagnostics),
            binding,
        )

    def assess_escrow_command(self, name: str) -> NativeSupportAssessment:
        if name not in {
            NATIVE_ESCROW_RELEASE_COMMAND,
            NATIVE_ESCROW_POLICY_COMMAND,
        }:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-ESCROW-006",
                "error",
                f"escrow command '{name}' is not supported by the promoted native escrow slices",
            )
            return NativeSupportAssessment(name, NativeSupportState.UNSUPPORTED, diagnostic.message, (diagnostic,))

        native = self.native_registry.get(name)
        if native is None:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-ESCROW-006",
                "error",
                f"{name} is not present in the checked-in native schema",
            )
            return NativeSupportAssessment(name, NativeSupportState.UNSUPPORTED, diagnostic.message, (diagnostic,))

        if not self._native_typed(native):
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-ESCROW-006",
                "error",
                f"{name} native metadata is not typed",
            )
            return NativeSupportAssessment(name, NativeSupportState.UNSUPPORTED, diagnostic.message, (diagnostic,))

        if native.command_type != "Action":
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-ESCROW-006",
                "error",
                f"{name} must be an Action, native schema reports '{native.command_type}'",
            )
            return NativeSupportAssessment(name, NativeSupportState.UNSUPPORTED, diagnostic.message, (diagnostic,))

        expected_count = 1 if name == NATIVE_ESCROW_RELEASE_COMMAND else 2
        if native.parameter_count != expected_count or len(native.parameters) != expected_count:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-ESCROW-006",
                "error",
                f"{name} requires exactly {expected_count} native parameter(s)",
            )
            return NativeSupportAssessment(name, NativeSupportState.UNSUPPORTED, diagnostic.message, (diagnostic,))

        first = native.parameters[0]
        if (
            first.name != "Resource"
            or first.type != "Const"
            or first.direction != "in"
        ):
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-ESCROW-006",
                "error",
                f"{name} requires an input parameter named Resource with type Const",
            )
            return NativeSupportAssessment(name, NativeSupportState.UNSUPPORTED, diagnostic.message, (diagnostic,))

        integer_range = None
        if name == NATIVE_ESCROW_POLICY_COMMAND:
            second = native.parameters[1]
            if (
                second.name != "Value"
                or second.type != "Const"
                or second.direction != "in"
            ):
                diagnostic = self._diagnostic(
                    name,
                    NativeSupportState.UNSUPPORTED,
                    "NATIVE-ESCROW-006",
                    "error",
                    "set-escrow-percentage requires an input parameter named Value with type Const",
                )
                return NativeSupportAssessment(name, NativeSupportState.UNSUPPORTED, diagnostic.message, (diagnostic,))
            integer_range = (0, 100)

        mapping = self.semantic_mappings.for_command(name)
        if mapping is None:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-ESCROW-006",
                "error",
                f"{name} has no contracted engine semantic mapping",
            )
            return NativeSupportAssessment(name, NativeSupportState.UNSUPPORTED, diagnostic.message, (diagnostic,))

        mapping_ok, mapping_message = self.semantic_mappings.validate_primitive(
            command=name,
            native_kind=native.command_type,
            identity=mapping.identity,
        )
        expected_mapping = (
            "escrow.execution.release"
            if name == NATIVE_ESCROW_RELEASE_COMMAND
            else "escrow.execution.set-percentage"
        )
        if not mapping_ok or mapping.identity != expected_mapping:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-ESCROW-006",
                "error",
                mapping_message if not mapping_ok else (
                    f"{name} is mapped to an unsupported semantic contract"
                ),
            )
            return NativeSupportAssessment(name, NativeSupportState.UNSUPPORTED, diagnostic.message, (diagnostic,))

        binding = NativeEscrowSemanticBinding(
            command=name,
            native_version=native.version,
            native_kind=native.command_type,
            parameter_count=native.parameter_count,
            parameter_name=first.name,
            parameter_type=first.type,
            parameter_direction=first.direction,
            resource_domain=(
                tuple(NATIVE_ESCROW_RELEASE_RESOURCES)
                if name == NATIVE_ESCROW_RELEASE_COMMAND
                else tuple(NATIVE_ESCROW_POLICY_RESOURCES)
            ),
            semantic_mapping_id=mapping.identity,
            mapping_status=mapping.status,
            evidence_class=mapping.evidence_class,
            evidence_sources=tuple(mapping.evidence_sources),
            support_state=NativeSupportState.EXECUTABLE_SAFE,
            integer_range=integer_range,
        )
        code = (
            "NATIVE-ESCROW-005"
            if name == NATIVE_ESCROW_RELEASE_COMMAND
            else "NATIVE-ESCROW-007"
        )
        message = (
            "release-escrow is executable-safe for the promoted release-only slice"
            if name == NATIVE_ESCROW_RELEASE_COMMAND
            else "set-escrow-percentage is executable-safe for explicit policy mutation"
        )
        diagnostic = self._diagnostic(
            name,
            NativeSupportState.EXECUTABLE_SAFE,
            code,
            "info",
            message,
        )
        return NativeSupportAssessment(
            name,
            NativeSupportState.EXECUTABLE_SAFE,
            message,
            (diagnostic,),
            binding=None,
        )

    def bind_escrow_command(self, name: str) -> NativeEscrowSemanticBinding:
        assessment = self.assess_escrow_command(name)
        if assessment.state is not NativeSupportState.EXECUTABLE_SAFE:
            raise ValueError(assessment.message)
        mapping = self.semantic_mappings.for_command(name)
        native = self.native_registry.get(name)
        assert mapping is not None and native is not None
        parameter = native.parameters[0]
        return NativeEscrowSemanticBinding(
            command=name,
            native_version=native.version,
            native_kind=native.command_type,
            parameter_count=native.parameter_count,
            parameter_name=parameter.name,
            parameter_type=parameter.type,
            parameter_direction=parameter.direction,
            resource_domain=(
                tuple(NATIVE_ESCROW_RELEASE_RESOURCES)
                if name == NATIVE_ESCROW_RELEASE_COMMAND
                else tuple(NATIVE_ESCROW_POLICY_RESOURCES)
            ),
            semantic_mapping_id=mapping.identity,
            mapping_status=mapping.status,
            evidence_class=mapping.evidence_class,
            evidence_sources=tuple(mapping.evidence_sources),
            support_state=NativeSupportState.EXECUTABLE_SAFE,
            integer_range=(0, 100) if name == NATIVE_ESCROW_POLICY_COMMAND else None,
        )

    def bind_escrow_plan(self, plan) -> tuple[NativeEscrowSemanticBinding, ...]:
        bindings = tuple(
            self.bind_escrow_command(command)
            for command in plan.commands
        )
        return tuple(sorted(bindings, key=lambda item: item.command))

    def assess_attack_command(self, name: str) -> NativeSupportAssessment:
        if name != "attack-now":
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-ATTACK-006",
                "error",
                f"attack lifecycle command '{name}' is not supported by the native attack lifecycle slice",
            )
            return NativeSupportAssessment(
                name,
                NativeSupportState.UNSUPPORTED,
                diagnostic.message,
                (diagnostic,),
            )

        native = self.native_registry.get(name)
        if native is None:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-ATTACK-006",
                "error",
                "attack lifecycle command is not present in the checked-in native schema",
            )
            return NativeSupportAssessment(
                name,
                NativeSupportState.UNSUPPORTED,
                diagnostic.message,
                (diagnostic,),
            )

        if not self._native_typed(native):
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-ATTACK-006",
                "error",
                "attack lifecycle native metadata is not typed",
            )
            return NativeSupportAssessment(
                name,
                NativeSupportState.UNSUPPORTED,
                diagnostic.message,
                (diagnostic,),
            )

        if native.parameter_count != 0:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-ATTACK-006",
                "error",
                f"attack lifecycle command 'attack-now' expects exactly 0 argument(s), "
                f"native schema reports {native.parameter_count}",
            )
            return NativeSupportAssessment(
                name,
                NativeSupportState.UNSUPPORTED,
                diagnostic.message,
                (diagnostic,),
            )

        if native.command_type != "Action":
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-ATTACK-006",
                "error",
                f"attack lifecycle command 'attack-now' must be an Action, "
                f"native schema reports '{native.command_type}'",
            )
            return NativeSupportAssessment(
                name,
                NativeSupportState.UNSUPPORTED,
                diagnostic.message,
                (diagnostic,),
            )

        catalog = default_native_controller_catalog()
        try:
            surface = catalog.resolve_surface(
                NativeControlSurfaceKind.COMMAND,
                name,
            )
            controller = catalog.controller(surface.controller_id)
        except KeyError as exc:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-ATTACK-006",
                "error",
                f"attack lifecycle ownership lookup failed for 'attack-now': {exc.args[0]}",
            )
            return NativeSupportAssessment(
                name,
                NativeSupportState.UNSUPPORTED,
                diagnostic.message,
                (diagnostic,),
            )

        if controller.identity != "attack-group-control":
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-ATTACK-006",
                "error",
                f"attack-now is owned by unexpected controller '{controller.identity}'",
            )
            return NativeSupportAssessment(
                name,
                NativeSupportState.UNSUPPORTED,
                diagnostic.message,
                (diagnostic,),
            )

        mapping = self.semantic_mappings.for_command(name)
        if mapping is None:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-ATTACK-006",
                "error",
                "attack lifecycle command has no contracted engine semantic mapping",
            )
            return NativeSupportAssessment(
                name,
                NativeSupportState.UNSUPPORTED,
                diagnostic.message,
                (diagnostic,),
            )

        mapping_ok, mapping_message = self.semantic_mappings.validate_primitive(
            command=name,
            native_kind=native.command_type,
            identity=mapping.identity,
        )
        if not mapping_ok or mapping.identity != "attack.execution.issue":
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-ATTACK-006",
                "error",
                mapping_message
                if not mapping_ok
                else "attack-now is mapped to an unsupported semantic contract",
            )
            return NativeSupportAssessment(
                name,
                NativeSupportState.UNSUPPORTED,
                diagnostic.message,
                (diagnostic,),
            )

        diagnostic = self._diagnostic(
            name,
            NativeSupportState.EXECUTABLE_SAFE,
            "NATIVE-ATTACK-005",
            "info",
            "attack-now has native schema, controller ownership, exact arity, and a contracted issue-only semantic mapping",
        )
        binding = NativeAttackSemanticBinding(
            command=name,
            native_version=native.version,
            native_kind=native.command_type,
            parameter_count=native.parameter_count,
            controller_id=controller.identity,
            surface_identity=surface.identity,
            semantic_mapping_id=mapping.identity,
            support_state=NativeSupportState.EXECUTABLE_SAFE,
            completion_state=AttackLifecycleObservation.COMPLETION_UNOBSERVED,
            evidence_sources=tuple(mapping.evidence_sources),
        )
        return NativeSupportAssessment(
            name,
            NativeSupportState.EXECUTABLE_SAFE,
            "attack-now is executable-safe for issue-only lifecycle lowering",
            (diagnostic,),
            binding=None,
        )

    def bind_attack_command(self, name: str) -> NativeAttackSemanticBinding:
        assessment = self.assess_attack_command(name)
        if assessment.state is not NativeSupportState.EXECUTABLE_SAFE:
            raise ValueError(assessment.message)
        native = self.native_registry.get(name)
        mapping = self.semantic_mappings.for_command(name)
        catalog = default_native_controller_catalog()
        assert native is not None and mapping is not None
        surface = catalog.resolve_surface(NativeControlSurfaceKind.COMMAND, name)
        controller = catalog.controller(surface.controller_id)
        return NativeAttackSemanticBinding(
            command=name,
            native_version=native.version,
            native_kind=native.command_type,
            parameter_count=native.parameter_count,
            controller_id=controller.identity,
            surface_identity=surface.identity,
            semantic_mapping_id=mapping.identity,
            support_state=NativeSupportState.EXECUTABLE_SAFE,
            completion_state=AttackLifecycleObservation.COMPLETION_UNOBSERVED,
            evidence_sources=tuple(mapping.evidence_sources),
        )

    def bind_attack_plan(self, plan) -> tuple[NativeAttackSemanticBinding, ...]:
        bindings: list[NativeAttackSemanticBinding] = []
        for rule in plan.rules:
            for expression in rule.actions:
                bindings.append(self.bind_attack_command(expression.head))
        return tuple(
            sorted(
                bindings,
                key=lambda item: (item.command, item.controller_id, item.surface_identity),
            )
        )

    def assess_native_output_command(self, name: str) -> NativeSupportAssessment:
        native = self.native_registry.get(name)
        if native is None:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-OUTPUT-006",
                "error",
                "native output command is not present in the checked-in native schema",
            )
            return NativeSupportAssessment(
                name,
                NativeSupportState.UNSUPPORTED,
                diagnostic.message,
                (diagnostic,),
            )
        if not self._native_typed(native):
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-OUTPUT-006",
                "error",
                "native output command metadata is not typed",
            )
            return NativeSupportAssessment(
                name,
                NativeSupportState.UNSUPPORTED,
                diagnostic.message,
                (diagnostic,),
            )
        try:
            self.native_contracts.native_output_goal(name)
        except KeyError:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-OUTPUT-006",
                "error",
                "native output command has no typed Goal output contract",
            )
            return NativeSupportAssessment(
                name,
                NativeSupportState.UNSUPPORTED,
                diagnostic.message,
                (diagnostic,),
            )
        mapping = self.semantic_mappings.for_command(name)
        if mapping is None:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-OUTPUT-006",
                "error",
                "native output command has no contracted engine semantic mapping",
            )
            return NativeSupportAssessment(
                name,
                NativeSupportState.UNSUPPORTED,
                diagnostic.message,
                (diagnostic,),
            )
        mapping_ok, mapping_message = self.semantic_mappings.validate_primitive(
            command=name,
            native_kind=native.command_type,
            identity=mapping.identity,
        )
        if not mapping_ok:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-OUTPUT-006",
                "error",
                mapping_message,
            )
            return NativeSupportAssessment(
                name,
                NativeSupportState.UNSUPPORTED,
                diagnostic.message,
                (diagnostic,),
            )
        diagnostic = self._diagnostic(
            name,
            NativeSupportState.EXECUTABLE_SAFE,
            "NATIVE-OUTPUT-005",
            "info",
            "native output command has schema, typed Goal contract, contracted engine semantics, and executable-safe promotion",
        )
        return NativeSupportAssessment(
            name,
            NativeSupportState.EXECUTABLE_SAFE,
            "native output command is executable-safe",
            (diagnostic,),
            binding=None,
        )

    def bind_native_output_command(self, name: str) -> NativeOutputSemanticBinding:
        assessment = self.assess_native_output_command(name)
        if assessment.state is not NativeSupportState.EXECUTABLE_SAFE:
            raise ValueError(assessment.message)
        mapping = self.semantic_mappings.for_command(name)
        native = self.native_registry.get(name)
        assert mapping is not None and native is not None
        return NativeOutputSemanticBinding(
            command=name,
            native_version=native.version,
            native_kind=native.command_type,
            parameter_count=native.parameter_count,
            semantic_mapping_id=mapping.identity,
            mapping_status=mapping.status,
            evidence_class=mapping.evidence_class,
            evidence_sources=tuple(mapping.evidence_sources),
            support_state=NativeSupportState.EXECUTABLE_SAFE,
        )


    def assess_duc_command(self, name: str) -> NativeSupportAssessment:
        native = self.native_registry.get(name)
        if native is None:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-DUC-006",
                "error",
                "DUC command is not present in the checked-in native schema",
            )
            return NativeSupportAssessment(
                name,
                NativeSupportState.UNSUPPORTED,
                diagnostic.message,
                (diagnostic,),
            )

        if not self._native_typed(native):
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-DUC-006",
                "error",
                "DUC native metadata is not typed",
            )
            return NativeSupportAssessment(
                name,
                NativeSupportState.UNSUPPORTED,
                diagnostic.message,
                (diagnostic,),
            )

        mapping = self.semantic_mappings.for_command(name)
        if mapping is None:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-DUC-006",
                "error",
                "DUC command has no contracted engine semantic mapping",
            )
            return NativeSupportAssessment(
                name,
                NativeSupportState.UNSUPPORTED,
                diagnostic.message,
                (diagnostic,),
            )

        mapping_ok, mapping_message = self.semantic_mappings.validate_primitive(
            command=name,
            native_kind=native.command_type,
            identity=mapping.identity,
        )
        if not mapping_ok:
            diagnostic = self._diagnostic(
                name,
                NativeSupportState.UNSUPPORTED,
                "NATIVE-DUC-006",
                "error",
                mapping_message,
            )
            return NativeSupportAssessment(
                name,
                NativeSupportState.UNSUPPORTED,
                diagnostic.message,
                (diagnostic,),
            )

        binding = NativeDucSemanticBinding(
            command=name,
            native_version=native.version,
            native_kind=native.command_type,
            parameter_count=native.parameter_count,
            semantic_mapping_id=mapping.identity,
            mapping_status=mapping.status,
            evidence_class=mapping.evidence_class,
            evidence_sources=tuple(mapping.evidence_sources),
            support_state=NativeSupportState.EXECUTABLE_SAFE,
        )
        diagnostic = self._diagnostic(
            name,
            NativeSupportState.EXECUTABLE_SAFE,
            "NATIVE-DUC-005",
            "info",
            "DUC command has native schema, contracted engine semantics, and executable-safe promotion",
        )
        return NativeSupportAssessment(
            name,
            NativeSupportState.EXECUTABLE_SAFE,
            "DUC command is executable-safe",
            (diagnostic,),
            binding=None,
        )

    def bind_duc_command(self, name: str) -> NativeDucSemanticBinding:
        assessment = self.assess_duc_command(name)
        if assessment.state is not NativeSupportState.EXECUTABLE_SAFE:
            raise ValueError(assessment.message)
        mapping = self.semantic_mappings.for_command(name)
        native = self.native_registry.get(name)
        assert mapping is not None and native is not None
        return NativeDucSemanticBinding(
            command=name,
            native_version=native.version,
            native_kind=native.command_type,
            parameter_count=native.parameter_count,
            semantic_mapping_id=mapping.identity,
            mapping_status=mapping.status,
            evidence_class=mapping.evidence_class,
            evidence_sources=tuple(mapping.evidence_sources),
            support_state=NativeSupportState.EXECUTABLE_SAFE,
        )

    def bind_duc_plan(self, plan) -> tuple[NativeDucSemanticBinding, ...]:
        duc_commands = set(self.native_contracts.duc_command_names)
        bindings = tuple(
            self.bind_duc_command(command)
            for command in plan.commands
            if command in duc_commands
        )
        return tuple(sorted(bindings, key=lambda item: item.command))

    def bind(self, name: str) -> NativeSemanticBinding:
        assessment = self.assess(name)
        if assessment.state is not NativeSupportState.EXECUTABLE_SAFE:
            raise ValueError(assessment.message)
        assert assessment.binding is not None
        return assessment.binding

    def assess_all(self) -> tuple[NativeSupportAssessment, ...]:
        """Assess the complete native inventory without collapsing unsupported commands."""
        return tuple(
            self.assess(name)
            for name in sorted(self.native_registry.names())
        )

    def executable_bindings(self) -> tuple[NativeSemanticBinding, ...]:
        """Return only commands that clear the executable-safe semantic gate."""
        return tuple(
            assessment.binding
            for assessment in self.assess_all()
            if assessment.binding is not None
        )
