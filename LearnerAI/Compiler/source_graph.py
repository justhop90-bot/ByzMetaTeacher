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
from pathlib import Path

from .ast import SourceLocation
from .diagnostics import DiagnosticSeverity, DiagnosticSource, SemanticDiagnostic
from .errors import CompileError
from .ir.source_graph import (
    ConditionContext,
    ConditionPredicate,
    EffectiveSourceGraph,
    EffectiveSourceSlice,
    LoadKind,
    LoadSymbolEnvironment,
    LoadSymbolState,
    SourceEdge,
    SourceEdgeId,
    SourceFile,
    SourceFileId,
    SourceInstance,
    SourceInstanceId,
    SourceRange,
    structural_edge_id,
    structural_instance_id,
)


@dataclass(frozen=True)
class SourceGraphRequest:
    entrypoint: Path
    search_roots: tuple[Path, ...] = ()
    load_symbols: LoadSymbolEnvironment = field(default_factory=LoadSymbolEnvironment)
    allow_load_random: bool = False


SourceUnit = SourceFile


@dataclass(frozen=True)
class _ConditionalFrame:
    predicate: ConditionPredicate
    parent_active: bool
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
        self._instances: list[SourceInstance] = []
        self._edges: list[SourceEdge] = []
        self._slices: list[EffectiveSourceSlice] = []
        self._files_by_id: dict[SourceFileId, SourceFile] = {}

    def resolve(self, request: SourceGraphRequest) -> EffectiveSourceGraph:
        self._instances = []
        self._edges = []
        self._slices = []
        self._files_by_id = {}

        search_roots = tuple(path.resolve() for path in request.search_roots)
        entrypoint = request.entrypoint.resolve()
        root_file = self._load_unit(
            entrypoint,
            containing_source=entrypoint,
            search_roots=search_roots,
            error_line=1,
            error_column=1,
        )
        root = self._expand_instance(
            root_file,
            parent=None,
            via_edge=None,
            search_roots=search_roots,
            symbols=request.load_symbols,
            allow_load_random=request.allow_load_random,
        )

        return EffectiveSourceGraph.build(
            root=root,
            files=tuple(self._files_by_id.values()),
            instances=tuple(self._instances),
            edges=tuple(self._edges),
            slices=tuple(self._slices),
            symbols=request.load_symbols,
        )

    def _load_unit(
        self,
        target: Path,
        *,
        containing_source: Path,
        search_roots: tuple[Path, ...],
        error_line: int,
        error_column: int,
    ) -> SourceFile:
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
        try:
            text = resolved.read_text(encoding="utf-8")
        except OSError as exc:
            raise SourceGraphError(
                "SOURCE-GRAPH-001",
                f"unable to read load target '{target}': {exc}",
                path=containing_source,
                line=error_line,
                column=error_column,
            ) from exc
        source = SourceFile.from_path_text(resolved, text)
        self._files_by_id[source.identity] = source
        return source

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
        physical: SourceFile,
        *,
        parent: SourceInstance | None,
        via_edge: SourceEdgeId | None,
    ) -> SourceInstance:
        occurrence = sum(
            1 for item in self._instances if item.source == physical.identity
        )
        identity = structural_instance_id(
            source=physical.identity,
            parent=parent.identity if parent else None,
            via_edge=via_edge,
        )
        ancestry = (
            (physical.identity,)
            if parent is None
            else parent.ancestry + (physical.identity,)
        )
        instance = SourceInstance(
            identity=identity,
            physical=physical,
            parent=parent.identity if parent else None,
            via_edge=via_edge,
            ancestry=ancestry,
            depth=0 if parent is None else parent.depth + 1,
            occurrence=occurrence,
        )
        self._instances.append(instance)
        return instance

    def _expand_instance(
        self,
        physical: SourceFile,
        *,
        parent: SourceInstance | None,
        via_edge: SourceEdgeId | None,
        search_roots: tuple[Path, ...],
        symbols: LoadSymbolEnvironment,
        allow_load_random: bool,
    ) -> SourceInstance:
        if parent is not None and physical.path in {
            source.path for source in parent.ancestry
        }:
            cycle = " -> ".join(
                str(source.path)
                for source in (*parent.ancestry, physical.identity)
            )
            raise SourceGraphError(
                "SOURCE-GRAPH-002",
                f"load cycle detected: {cycle}",
                path=physical.path,
                line=1,
                column=1,
            )
        if parent is not None and parent.depth + 1 > self.MAX_LOAD_DEPTH:
            raise SourceGraphError(
                "SOURCE-GRAPH-003",
                f"nested load depth exceeds {self.MAX_LOAD_DEPTH}",
                path=physical.path,
                line=1,
                column=1,
            )

        instance = self._new_instance(
            physical,
            parent=parent,
            via_edge=via_edge,
        )
        masked, active_lines, condition_contexts, directive_edges = _mask_conditionals(
            physical,
            symbols,
            self.MAX_CONDITIONAL_DEPTH,
            instance.identity,
        )
        self._edges.extend(directive_edges)

        occurrences = _scan_load_occurrences(physical.text, path=physical.path)
        cursor = 0

        for lexical_order, occurrence in enumerate(occurrences):
            context = condition_contexts[occurrence.line - 1]
            active = active_lines[occurrence.line - 1]
            physical_range = _segment_range(
                physical,
                occurrence.start,
                occurrence.end,
            )
            self._append_slice(
                instance,
                masked[cursor:occurrence.start],
                cursor,
                physical,
            )
            cursor = occurrence.end

            target_source = None
            if occurrence.target is not None:
                target_source = self._load_unit(
                    Path(occurrence.target),
                    containing_source=physical.path,
                    search_roots=search_roots,
                    error_line=occurrence.line,
                    error_column=occurrence.column,
                )

            condition = context or ConditionContext()
            edge_id = structural_edge_id(
                source=instance.identity,
                span=physical_range,
                kind=occurrence.kind,
                condition=condition,
                target_text=occurrence.target,
            )

            if not active:
                self._edges.append(
                    SourceEdge(
                        identity=edge_id,
                        source=instance.identity,
                        target=target_source.identity if target_source else None,
                        child=None,
                        kind=occurrence.kind,
                        span=physical_range,
                        condition=condition,
                        active=False,
                        lexical_order=lexical_order,
                        target_text=occurrence.target,
                    )
                )
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

            if target_source is None:
                raise SourceGraphError(
                    "SOURCE-GRAPH-001",
                    f"missing load target '{occurrence.target}'",
                    path=physical.path,
                    line=occurrence.line,
                    column=occurrence.column,
                )

            child = self._expand_instance(
                target_source,
                parent=instance,
                via_edge=edge_id,
                search_roots=search_roots,
                symbols=symbols,
                allow_load_random=allow_load_random,
            )
            self._edges.append(
                SourceEdge(
                    identity=edge_id,
                    source=instance.identity,
                    target=target_source.identity,
                    child=child.identity,
                    kind=occurrence.kind,
                    span=physical_range,
                    condition=condition,
                    active=True,
                    lexical_order=lexical_order,
                    target_text=occurrence.target,
                )
            )

        self._append_slice(
            instance,
            masked[cursor:],
            cursor,
            physical,
        )
        return instance

    def _append_slice(
        self,
        instance: SourceInstance,
        text: str,
        start_offset: int,
        physical: SourceFile,
    ) -> None:
        if not text.strip():
            return
        end_offset = start_offset + len(text)
        self._slices.append(
            EffectiveSourceSlice(
                ordinal=len(self._slices),
                instance=instance.identity,
                physical_range=_segment_range(physical, start_offset, end_offset),
                text=text,
            )
        )

def _segment_range(source: SourceFile, start: int, end: int) -> SourceRange:
    text = source.text
    prefix = text[:start]
    segment = text[start:end]
    start_line = prefix.count("\n") + 1
    previous_newline = prefix.rfind("\n")
    start_column = start + 1 if previous_newline < 0 else start - previous_newline
    if not segment:
        end_line = start_line
        end_column = start_column
    else:
        end_line = start_line + segment.count("\n")
        if "\n" in segment:
            end_column = len(segment.rsplit("\n", 1)[-1]) + 1
        else:
            end_column = start_column + len(segment) - 1
    return SourceRange(
        source=source.identity,
        start_offset=start,
        end_offset=end,
        start_line=start_line,
        start_column=start_column,
        end_line=end_line,
        end_column=max(1, end_column),
    )


def _line_range(source: SourceFile, line: int) -> SourceRange:
    lines = source.text.splitlines(keepends=True)
    if line < 1 or line > len(lines):
        raise ValueError("line outside source")
    start = sum(len(item) for item in lines[: line - 1])
    end = start + len(lines[line - 1])
    return _segment_range(source, start, end)


def _mask_conditionals(
    source: SourceFile,
    symbols: LoadSymbolEnvironment,
    max_depth: int,
    source_instance: SourceInstanceId,
) -> tuple[
    str,
    tuple[bool, ...],
    tuple[ConditionContext | None, ...],
    tuple[SourceEdge, ...],
]:
    lines = source.text.splitlines(keepends=True)
    active_flags: list[bool] = []
    contexts: list[ConditionContext | None] = []
    frames: list[_ConditionalFrame] = []
    directive_edges: list[SourceEdge] = []

    def context_now() -> ConditionContext:
        return ConditionContext(tuple(frame.predicate for frame in frames))

    for index, raw_line in enumerate(lines, 1):
        stripped = raw_line.strip()
        before = context_now()
        current_active = before.evaluate(symbols)

        match = _CONDITIONAL_RE.fullmatch(stripped)
        if match:
            if len(frames) >= max_depth:
                raise SourceGraphError(
                    "SOURCE-GRAPH-005",
                    f"conditional nesting exceeds {max_depth}",
                    path=source.path,
                    line=index,
                    column=1,
                )
            symbol = match.group("symbol")
            if symbols.state(symbol) is None:
                raise SourceGraphError(
                    "SOURCE-GRAPH-006",
                    f"conditional load symbol '{symbol}' is unresolved",
                    path=source.path,
                    line=index,
                    column=1,
                )
            expected = (
                LoadSymbolState.DEFINED
                if match.group("kind") == "load-if-defined"
                else LoadSymbolState.UNDEFINED
            )
            predicate = ConditionPredicate(symbol, expected)
            frames.append(
                _ConditionalFrame(
                    predicate=predicate,
                    parent_active=current_active,
                    else_seen=False,
                    line=index,
                )
            )
            context = context_now()
            active = context.evaluate(symbols)
            kind = (
                LoadKind.CONDITIONAL_DEFINED
                if expected is LoadSymbolState.DEFINED
                else LoadKind.CONDITIONAL_NOT_DEFINED
            )
            span = _line_range(source, index)
            directive_edges.append(
                SourceEdge(
                    identity=structural_edge_id(
                        source=source_instance,
                        span=span,
                        kind=kind,
                        condition=context,
                        target_text=symbol,
                    ),
                    source=source_instance,
                    target=None,
                    child=None,
                    kind=kind,
                    span=span,
                    condition=context,
                    active=active,
                    lexical_order=index,
                    target_text=symbol,
                )
            )
            active_flags.append(False)
            contexts.append(context)
            continue

        if _ELSE_RE.fullmatch(stripped):
            if not frames:
                raise SourceGraphError(
                    "SOURCE-GRAPH-013",
                    "#else appears without an active conditional",
                    path=source.path,
                    line=index,
                    column=1,
                )
            frame = frames[-1]
            if frame.else_seen:
                raise SourceGraphError(
                    "SOURCE-GRAPH-014",
                    "duplicate #else in conditional block",
                    path=source.path,
                    line=index,
                    column=1,
                )
            frames[-1] = _ConditionalFrame(
                predicate=ConditionPredicate(
                    frame.predicate.symbol,
                    LoadSymbolState.UNDEFINED
                    if frame.predicate.expected is LoadSymbolState.DEFINED
                    else LoadSymbolState.DEFINED,
                ),
                parent_active=frame.parent_active,
                else_seen=True,
                line=frame.line,
            )
            context = context_now()
            active = context.evaluate(symbols)
            span = _line_range(source, index)
            directive_edges.append(
                SourceEdge(
                    identity=structural_edge_id(
                        source=source_instance,
                        span=span,
                        kind=LoadKind.CONDITIONAL_ELSE,
                        condition=context,
                        target_text=frame.predicate.symbol,
                    ),
                    source=source_instance,
                    target=None,
                    child=None,
                    kind=LoadKind.CONDITIONAL_ELSE,
                    span=span,
                    condition=context,
                    active=active,
                    lexical_order=index,
                    target_text=frame.predicate.symbol,
                )
            )
            active_flags.append(False)
            contexts.append(context)
            continue

        if _END_RE.fullmatch(stripped):
            if not frames:
                raise SourceGraphError(
                    "SOURCE-GRAPH-015",
                    "#end-if appears without an active conditional",
                    path=source.path,
                    line=index,
                    column=1,
                )
            frame = frames[-1]
            context = context_now()
            active = context.evaluate(symbols)
            frames.pop()
            span = _line_range(source, index)
            directive_edges.append(
                SourceEdge(
                    identity=structural_edge_id(
                        source=source_instance,
                        span=span,
                        kind=LoadKind.CONDITIONAL_ELSE,
                        condition=context,
                        target_text=frame.predicate.symbol,
                    ),
                    source=source_instance,
                    target=None,
                    child=None,
                    kind=LoadKind.CONDITIONAL_ELSE,
                    span=span,
                    condition=context,
                    active=active,
                    lexical_order=index,
                    target_text=frame.predicate.symbol,
                )
            )
            active_flags.append(False)
            contexts.append(context)
            continue

        if stripped.startswith("#load-if-defined") or stripped.startswith("#load-if-not-defined"):
            raise SourceGraphError(
                "SOURCE-GRAPH-012",
                "malformed preprocessor conditional directive",
                path=source.path,
                line=index,
                column=1,
            )
        if stripped.startswith("#else"):
            raise SourceGraphError(
                "SOURCE-GRAPH-012",
                "malformed #else directive",
                path=source.path,
                line=index,
                column=1,
            )
        if stripped.startswith("#end-if"):
            raise SourceGraphError(
                "SOURCE-GRAPH-012",
                "malformed #end-if directive",
                path=source.path,
                line=index,
                column=1,
            )

        active_flags.append(current_active)
        contexts.append(before if frames else None)

    if frames:
        frame = frames[-1]
        raise SourceGraphError(
            "SOURCE-GRAPH-016",
            f"unterminated conditional started on line {frame.line}",
            path=source.path,
            line=frame.line,
            column=1,
        )

    masked: list[str] = []
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
