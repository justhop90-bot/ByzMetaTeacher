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
