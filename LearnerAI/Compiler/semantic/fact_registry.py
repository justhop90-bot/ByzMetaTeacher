"""Semantic bridge for native AoE2 fact commands.

This module binds checked-in native fact metadata to canonical semantic values.
It deliberately does not resolve GameData names/classes, observe runtime state,
or infer predicate truth. Those remain separate compiler layers.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, Iterable, Sequence, TypeAlias

from ..primitives.native_hygiene import (
    AIRefProvenance,
    ConfidenceBasis,
    ConfidenceLevel,
    EvidenceKind,
)
from ..primitives.native_schema import NativeCommandRegistry, NativeParameterSpec
from .fact_values import (
    CanonicalizationContext,
    FactDomain,
    NormalizedFact,
    IdentifierForm,
    canonicalize_value,
)


_COMPARE_OPS = (">", ">=", "<", "<=", "==", "!=")
_AGE_VALUES = ("DARK", "FEUDAL", "CASTLE", "IMPERIAL")
_RESOURCE_VALUES = (
    "FOOD",
    "WOOD",
    "STONE",
    "GOLD",
    "HUNTING",
    "BOAR-HUNTING",
    "DEER-HUNTING",
    "LIVE-BOAR",
)
_TYPE_OP_VALUES = ("C", "G", "S")
_NUMERIC_RANGE = re.compile(r"(-?\d+)\s+to\s+(-?\d+)")

StaticTruthEvaluator: TypeAlias = Callable[[NormalizedFact], StaticTruth]


def _documented_fact_provenance(command: str) -> tuple[AIRefProvenance, ...]:
    return (
        AIRefProvenance(
            evidence_kind=EvidenceKind.DOCUMENTED_FACT,
            confidence=ConfidenceLevel.HIGH,
            confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
            citation_id=f"airef:{command}",
        ),
    )


def _integer_context(parameter: NativeParameterSpec) -> CanonicalizationContext:
    match = _NUMERIC_RANGE.search(parameter.range)
    minimum = maximum = None
    if match:
        minimum = int(match.group(1))
        maximum = int(match.group(2))
    return CanonicalizationContext.integer(
        parameter_name=parameter.name,
        minimum=minimum,
        maximum=maximum,
    )


def _identifier_context(
    parameter: NativeParameterSpec,
    *,
    namespace: str,
) -> CanonicalizationContext:
    # Native command metadata identifies the identifier class but does not
    # provide the complete checked-in name/class universe.  This bridge therefore
    # accepts numeric object ids (including decimal text) and fails closed on
    # unresolved names/classes until the GameData layer supplies those symbols.
    return CanonicalizationContext.identifier(
        parameter_name=parameter.name,
        namespace=namespace,
        accepted_forms=(IdentifierForm.NUMERIC_ID,),
        allow_numeric_strings=True,
    )


def _parameter_context(
    command: str,
    parameter: NativeParameterSpec,
) -> CanonicalizationContext:
    name = parameter.name
    if name == "compareOp":
        return CanonicalizationContext.enum(
            parameter_name=name,
            domain="COMPARE_OP",
            members=_COMPARE_OPS,
            case_sensitive=True,
        )

    if name == "typeOp":
        return CanonicalizationContext.enum(
            parameter_name=name,
            domain="TYPE_OP",
            members=_TYPE_OP_VALUES,
            aliases=(("c:", "C"), ("g:", "G"), ("s:", "S")),
            case_sensitive=False,
        )

    if command == "current-age" and name == "Age":
        return CanonicalizationContext.enum(
            parameter_name=name,
            domain="AGE",
            members=_AGE_VALUES,
            case_sensitive=False,
        )

    if command == "dropsite-min-distance" and name == "Resource":
        return CanonicalizationContext.enum(
            parameter_name=name,
            domain="RESOURCE",
            members=_RESOURCE_VALUES,
            case_sensitive=False,
        )

    if name == "PlayerNumber":
        return CanonicalizationContext.integer(parameter_name=name)

    if name in {"BuildingId", "BuildingID"}:
        return _identifier_context(parameter, namespace="BUILDING")

    if name in {"UnitId", "UnitID"}:
        return _identifier_context(parameter, namespace="UNIT")

    if name in {"TechId", "TechID"}:
        return _identifier_context(parameter, namespace="TECH")

    if name == "ObjectId":
        return _identifier_context(parameter, namespace="OBJECT")

    if parameter.type == "Op" and parameter.range:
        return _integer_context(parameter)

    raise ValueError(
        f"native fact parameter '{name}' on '{command}' has no canonical "
        "semantic context"
    )


@dataclass(frozen=True)
class FactSemanticAdapter:
    """Canonical semantic contract for one native Fact command."""

    native_command: str
    semantic_id: str
    role: str
    parameter_contexts: tuple[CanonicalizationContext, ...]
    provenance: tuple[AIRefProvenance, ...]
    static_truth_evaluator: StaticTruthEvaluator | None = None
    native_version: str = "DE"
    domain: FactDomain | None = None

    def __post_init__(self) -> None:
        if not self.native_command:
            raise ValueError("fact semantic adapter native_command is required")
        if not self.semantic_id:
            raise ValueError("fact semantic adapter semantic_id is required")
        if not self.role:
            raise ValueError("fact semantic adapter role is required")
        if not self.parameter_contexts:
            raise ValueError(
                f"fact semantic adapter '{self.native_command}' requires parameters"
            )
        if not self.provenance:
            raise ValueError(
                f"fact semantic adapter '{self.native_command}' requires provenance"
            )
        names = tuple(context.parameter_name for context in self.parameter_contexts)
        if len(names) != len(set(names)):
            raise ValueError(
                f"fact semantic adapter '{self.native_command}' has duplicate "
                "parameter names"
            )
        for evidence in self.provenance:
            if not isinstance(evidence, AIRefProvenance):
                raise TypeError(
                    "fact semantic adapter provenance contains invalid evidence"
                )

    @property
    def arity(self) -> int:
        return len(self.parameter_contexts)

    def evaluate_static_truth(self, fact: NormalizedFact) -> StaticTruth:
        if not isinstance(fact, NormalizedFact):
            raise TypeError("fact must be a NormalizedFact")
        if fact.semantic_id != self.semantic_id:
            raise ValueError(
                f"semantic adapter '{self.semantic_id}' cannot evaluate "
                f"fact '{fact.semantic_id}'"
            )
        if len(fact.canonical_args) != self.arity:
            raise ValueError(
                f"fact '{fact.semantic_id}' has {len(fact.canonical_args)} "
                f"canonical arguments; adapter requires {self.arity}"
            )
        if self.static_truth_evaluator is None:
            return StaticTruth.UNKNOWN
        result = self.static_truth_evaluator(fact)
        if not isinstance(result, StaticTruth):
            raise TypeError(
                f"static truth evaluator for '{self.semantic_id}' returned "
                f"{type(result).__name__}, expected StaticTruth"
            )
        return result

    def normalize(
        self,
        args: Sequence[object],
        *,
        provenance: tuple[AIRefProvenance, ...] | None = None,
    ) -> NormalizedFact:
        if len(args) != self.arity:
            raise ValueError(
                f"native fact '{self.native_command}' expects exactly "
                f"{self.arity} argument(s), got {len(args)}"
            )

        canonical_args = tuple(
            canonicalize_value(value, context)
            for value, context in zip(args, self.parameter_contexts, strict=True)
        )
        evidence = self.provenance if provenance is None else tuple(provenance)
        if not evidence:
            raise ValueError(
                f"native fact '{self.native_command}' normalization requires provenance"
            )
        return NormalizedFact(
            semantic_id=self.semantic_id,
            canonical_args=canonical_args,
            provenance=evidence,
            domain=self.domain,
        )


@dataclass(frozen=True)
class NativeFactRegistry:
    """Deterministic registry of executable native fact semantic adapters."""

    adapters: tuple[FactSemanticAdapter, ...]
    source_blob_sha: str

    def __post_init__(self) -> None:
        if not self.source_blob_sha:
            raise ValueError("native fact registry source_blob_sha is required")
        commands = tuple(adapter.native_command for adapter in self.adapters)
        semantic_ids = tuple(adapter.semantic_id for adapter in self.adapters)
        if len(commands) != len(set(commands)):
            raise ValueError("duplicate native fact semantic adapter command")
        if len(semantic_ids) != len(set(semantic_ids)):
            raise ValueError("duplicate native fact semantic adapter identity")
        if commands != tuple(sorted(commands)):
            raise ValueError(
                "native fact semantic adapters must be stored in deterministic command order"
            )

    @classmethod
    def from_primitives(
        cls,
        primitives: Iterable[object],
        native_registry: NativeCommandRegistry,
        semantic_mappings,
    ) -> "NativeFactRegistry":
        adapters: list[FactSemanticAdapter] = []
        for primitive in primitives:
            if getattr(primitive, "kind", None) != "FACT":
                continue

            command = primitive.name
            native = native_registry.require(command)
            if native.command_type != "Fact":
                raise ValueError(
                    f"fact primitive '{command}' is backed by native "
                    f"'{native.command_type}', not Fact"
                )
            semantic_id = primitive.engine_semantics_id
            if not semantic_id:
                raise ValueError(
                    f"fact primitive '{command}' has no engine semantic identity"
                )
            mapping = semantic_mappings.require(semantic_id)
            if mapping.native_command != command or mapping.native_kind != "Fact":
                raise ValueError(
                    f"fact primitive '{command}' has mismatched engine semantic "
                    f"mapping '{semantic_id}'"
                )
            contexts = tuple(
                _parameter_context(command, parameter)
                for parameter in native.parameters
            )
            if len(contexts) != native.parameter_count:
                raise ValueError(
                    f"fact semantic adapter '{command}' parameter context count "
                    f"does not match native metadata"
                )
            if not (
                primitive.min_args
                <= native.parameter_count
                <= primitive.max_args
            ):
                raise ValueError(
                    f"semantic adapter arity mismatch for '{command}': "
                    f"native={native.parameter_count}, "
                    f"semantic={primitive.min_args}..{primitive.max_args}"
                )
            adapters.append(
                FactSemanticAdapter(
                    native_command=command,
                    semantic_id=semantic_id,
                    role=primitive.role,
                    parameter_contexts=contexts,
                    provenance=_documented_fact_provenance(command),
                    native_version=native.version,
                )
            )

        ordered = tuple(sorted(adapters, key=lambda item: item.native_command))
        return cls(
            adapters=ordered,
            source_blob_sha=native_registry.source_blob_sha,
        )

    def get(self, command: str) -> FactSemanticAdapter | None:
        for adapter in self.adapters:
            if adapter.native_command == command:
                return adapter
        return None

    def require(self, command: str) -> FactSemanticAdapter:
        adapter = self.get(command)
        if adapter is None:
            raise KeyError(command)
        return adapter

    def by_semantic_id(self, semantic_id: str) -> FactSemanticAdapter | None:
        for adapter in self.adapters:
            if adapter.semantic_id == semantic_id:
                return adapter
        return None

    def names(self) -> tuple[str, ...]:
        return tuple(adapter.native_command for adapter in self.adapters)

    def normalize(
        self,
        command: str,
        args: Sequence[object],
        *,
        provenance: tuple[AIRefProvenance, ...] | None = None,
    ) -> NormalizedFact:
        return self.require(command).normalize(args, provenance=provenance)


__all__ = [
    "FactSemanticAdapter",
    "NativeFactRegistry",
    "StaticTruthEvaluator",
]
