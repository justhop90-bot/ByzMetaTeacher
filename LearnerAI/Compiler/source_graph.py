"""Effective native .per source graph resolution.

The graph resolves source assembly before the semantic demand parser. It owns
effective source order, load reachability, conditional branches, and physical
source provenance. Native package legality remains a backend concern.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .ast import SourceLocation
from .diagnostics import DiagnosticSeverity, DiagnosticSource, SemanticDiagnostic
from .errors import CompileError


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


@dataclass(frozen=True)
class LoadSymbolEnvironment:
    values: tuple[tuple[str, LoadSymbolState], ...] = ()

    def __post_init__(self) -> None:
        normalized = tuple(sorted(self.values, key=lambda item: item[0]))
        names = [name for name, _state in normalized]
        if len(names) != len(set(names)):
            raise ValueError("duplicate load-symbol definition")
        if any(not name or _SYMBOL_RE.fullmatch(name) is None for name in names):
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
class SourceGraphRequest:
    entrypoint: Path
    search_roots: tuple[Path, ...] = ()
    load_symbols: LoadSymbolEnvironment = field(default_factory=LoadSymbolEnvironment)
    allow_load_random: bool = False


@dataclass(frozen=True)
class SourceUnit:
    path: Path
    sha256: str
    text: str


@dataclass(frozen=True)
class SourceInstance:
    instance_id: str
    physical: SourceUnit
    load_stack: tuple[Path, ...]
    occurrence: int


@dataclass(frozen=True)
class SourceEdge:
    source_instance: str
    target_path: Path | None
    kind: LoadKind
    location: SourceLocation
    condition_symbol: str | None
    active: bool
    condition_kind: LoadKind | None = None


@dataclass(frozen=True)
class EffectiveSourceSlice:
    ordinal: int
    instance_id: str
    path: Path
    start_line: int
    end_line: int
    start_column: int
    text: str


@dataclass(frozen=True)
class EffectiveSourceGraph:
    root: SourceInstance
    instances: tuple[SourceInstance, ...]
    edges: tuple[SourceEdge, ...]
    slices: tuple[EffectiveSourceSlice, ...]
    symbol_environment: LoadSymbolEnvironment
    fingerprint: str


@dataclass(frozen=True)
class _ConditionalFrame:
    kind: LoadKind
    symbol: str
    parent_active: bool
    branch_active: bool
    else_seen: bool
    line: int


@dataclass(frozen=True)
class _LoadOccurrence:
    start: int
    end: int
    line: int
    column: int
    kind: LoadKind
    target: str | None
    raw: str


_SYMBOL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_CONDITIONAL_RE = re.compile(
    r"^\s*#(?P<kind>load-if-defined|load-if-not-defined)\s+"
    r"(?P<symbol>[A-Za-z_][A-Za-z0-9_-]*)\s*$"
)
_ELSE_RE = re.compile(r"^\s*#else\s*$")
_END_RE = re.compile(r"^\s*#end-if\s*$")
_RAW_LOAD_RE = re.compile(r'^\s*#load\s+"(?P<target>(?:\\.|[^"\\])*)"\s*$')
_RAW_RANDOM_RE = re.compile(r"^\s*#load-random(?:\s+.*)?$")


def _diagnostic(
    code: str,
    message: str,
    *,
    path: Path,
    line: int,
    column: int,
) -> SemanticDiagnostic:
    identifier = hashlib.sha256(
        f"LearnerAI\0{code}\0{path}\0{line}\0{column}\0{message}".encode("utf-8")
    ).hexdigest()
    return SemanticDiagnostic(
        id=identifier,
        source=DiagnosticSource.LEARNERAI,
        code=code,
        severity=DiagnosticSeverity.ERROR,
        message=message,
        path=path,
        line=line,
        column=column,
    )


class SourceGraphError(CompileError):
    """Compiler-owned source graph failure with structured diagnostics."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        path: Path,
        line: int,
        column: int,
    ) -> None:
        super().__init__(
            f"{code}: {message}",
            diagnostics=(
                _diagnostic(
                    code,
                    message,
                    path=path,
                    line=line,
                    column=column,
                ),
            ),
        )


class SourceGraphResolver:
    MAX_LOAD_DEPTH = 10
    MAX_CONDITIONAL_DEPTH = 50

    def __init__(self) -> None:
        self._instance_counter = 0
        self._slice_counter = 0
        self._occurrences_by_path: dict[Path, int] = {}
        self._instances: list[SourceInstance] = []
        self._edges: list[SourceEdge] = []
        self._slices: list[EffectiveSourceSlice] = []

    def resolve(self, request: SourceGraphRequest) -> EffectiveSourceGraph:
        self._instance_counter = 0
        self._slice_counter = 0
        self._occurrences_by_path = {}
        self._instances = []
        self._edges = []
        self._slices = []

        search_roots = tuple(path.resolve() for path in request.search_roots)
        entrypoint = request.entrypoint.resolve()
        root_unit = self._load_unit(
            entrypoint,
            containing_source=entrypoint,
            search_roots=search_roots,
            error_line=1,
            error_column=1,
        )
        root = self._expand_instance(
            root_unit,
            load_stack=(),
            search_roots=search_roots,
            symbols=request.load_symbols,
            allow_load_random=request.allow_load_random,
        )

        fingerprint_payload = {
            "root": root.instance_id,
            "symbols": request.load_symbols.fingerprint_payload(),
            "instances": [
                {
                    "id": item.instance_id,
                    "path": str(item.physical.path),
                    "sha256": item.physical.sha256,
                    "stack": [str(path) for path in item.load_stack],
                    "occurrence": item.occurrence,
                }
                for item in self._instances
            ],
            "edges": [
                {
                    "source": item.source_instance,
                    "target": str(item.target_path) if item.target_path else None,
                    "kind": item.kind.value,
                    "condition_kind": item.condition_kind.value if item.condition_kind else None,
                    "line": item.location.line,
                    "column": item.location.column,
                    "condition_symbol": item.condition_symbol,
                    "active": item.active,
                }
                for item in self._edges
            ],
            "slices": [
                {
                    "ordinal": item.ordinal,
                    "instance": item.instance_id,
                    "path": str(item.path),
                    "start_line": item.start_line,
                    "end_line": item.end_line,
                    "start_column": item.start_column,
                    "sha256": hashlib.sha256(item.text.encode("utf-8")).hexdigest(),
                }
                for item in self._slices
            ],
        }
        fingerprint = hashlib.sha256(
            json.dumps(
                fingerprint_payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8"),
        ).hexdigest()

        return EffectiveSourceGraph(
            root=root,
            instances=tuple(self._instances),
            edges=tuple(self._edges),
            slices=tuple(self._slices),
            symbol_environment=request.load_symbols,
            fingerprint=fingerprint,
        )

    def _load_unit(
        self,
        target: Path,
        *,
        containing_source: Path,
        search_roots: tuple[Path, ...],
        error_line: int,
        error_column: int,
    ) -> SourceUnit:
        resolved = self._resolve_path(
            target,
            containing_source.parent,
            search_roots,
        )
        if resolved is None or not resolved.is_file():
            raise SourceGraphError(
                "SOURCE-GRAPH-001",
                f"missing load target '{target}'",
                path=containing_source,
                line=error_line,
                column=error_column,
            )
        text = resolved.read_text(encoding="utf-8")
        return SourceUnit(
            path=resolved,
            sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            text=text,
        )

    @staticmethod
    def _resolve_path(
        target: Path,
        containing_directory: Path,
        search_roots: tuple[Path, ...],
    ) -> Path | None:
        if target.is_absolute():
            candidate = target.resolve()
            return candidate if candidate.exists() else None

        local = (containing_directory / target).resolve()
        if local.exists():
            return local

        for root in search_roots:
            candidate = (root / target).resolve()
            if candidate.exists():
                return candidate
        return None

    def _new_instance(
        self,
        physical: SourceUnit,
        load_stack: tuple[Path, ...],
    ) -> SourceInstance:
        occurrence = self._occurrences_by_path.get(physical.path, 0)
        self._occurrences_by_path[physical.path] = occurrence + 1
        instance = SourceInstance(
            instance_id=f"{physical.path.as_posix()}@{self._instance_counter}",
            physical=physical,
            load_stack=load_stack + (physical.path,),
            occurrence=occurrence,
        )
        self._instance_counter += 1
        self._instances.append(instance)
        return instance

    def _expand_instance(
        self,
        physical: SourceUnit,
        *,
        load_stack: tuple[Path, ...],
        search_roots: tuple[Path, ...],
        symbols: LoadSymbolEnvironment,
        allow_load_random: bool,
    ) -> SourceInstance:
        if len(load_stack) > self.MAX_LOAD_DEPTH:
            raise SourceGraphError(
                "SOURCE-GRAPH-003",
                f"nested load depth exceeds {self.MAX_LOAD_DEPTH}",
                path=physical.path,
                line=1,
                column=1,
            )

        if physical.path in load_stack:
            cycle = " -> ".join(str(path) for path in (*load_stack, physical.path))
            raise SourceGraphError(
                "SOURCE-GRAPH-002",
                f"load cycle detected: {cycle}",
                path=physical.path,
                line=1,
                column=1,
            )

        instance = self._new_instance(physical, load_stack)
        masked, active_lines, condition_contexts, directive_edges = _mask_conditionals(
            physical.text,
            physical.path,
            symbols,
            self.MAX_CONDITIONAL_DEPTH,
            instance.instance_id,
        )
        self._edges.extend(directive_edges)

        occurrences = _scan_load_occurrences(physical.text, path=physical.path)
        cursor = 0

        for occurrence in occurrences:
            context = condition_contexts[occurrence.line - 1]
            active = active_lines[occurrence.line - 1]

            self._append_slice(
                instance,
                physical.path,
                masked[cursor:occurrence.start],
                cursor,
                physical.text,
            )
            cursor = occurrence.end

            target_path = None
            if occurrence.target is not None:
                target_path = self._resolve_path(
                    Path(occurrence.target),
                    physical.path.parent,
                    search_roots,
                )

            location = SourceLocation(
                occurrence.line,
                occurrence.column,
                str(physical.path),
            )
            self._edges.append(
                SourceEdge(
                    source_instance=instance.instance_id,
                    target_path=target_path,
                    kind=occurrence.kind,
                    location=location,
                    condition_symbol=context[1] if context else None,
                    active=active,
                    condition_kind=context[0] if context else None,
                )
            )

            if not active:
                continue

            if occurrence.kind is LoadKind.RANDOM:
                raise SourceGraphError(
                    "SOURCE-GRAPH-007",
                    (
                        "load-random requires an explicit materialized "
                        "selection policy for deterministic compilation"
                    ),
                    path=physical.path,
                    line=occurrence.line,
                    column=occurrence.column,
                )

            if target_path is None:
                raise SourceGraphError(
                    "SOURCE-GRAPH-001",
                    f"missing load target '{occurrence.target}'",
                    path=physical.path,
                    line=occurrence.line,
                    column=occurrence.column,
                )

            child = self._load_unit(
                target_path,
                containing_source=physical.path,
                search_roots=search_roots,
                error_line=occurrence.line,
                error_column=occurrence.column,
            )
            if child.path in (*load_stack, physical.path):
                cycle = " -> ".join(
                    str(path) for path in (*load_stack, physical.path, child.path)
                )
                raise SourceGraphError(
                    "SOURCE-GRAPH-002",
                    f"load cycle detected: {cycle}",
                    path=physical.path,
                    line=occurrence.line,
                    column=occurrence.column,
                )

            self._expand_instance(
                child,
                load_stack=(*load_stack, physical.path),
                search_roots=search_roots,
                symbols=symbols,
                allow_load_random=allow_load_random,
            )

        self._append_slice(
            instance,
            physical.path,
            masked[cursor:],
            cursor,
            physical.text,
        )
        return instance

    def _append_slice(
        self,
        instance: SourceInstance,
        path: Path,
        text: str,
        start_offset: int,
        physical_text: str,
    ) -> None:
        if not text.strip():
            return
        start_line = physical_text.count("\n", 0, start_offset) + 1
        last_newline = physical_text.rfind("\n", 0, start_offset)
        start_column = start_offset - last_newline
        end_line = start_line + text.count("\n")
        self._slices.append(
            EffectiveSourceSlice(
                ordinal=self._slice_counter,
                instance_id=instance.instance_id,
                path=path,
                start_line=start_line,
                end_line=end_line,
                start_column=start_column,
                text=text,
            )
        )
        self._slice_counter += 1


def _mask_conditionals(
    source: str,
    path: Path,
    symbols: LoadSymbolEnvironment,
    max_depth: int,
    source_instance: str,
) -> tuple[
    str,
    tuple[bool, ...],
    tuple[tuple[LoadKind, str] | None, ...],
    tuple[SourceEdge, ...],
]:
    lines = source.splitlines(keepends=True)
    active_flags: list[bool] = []
    contexts: list[tuple[LoadKind, str] | None] = []
    frames: list[_ConditionalFrame] = []
    directive_edges: list[SourceEdge] = []

    for index, raw_line in enumerate(lines, 1):
        stripped = raw_line.strip()
        current_active = frames[-1].branch_active if frames else True
        context = (frames[-1].kind, frames[-1].symbol) if frames else None

        match = _CONDITIONAL_RE.fullmatch(stripped)
        if match:
            if len(frames) >= max_depth:
                raise SourceGraphError(
                    "SOURCE-GRAPH-005",
                    f"conditional nesting exceeds {max_depth}",
                    path=path,
                    line=index,
                    column=1,
                )

            symbol = match.group("symbol")
            state = symbols.state(symbol)
            if state is None:
                raise SourceGraphError(
                    "SOURCE-GRAPH-006",
                    f"conditional load symbol '{symbol}' is unresolved",
                    path=path,
                    line=index,
                    column=1,
                )

            kind = (
                LoadKind.CONDITIONAL_DEFINED
                if match.group("kind") == "load-if-defined"
                else LoadKind.CONDITIONAL_NOT_DEFINED
            )
            condition = (
                state is LoadSymbolState.DEFINED
                if kind is LoadKind.CONDITIONAL_DEFINED
                else state is LoadSymbolState.UNDEFINED
            )
            frame = _ConditionalFrame(
                kind=kind,
                symbol=symbol,
                parent_active=current_active,
                branch_active=current_active and condition,
                else_seen=False,
                line=index,
            )
            frames.append(frame)
            active_flags.append(False)
            contexts.append((kind, symbol))
            directive_edges.append(
                SourceEdge(
                    source_instance=source_instance,
                    target_path=None,
                    kind=kind,
                    location=SourceLocation(index, 1, str(path)),
                    condition_symbol=symbol,
                    active=frame.branch_active,
                )
            )
            continue

        if _ELSE_RE.fullmatch(stripped):
            if not frames:
                raise SourceGraphError(
                    "SOURCE-GRAPH-013",
                    "#else appears without an active conditional",
                    path=path,
                    line=index,
                    column=1,
                )
            frame = frames[-1]
            if frame.else_seen:
                raise SourceGraphError(
                    "SOURCE-GRAPH-014",
                    "duplicate #else in conditional block",
                    path=path,
                    line=index,
                    column=1,
                )

            frames[-1] = _ConditionalFrame(
                kind=frame.kind,
                symbol=frame.symbol,
                parent_active=frame.parent_active,
                branch_active=frame.parent_active and not frame.branch_active,
                else_seen=True,
                line=frame.line,
            )
            active_flags.append(False)
            contexts.append((frame.kind, frame.symbol))
            directive_edges.append(
                SourceEdge(
                    source_instance=source_instance,
                    target_path=None,
                    kind=LoadKind.CONDITIONAL_ELSE,
                    location=SourceLocation(index, 1, str(path)),
                    condition_symbol=frame.symbol,
                    active=frames[-1].branch_active,
                    condition_kind=frame.kind,
                )
            )
            continue

        if _END_RE.fullmatch(stripped):
            if not frames:
                raise SourceGraphError(
                    "SOURCE-GRAPH-015",
                    "#end-if appears without an active conditional",
                    path=path,
                    line=index,
                    column=1,
                )
            frame = frames.pop()
            active_flags.append(False)
            contexts.append((frame.kind, frame.symbol))
            directive_edges.append(
                SourceEdge(
                    source_instance=source_instance,
                    target_path=None,
                    kind=LoadKind.CONDITIONAL_ELSE,
                    location=SourceLocation(index, 1, str(path)),
                    condition_symbol=frame.symbol,
                    active=True,
                    condition_kind=frame.kind,
                )
            )
            continue

        if stripped.startswith("#load-if-defined") or stripped.startswith("#load-if-not-defined"):
            raise SourceGraphError(
                "SOURCE-GRAPH-012",
                "malformed preprocessor conditional directive",
                path=path,
                line=index,
                column=1,
            )
        if stripped.startswith("#else"):
            raise SourceGraphError(
                "SOURCE-GRAPH-012",
                "malformed #else directive",
                path=path,
                line=index,
                column=1,
            )
        if stripped.startswith("#end-if"):
            raise SourceGraphError(
                "SOURCE-GRAPH-012",
                "malformed #end-if directive",
                path=path,
                line=index,
                column=1,
            )

        active_flags.append(current_active)
        contexts.append(context)

    if frames:
        frame = frames[-1]
        raise SourceGraphError(
            "SOURCE-GRAPH-016",
            f"unterminated conditional started on line {frame.line}",
            path=path,
            line=frame.line,
            column=1,
        )

    masked = []
    for raw_line, active in zip(lines, active_flags):
        if active:
            masked.append(raw_line)
        else:
            masked.append(
                "".join(
                    "\n" if char == "\n" else "\r" if char == "\r" else " "
                    for char in raw_line
                )
            )
    return (
        "".join(masked),
        tuple(active_flags),
        tuple(contexts),
        tuple(directive_edges),
    )


def _scan_load_occurrences(
    source: str,
    *,
    path: Path,
) -> tuple[_LoadOccurrence, ...]:
    occurrences: list[_LoadOccurrence] = []

    for match in re.finditer(
        r"(?m)^[ \t]*#load(?:-random)?(?:[ \t].*)?$",
        source,
    ):
        line = source.count("\n", 0, match.start()) + 1
        column = match.start() - source.rfind("\n", 0, match.start())
        stripped = match.group(0).strip()

        if stripped.startswith("#load-random"):
            body = stripped[len("#load-random"):].strip()
            if not body or not re.search(r'"(?:\\.|[^"\\])*"', body):
                raise SourceGraphError(
                    "SOURCE-GRAPH-009",
                    "malformed #load-random directive",
                    path=path,
                    line=line,
                    column=column,
                )
            occurrences.append(
                _LoadOccurrence(
                    match.start(),
                    match.end(),
                    line,
                    column,
                    LoadKind.RANDOM,
                    None,
                    match.group(0),
                )
            )
            continue

        raw_match = _RAW_LOAD_RE.fullmatch(stripped)
        if raw_match is None:
            raise SourceGraphError(
                "SOURCE-GRAPH-009",
                "malformed #load directive; target must be quoted",
                path=path,
                line=line,
                column=column,
            )

        occurrences.append(
            _LoadOccurrence(
                match.start(),
                match.end(),
                line,
                column,
                LoadKind.RAW_LOAD,
                _decode_string(raw_match.group("target")),
                match.group(0),
            )
        )

    length = len(source)
    index = 0
    depth = 0
    in_string = False
    in_comment = False
    escape = False

    while index < length:
        char = source[index]

        if in_comment:
            if char == "\n":
                in_comment = False
            index += 1
            continue

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            index += 1
            continue

        if char == '"':
            in_string = True
            index += 1
            continue

        if char == "(":
            if depth == 0:
                try:
                    close = _find_balanced_form(source, index)
                    form = source[index:close]
                    parsed = _parse_load_form(form)
                except ValueError as exc:
                    line = source.count("\n", 0, index) + 1
                    column = index - source.rfind("\n", 0, index)
                    code = (
                        "SOURCE-GRAPH-010"
                        if "unterminated" in str(exc)
                        else "SOURCE-GRAPH-009"
                    )
                    raise SourceGraphError(
                        code,
                        str(exc),
                        path=path,
                        line=line,
                        column=column,
                    ) from exc

                if parsed is not None:
                    head, target = parsed
                    line = source.count("\n", 0, index) + 1
                    column = index - source.rfind("\n", 0, index)
                    occurrences.append(
                        _LoadOccurrence(
                            index,
                            close,
                            line,
                            column,
                            LoadKind.RANDOM if head == "load-random" else LoadKind.FILE,
                            target,
                            form,
                        )
                    )
                    index = close
                    continue

            depth += 1
        elif char == ")":
            if depth > 0:
                depth -= 1

        index += 1

    occurrences.sort(key=lambda item: (item.start, item.end))
    return tuple(occurrences)


def _find_balanced_form(source: str, start: int) -> int:
    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(source)):
        char = source[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index + 1

    raise ValueError("unterminated parenthesized load form")


def _parse_load_form(form: str) -> tuple[str, str | None] | None:
    body = form[1:-1].strip()
    match = re.fullmatch(r'load\s+"((?:\\.|[^"\\])*)"', body)
    if match:
        return "load", _decode_string(match.group(1))

    random_match = re.fullmatch(r"load-random\b(.*)", body, re.DOTALL)
    if random_match:
        random_body = random_match.group(1).strip()
        if not random_body or not re.search(r'"(?:\\.|[^"\\])*"', random_body):
            raise ValueError("malformed load-random directive")
        return "load-random", None

    if body.startswith("load"):
        raise ValueError("malformed load directive")

    return None


def _decode_string(body: str) -> str:
    result: list[str] = []
    index = 0
    while index < len(body):
        char = body[index]
        if char == "\\" and index + 1 < len(body):
            next_char = body[index + 1]
            if next_char in {'"', "\\"}:
                result.append(next_char)
                index += 2
                continue
        result.append(char)
        index += 1
    return "".join(result)
