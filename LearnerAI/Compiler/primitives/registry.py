"""Semantic adapters backed by the checked-in AIRef native command schema."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path

from .native_schema import NativeCommandRegistry, load_default_native_schema



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

class PrimitiveRegistry:
    def __init__(
        self,
        primitives: tuple[Primitive, ...],
        native_registry: NativeCommandRegistry | None = None,
    ):
        self._items = {p.name: p for p in primitives}
        self._native = native_registry



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
                "NATIVE-SUPPORT-005",
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
        ),
        Primitive("train", "ACTION", "ACTION", 1, 1, completion_witness=False),
        Primitive("research", "ACTION", "ACTION", 1, 1, completion_witness=False),
    ]
    native_registry = (
        load_default_native_schema()
        if schema_path is None
        else NativeCommandRegistry.from_path(schema_path)
    )
    semantic_mappings = {
        "current-age": "observation.age.current",
        "food-amount": "observation.resource.food",
        "wood-amount": "observation.resource.wood",
        "gold-amount": "observation.resource.gold",
        "stone-amount": "observation.resource.stone",
        "players-unit-type-count": "observation.threat.unit-count",
        "players-building-type-count": "observation.world.building-count",
        "game-time": "observation.timing.game-time",
        "dropsite-min-distance": "observation.placement.dropsite-distance",
        "building-available": "admissibility.building.available",
        "can-afford-building": "arbitration.building.affordability",
        "can-build": "execution.build.feasibility",
        "can-build-with-escrow": "execution.build.feasibility.escrow",
        "building-type-count": "witness.building.present",
        "building-type-count-total": "witness.building.present.total",
        "unit-type-count": "observation.unit.count",
        "unit-type-count-total": "witness.unit.present.total",
        "can-train": "execution.train.feasibility",
        "can-train-with-escrow": "execution.train.feasibility.escrow",
        "up-pending-objects": "execution.pending-objects",
        "research-available": "admissibility.research.available",
        "can-afford-research": "arbitration.research.affordability",
        "can-research": "execution.research.feasibility",
        "can-research-with-escrow": "execution.research.feasibility.escrow",
        "research-completed": "witness.research.completed",
        "build": "execution.build.request",
        "train": "execution.train.request",
        "research": "execution.research.request",
    }
    primitive_items = tuple(facts + actions)
    if set(semantic_mappings) != {item.name for item in primitive_items}:
        raise ValueError("default native semantic mapping inventory is incomplete")
    mapped_items = tuple(
        replace(item, engine_semantics_id=semantic_mappings[item.name])
        for item in primitive_items
    )
    registry = PrimitiveRegistry(mapped_items, native_registry)
    for primitive in mapped_items:
        registry.validate_adapter_contract(primitive)
    return registry
