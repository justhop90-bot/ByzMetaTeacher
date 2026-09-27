"""Typed effective-source-graph intermediate representation.

This module contains compiler-owned source identity, source-instance identity,
explicit load topology, conditional predicates, effective slices, and canonical
assembly/effective fingerprints. The resolver is responsible for constructing
these values; validators are responsible for proving their consistency.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable


class LoadKind(str, Enum):
    FILE = "FILE"
    RAW_LOAD = "RAW_LOAD"
    CONDITIONAL_DEFINED = "CONDITIONAL_DEFINED"
    CONDITIONAL_NOT_DEFINED = "CONDITIONAL_NOT_DEFINED"
    CONDITIONAL_ELSE = "CONDITIONAL_ELSE"
    RANDOM = "RANDOM"


class LoadSymbolState(str, Enum):
    DEFINED = "DEFINED"
    UNDEFINED = "UNDEFINED"


@dataclass(frozen=True, order=True)
class SourceFileId:
    canonical_path: str
    content_sha256: str

    def __post_init__(self) -> None:
        if not self.canonical_path:
            raise ValueError("source file identity requires a canonical path")
        if len(self.content_sha256) != 64:
            raise ValueError("source file identity requires a SHA-256 hash")

    @property
    def path(self) -> Path:
        return Path(self.canonical_path)


@dataclass(frozen=True)
class SourceFile:
    identity: SourceFileId
    path: Path
    text: str

    def __post_init__(self) -> None:
        canonical = self.path.resolve()
        digest = hashlib.sha256(self.text.encode("utf-8")).hexdigest()
        if canonical != self.identity.path:
            raise ValueError("source file path does not match canonical identity")
        if digest != self.identity.content_sha256:
            raise ValueError("source file content does not match identity hash")
        object.__setattr__(self, "path", canonical)

    @classmethod
    def from_path_text(cls, path: Path, text: str) -> "SourceFile":
        canonical = path.resolve()
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return cls(
            identity=SourceFileId(canonical.as_posix(), digest),
            path=canonical,
            text=text,
        )

    @property
    def sha256(self) -> str:
        return self.identity.content_sha256

    def fingerprint_payload(self) -> tuple[str, str]:
        return (self.identity.canonical_path, self.identity.content_sha256)


@dataclass(frozen=True, order=True)
class SourceInstanceId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("source instance identity cannot be empty")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, order=True)
class SourceEdgeId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("source edge identity cannot be empty")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class SourceRange:
    source: SourceFileId
    start_offset: int
    end_offset: int
    start_line: int
    start_column: int
    end_line: int
    end_column: int

    def __post_init__(self) -> None:
        if self.start_offset < 0 or self.end_offset < self.start_offset:
            raise ValueError("invalid source offsets")
        if self.start_line < 1 or self.end_line < self.start_line:
            raise ValueError("invalid source line range")
        if self.start_column < 1 or self.end_column < 1:
            raise ValueError("invalid source columns")

    @property
    def location(self):
        from ..ast import SourceLocation
        return SourceLocation(
            self.start_line,
            self.start_column,
            self.source.canonical_path,
        )

    def fingerprint_payload(self) -> tuple[object, ...]:
        return (
            self.source.canonical_path,
            self.source.content_sha256,
            self.start_offset,
            self.end_offset,
            self.start_line,
            self.start_column,
            self.end_line,
            self.end_column,
        )


@dataclass(frozen=True)
class ConditionPredicate:
    symbol: str
    expected: LoadSymbolState

    def evaluate(self, environment: "LoadSymbolEnvironment") -> bool:
        state = environment.state(self.symbol)
        return state is self.expected

    def fingerprint_payload(self) -> tuple[str, str]:
        return (self.symbol, self.expected.value)


@dataclass(frozen=True)
class ConditionContext:
    predicates: tuple[ConditionPredicate, ...] = ()

    def __post_init__(self) -> None:
        names = [item.symbol for item in self.predicates]
        if len(names) != len(set(names)):
            raise ValueError("duplicate condition predicate")
        if any(not item.symbol for item in self.predicates):
            raise ValueError("condition predicate symbol cannot be empty")

    @property
    def depth(self) -> int:
        return len(self.predicates)

    def evaluate(self, environment: "LoadSymbolEnvironment") -> bool:
        return all(predicate.evaluate(environment) for predicate in self.predicates)

    def complement_last(self) -> "ConditionContext":
        if not self.predicates:
            raise ValueError("cannot complement an empty condition context")
        last = self.predicates[-1]
        expected = (
            LoadSymbolState.UNDEFINED
            if last.expected is LoadSymbolState.DEFINED
            else LoadSymbolState.DEFINED
        )
        return ConditionContext(
            self.predicates[:-1] + (
                ConditionPredicate(last.symbol, expected),
            )
        )

    def fingerprint_payload(self) -> tuple[tuple[str, str], ...]:
        return tuple(item.fingerprint_payload() for item in self.predicates)


@dataclass(frozen=True)
class LoadSymbolEnvironment:
    values: tuple[tuple[str, LoadSymbolState], ...] = ()

    def __post_init__(self) -> None:
        normalized = tuple(sorted(self.values, key=lambda item: item[0]))
        names = [name for name, _state in normalized]
        if len(names) != len(set(names)):
            raise ValueError("duplicate load-symbol definition")
        if any(not name for name in names):
            raise ValueError("invalid load-symbol name")
        object.__setattr__(self, "values", normalized)

    def state(self, name: str) -> LoadSymbolState | None:
        for candidate, state in self.values:
            if candidate == name:
                return state
        return None

    def fingerprint_payload(self) -> tuple[tuple[str, str], ...]:
        return tuple((name, state.value) for name, state in self.values)


@dataclass(frozen=True)
class SourceInstance:
    identity: SourceInstanceId
    source: SourceFileId
    parent: SourceInstanceId | None
    via_edge: SourceEdgeId | None
    ancestry: tuple[SourceFileId, ...]
    depth: int
    occurrence: int

    @property
    def instance_id(self) -> str:
        return self.identity.value

    @property
    def load_stack(self) -> tuple[Path, ...]:
        return tuple(item.path for item in self.ancestry)

    @property
    def physical(self) -> SourceFile:
        # Compatibility object for existing consumers. The graph-level files
        # table is authoritative; this lightweight projection carries identity.
        raise AttributeError(
            "SourceInstance.physical is graph-scoped; use EffectiveSourceGraph.files_by_id"
        )

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "id": self.identity.value,
            "source": self.source.fingerprint_payload(),
            "parent": self.parent.value if self.parent else None,
            "via_edge": self.via_edge.value if self.via_edge else None,
            "ancestry": [item.fingerprint_payload() for item in self.ancestry],
            "depth": self.depth,
            "occurrence": self.occurrence,
        }


@dataclass(frozen=True)
class SourceEdge:
    identity: SourceEdgeId
    source: SourceInstanceId
    target: SourceFileId | None
    child: SourceInstanceId | None
    kind: LoadKind
    span: SourceRange
    condition: ConditionContext
    active: bool
    lexical_order: int
    target_text: str | None = None

    @property
    def source_instance(self) -> str:
        return self.source.value

    @property
    def target_path(self) -> Path | None:
        return self.target.path if self.target else None

    @property
    def location(self):
        return self.span.location

    @property
    def condition_symbol(self) -> str | None:
        if not self.condition.predicates:
            return None
        return self.condition.predicates[-1].symbol

    @property
    def condition_kind(self) -> LoadKind | None:
        if not self.condition.predicates:
            return None
        expected = self.condition.predicates[-1].expected
        return (
            LoadKind.CONDITIONAL_DEFINED
            if expected is LoadSymbolState.DEFINED
            else LoadKind.CONDITIONAL_NOT_DEFINED
        )

    @property
    def edge_id(self) -> str:
        return self.identity.value

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "id": self.identity.value,
            "source": self.source.value,
            "target": self.target.fingerprint_payload() if self.target else None,
            "child": self.child.value if self.child else None,
            "kind": self.kind.value,
            "span": self.span.fingerprint_payload(),
            "condition": self.condition.fingerprint_payload(),
            "active": self.active,
            "lexical_order": self.lexical_order,
            "target_text": self.target_text,
        }


@dataclass(frozen=True)
class EffectiveSourceSlice:
    ordinal: int
    instance: SourceInstanceId
    physical_range: SourceRange
    text: str

    @property
    def instance_id(self) -> str:
        return self.instance.value

    @property
    def path(self) -> Path:
        return self.physical_range.source.path

    @property
    def start_line(self) -> int:
        return self.physical_range.start_line

    @property
    def end_line(self) -> int:
        return self.physical_range.end_line

    @property
    def start_column(self) -> int:
        return self.physical_range.start_column

    @property
    def text_sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "ordinal": self.ordinal,
            "instance": self.instance.value,
            "range": self.physical_range.fingerprint_payload(),
            "sha256": self.text_sha256,
        }


@dataclass(frozen=True)
class EffectiveSourceGraph:
    root: SourceInstance
    files: tuple[SourceFile, ...]
    instances: tuple[SourceInstance, ...]
    edges: tuple[SourceEdge, ...]
    slices: tuple[EffectiveSourceSlice, ...]
    symbol_environment: LoadSymbolEnvironment
    assembly_fingerprint: str
    effective_fingerprint: str

    @property
    def fingerprint(self) -> str:
        """Compatibility alias for the former single graph fingerprint."""
        return self.assembly_fingerprint

    @property
    def files_by_id(self) -> dict[SourceFileId, SourceFile]:
        return {item.identity: item for item in self.files}

    @property
    def instances_by_id(self) -> dict[SourceInstanceId, SourceInstance]:
        return {item.identity: item for item in self.instances}

    @property
    def edges_by_id(self) -> dict[SourceEdgeId, SourceEdge]:
        return {item.identity: item for item in self.edges}

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "root": self.root.identity.value,
            "files": [
                item.fingerprint_payload()
                for item in sorted(self.files, key=lambda value: value.identity)
            ],
            "instances": [
                item.fingerprint_payload()
                for item in sorted(self.instances, key=lambda value: value.identity)
            ],
            "edges": [
                item.fingerprint_payload()
                for item in sorted(self.edges, key=lambda value: value.identity)
            ],
            "symbols": self.symbol_environment.fingerprint_payload(),
            "slices": [
                item.fingerprint_payload()
                for item in sorted(self.slices, key=lambda value: value.ordinal)
            ],
        }

    @staticmethod
    def compute_assembly_fingerprint(
        *,
        root: SourceInstance,
        files: Iterable[SourceFile],
        instances: Iterable[SourceInstance],
        edges: Iterable[SourceEdge],
        slices: Iterable[EffectiveSourceSlice],
        symbols: LoadSymbolEnvironment,
    ) -> str:
        payload = {
            "root": root.identity.value,
            "files": [
                item.fingerprint_payload()
                for item in sorted(files, key=lambda value: value.identity)
            ],
            "instances": [
                item.fingerprint_payload()
                for item in sorted(instances, key=lambda value: value.identity)
            ],
            "edges": [
                item.fingerprint_payload()
                for item in sorted(edges, key=lambda value: value.identity)
            ],
            "slices": [
                item.fingerprint_payload()
                for item in sorted(slices, key=lambda value: value.ordinal)
            ],
            "symbols": symbols.fingerprint_payload(),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def compute_effective_fingerprint(
        *,
        root: SourceInstance,
        slices: Iterable[EffectiveSourceSlice],
    ) -> str:
        payload = {
            "root": root.identity.value,
            "slices": [
                {
                    "ordinal": item.ordinal,
                    "instance": item.instance.value,
                    "sha256": item.text_sha256,
                }
                for item in sorted(slices, key=lambda value: value.ordinal)
            ],
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    @classmethod
    def build(
        cls,
        *,
        root: SourceInstance,
        files: Iterable[SourceFile],
        instances: Iterable[SourceInstance],
        edges: Iterable[SourceEdge],
        slices: Iterable[EffectiveSourceSlice],
        symbols: LoadSymbolEnvironment,
    ) -> "EffectiveSourceGraph":
        files_tuple = tuple(files)
        instances_tuple = tuple(instances)
        edges_tuple = tuple(edges)
        slices_tuple = tuple(slices)
        return cls(
            root=root,
            files=files_tuple,
            instances=instances_tuple,
            edges=edges_tuple,
            slices=slices_tuple,
            symbol_environment=symbols,
            assembly_fingerprint=cls.compute_assembly_fingerprint(
                root=root,
                files=files_tuple,
                instances=instances_tuple,
                edges=edges_tuple,
                slices=slices_tuple,
                symbols=symbols,
            ),
            effective_fingerprint=cls.compute_effective_fingerprint(
                root=root,
                slices=slices_tuple,
            ),
        )


def structural_instance_id(
    *,
    source: SourceFileId,
    parent: SourceInstanceId | None,
    via_edge: SourceEdgeId | None,
) -> SourceInstanceId:
    payload = {
        "source": source.fingerprint_payload(),
        "parent": parent.value if parent else None,
        "via_edge": via_edge.value if via_edge else None,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return SourceInstanceId(digest)


def structural_edge_id(
    *,
    source: SourceInstanceId,
    span: SourceRange,
    kind: LoadKind,
    condition: ConditionContext,
    target_text: str | None,
) -> SourceEdgeId:
    payload = {
        "source": source.value,
        "span": span.fingerprint_payload(),
        "kind": kind.value,
        "condition": condition.fingerprint_payload(),
        "target_text": target_text,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return SourceEdgeId(digest)


__all__ = [
    "ConditionContext",
    "ConditionPredicate",
    "EffectiveSourceGraph",
    "EffectiveSourceSlice",
    "LoadKind",
    "LoadSymbolEnvironment",
    "LoadSymbolState",
    "SourceEdge",
    "SourceEdgeId",
    "SourceFile",
    "SourceFileId",
    "SourceInstance",
    "SourceInstanceId",
    "SourceRange",
    "structural_edge_id",
    "structural_instance_id",
]
