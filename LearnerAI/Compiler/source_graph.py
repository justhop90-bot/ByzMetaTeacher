"""Effective native .per source graph resolution.

The graph resolves source assembly before the semantic demand parser. It owns
effective source order, load reachability, conditional branches, and physical
source provenance. Native package legality remains a backend concern.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, replace
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
    ConditionalElsePayload,
    ConditionalEndPayload,
    ConditionalOpenPayload,
    LoadEventPayload,
    LoadRandomEntry,
    LoadRandomEventPayload,
    SourceAssemblyEvent,
    SourceAssemblyEventId,
    SourceAssemblyEventKind,
    SourceAssemblyEventPayload,
    SourceEdgeId,
    SourceFile,
    SourceFileId,
    SourceInstance,
    SourceInstanceId,
    SourceLoadSyntax,
    SourceRange,
    structural_edge_id,
    structural_event_id,
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
class _LexicalOccurrence:
    start: int
    end: int
    kind: SourceAssemblyEventKind
    payload: SourceAssemblyEventPayload


_CONDITIONAL_RE = re.compile(
    r"^\s*#(?P<kind>load-if-defined|load-if-not-defined)\s+"
    r"(?P<symbol>[A-Za-z_][A-Za-z0-9_-]*)\s*$"
)
_ELSE_RE = re.compile(r"^\s*#else\s*$")
_END_RE = re.compile(r"^\s*#end-if\s*$")
_RAW_LOAD_RE = re.compile(
    r"""^\s*#load\s+"(?P<target>(?:\\.|[^"\\])*)"\s*$"""
)

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
        self._events: list[SourceAssemblyEvent] = []
        self._edges: list[SourceEdge] = []
        self._slices: list[EffectiveSourceSlice] = []
        self._files_by_id: dict[SourceFileId, SourceFile] = {}

    def resolve(self, request: SourceGraphRequest) -> EffectiveSourceGraph:
        self._instances = []
        self._events = []
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
            events=tuple(self._events),
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
        events, masked = _parse_assembly_events(
            physical,
            symbols,
            self.MAX_CONDITIONAL_DEPTH,
            instance.identity,
        )
        self._events.extend(events)

        event_ids: list[SourceAssemblyEventId] = []
        cursor = 0

        for event in events:
            event_ids.append(event.identity)
            if event.kind not in {
                SourceAssemblyEventKind.LOAD,
                SourceAssemblyEventKind.LOAD_RANDOM,
            }:
                continue

            self._append_slice(
                instance,
                masked[cursor:event.span.start_offset],
                cursor,
                physical,
            )
            cursor = event.span.end_offset

            active = event.condition_before.evaluate(symbols)
            target_source: SourceFile | None = None
            target_text: str | None = None
            load_kind: LoadKind

            if event.kind is SourceAssemblyEventKind.LOAD:
                payload = event.payload
                assert isinstance(payload, LoadEventPayload)
                target_text = payload.target_text
                load_kind = (
                    LoadKind.RAW_LOAD
                    if payload.syntax is SourceLoadSyntax.RAW_LOAD
                    else LoadKind.FILE
                )
            else:
                payload = event.payload
                assert isinstance(payload, LoadRandomEventPayload)
                target_text = None
                load_kind = LoadKind.RANDOM

            if event.kind is SourceAssemblyEventKind.LOAD:
                target_source = self._load_unit(
                    Path(target_text),
                    containing_source=physical.path,
                    search_roots=search_roots,
                    error_line=event.span.start_line,
                    error_column=event.span.start_column,
                )
            elif active:
                if not allow_load_random:
                    raise SourceGraphError(
                        "SOURCE-GRAPH-007",
                        (
                            "load-random requires an explicit materialized "
                            "selection policy for deterministic compilation"
                        ),
                        path=physical.path,
                        line=event.span.start_line,
                        column=event.span.start_column,
                    )
                raise SourceGraphError(
                    "SOURCE-GRAPH-007",
                    (
                        "load-random materialization is not implemented; "
                        "deterministic compilation requires an explicit "
                        "selection policy"
                    ),
                    path=physical.path,
                    line=event.span.start_line,
                    column=event.span.start_column,
                )

            condition = event.condition_before
            edge_id = structural_edge_id(
                source=instance.identity,
                span=event.span,
                kind=load_kind,
                condition=condition,
                target_text=target_text,
            )
            child: SourceInstance | None = None

            if active and event.kind is SourceAssemblyEventKind.LOAD:
                if target_source is None:
                    raise SourceGraphError(
                        "SOURCE-GRAPH-001",
                        f"missing load target '{target_text}'",
                        path=physical.path,
                        line=event.span.start_line,
                        column=event.span.start_column,
                    )
                child = self._expand_instance(
                    target_source,
                    parent=instance,
                    via_edge=edge_id,
                    search_roots=search_roots,
                    symbols=symbols,
                    allow_load_random=allow_load_random,
                )

            edge = SourceEdge(
                identity=edge_id,
                source=instance.identity,
                target=(
                    target_source.identity
                    if target_source is not None
                    else None
                ),
                child=child.identity if child is not None else None,
                kind=load_kind,
                span=event.span,
                condition=condition,
                active=active,
                event=event.identity,
                target_text=target_text,
            )
            self._edges.append(edge)

            event_index = self._events.index(event)
            self._events[event_index] = replace(event, edge=edge.identity)

        self._append_slice(
            instance,
            masked[cursor:],
            cursor,
            physical,
        )
        self._instances[self._instances.index(instance)] = replace(
            instance,
            events=tuple(event_ids),
        )
        return replace(instance, events=tuple(event_ids))

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


def _parse_assembly_events(
    source: SourceFile,
    symbols: LoadSymbolEnvironment,
    max_depth: int,
    source_instance: SourceInstanceId,
) -> tuple[tuple[SourceAssemblyEvent, ...], str]:
    occurrences = _scan_assembly_occurrences(source.text, path=source.path)
    frames: list[
        tuple[
            SourceAssemblyEventId,
            ConditionPredicate,
            SourceAssemblyEventId | None,
        ]
    ] = []
    events: list[SourceAssemblyEvent] = []

    for ordinal, occurrence in enumerate(occurrences):
        span = _segment_range(source, occurrence.start, occurrence.end)
        before = (
            ConditionContext(tuple(frame[1] for frame in frames))
        )
        after = before
        payload = occurrence.payload

        if occurrence.kind is SourceAssemblyEventKind.CONDITIONAL_OPEN:
            assert isinstance(payload, ConditionalOpenPayload)
            if before.depth >= max_depth:
                raise SourceGraphError(
                    "SOURCE-GRAPH-005",
                    f"conditional nesting exceeds {max_depth}",
                    path=source.path,
                    line=span.start_line,
                    column=span.start_column,
                )
            if symbols.state(payload.predicate.symbol) is None:
                raise SourceGraphError(
                    "SOURCE-GRAPH-006",
                    (
                        f"conditional load symbol "
                        f"'{payload.predicate.symbol}' is unresolved"
                    ),
                    path=source.path,
                    line=span.start_line,
                    column=span.start_column,
                )
            after = before.append(payload.predicate)
            event_id = structural_event_id(
                source_instance=source_instance,
                span=span,
                kind=occurrence.kind,
                condition_before=before,
                condition_after=after,
                payload=payload,
            )
            event = SourceAssemblyEvent(
                identity=event_id,
                source_instance=source_instance,
                kind=occurrence.kind,
                span=span,
                lexical_ordinal=ordinal,
                condition_before=before,
                condition_after=after,
                payload=payload,
            )
            events.append(event)
            frames.append((event_id, payload.predicate, None))
            continue

        if occurrence.kind is SourceAssemblyEventKind.CONDITIONAL_ELSE:
            if not frames:
                raise SourceGraphError(
                    "SOURCE-GRAPH-013",
                    "#else appears without an active conditional",
                    path=source.path,
                    line=span.start_line,
                    column=span.start_column,
                )
            open_event, predicate, else_event = frames[-1]
            if else_event is not None:
                raise SourceGraphError(
                    "SOURCE-GRAPH-014",
                    "duplicate #else in conditional block",
                    path=source.path,
                    line=span.start_line,
                    column=span.start_column,
                )
            payload = ConditionalElsePayload(open_event=open_event)
            after = before.complement_last()
            event_id = structural_event_id(
                source_instance=source_instance,
                span=span,
                kind=occurrence.kind,
                condition_before=before,
                condition_after=after,
                payload=payload,
            )
            event = SourceAssemblyEvent(
                identity=event_id,
                source_instance=source_instance,
                kind=occurrence.kind,
                span=span,
                lexical_ordinal=ordinal,
                condition_before=before,
                condition_after=after,
                payload=payload,
            )
            events.append(event)
            complemented = after.predicates[-1]
            frames[-1] = (open_event, complemented, event_id)
            continue

        if occurrence.kind is SourceAssemblyEventKind.CONDITIONAL_END:
            if not frames:
                raise SourceGraphError(
                    "SOURCE-GRAPH-015",
                    "#end-if appears without an active conditional",
                    path=source.path,
                    line=span.start_line,
                    column=span.start_column,
                )
            open_event, _predicate, else_event = frames[-1]
            payload = ConditionalEndPayload(
                open_event=open_event,
                else_event=else_event,
            )
            after = before.pop_last()
            event_id = structural_event_id(
                source_instance=source_instance,
                span=span,
                kind=occurrence.kind,
                condition_before=before,
                condition_after=after,
                payload=payload,
            )
            event = SourceAssemblyEvent(
                identity=event_id,
                source_instance=source_instance,
                kind=occurrence.kind,
                span=span,
                lexical_ordinal=ordinal,
                condition_before=before,
                condition_after=after,
                payload=payload,
            )
            events.append(event)
            frames.pop()
            continue

        event_id = structural_event_id(
            source_instance=source_instance,
            span=span,
            kind=occurrence.kind,
            condition_before=before,
            condition_after=after,
            payload=payload,
        )
        events.append(
            SourceAssemblyEvent(
                identity=event_id,
                source_instance=source_instance,
                kind=occurrence.kind,
                span=span,
                lexical_ordinal=ordinal,
                condition_before=before,
                condition_after=after,
                payload=payload,
            )
        )

    if frames:
        frame = frames[-1]
        raise SourceGraphError(
            "SOURCE-GRAPH-016",
            "unterminated conditional block",
            path=source.path,
            line=next(
                (
                    item.span.start_line
                    for item in events
                    if item.identity == frame[0]
                ),
                1,
            ),
            column=1,
        )

    masked = _mask_inactive_lines(source, events, symbols)
    return tuple(events), masked


def _scan_assembly_occurrences(
    source: str,
    *,
    path: Path,
) -> tuple[_LexicalOccurrence, ...]:
    occurrences: list[_LexicalOccurrence] = []

    for match in re.finditer(
        r"(?m)^[ 	]*#(?:load-if-defined|load-if-not-defined|else|end-if|load-random|load)(?:[ 	].*)?$",
        source,
    ):
        line = source.count("\n", 0, match.start()) + 1
        column = match.start() - source.rfind("\n", 0, match.start())
        stripped = match.group(0).strip()

        conditional = _CONDITIONAL_RE.fullmatch(stripped)
        if conditional:
            expected = (
                LoadSymbolState.DEFINED
                if conditional.group("kind") == "load-if-defined"
                else LoadSymbolState.UNDEFINED
            )
            occurrences.append(
                _LexicalOccurrence(
                    start=match.start(),
                    end=match.end(),
                    kind=SourceAssemblyEventKind.CONDITIONAL_OPEN,
                    payload=ConditionalOpenPayload(
                        predicate=ConditionPredicate(
                            conditional.group("symbol"),
                            expected,
                        )
                    ),
                )
            )
            continue

        if _ELSE_RE.fullmatch(stripped):
            occurrences.append(
                _LexicalOccurrence(
                    start=match.start(),
                    end=match.end(),
                    kind=SourceAssemblyEventKind.CONDITIONAL_ELSE,
                    payload=ConditionalElsePayload(
                        open_event=SourceAssemblyEventId("__parser_pending__"),
                    ),
                )
            )
            continue

        if _END_RE.fullmatch(stripped):
            occurrences.append(
                _LexicalOccurrence(
                    start=match.start(),
                    end=match.end(),
                    kind=SourceAssemblyEventKind.CONDITIONAL_END,
                    payload=ConditionalEndPayload(
                        open_event=SourceAssemblyEventId("__parser_pending__"),
                        else_event=None,
                    ),
                )
            )
            continue

        if stripped.startswith("#load-random"):
            body = stripped[len("#load-random"):].strip()
            entries = _parse_random_entries(body, path=path, line=line, column=column)
            occurrences.append(
                _LexicalOccurrence(
                    start=match.start(),
                    end=match.end(),
                    kind=SourceAssemblyEventKind.LOAD_RANDOM,
                    payload=LoadRandomEventPayload(
                        syntax=SourceLoadSyntax.RAW_LOAD,
                        entries=entries,
                    ),
                )
            )
            continue

        if stripped.startswith("#load-if-defined") or stripped.startswith(
            "#load-if-not-defined"
        ):
            raise SourceGraphError(
                "SOURCE-GRAPH-012",
                "malformed preprocessor conditional directive",
                path=path,
                line=line,
                column=column,
            )
        if stripped.startswith("#else"):
            raise SourceGraphError(
                "SOURCE-GRAPH-012",
                "malformed #else directive",
                path=path,
                line=line,
                column=column,
            )
        if stripped.startswith("#end-if"):
            raise SourceGraphError(
                "SOURCE-GRAPH-012",
                "malformed #end-if directive",
                path=path,
                line=line,
                column=column,
            )

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
            _LexicalOccurrence(
                start=match.start(),
                end=match.end(),
                kind=SourceAssemblyEventKind.LOAD,
                payload=LoadEventPayload(
                    syntax=SourceLoadSyntax.RAW_LOAD,
                    target_text=_decode_string(raw_match.group("target")),
                ),
            )
        )

    length = len(source)
    index = 0
    depth = 0
    in_string = False
    escape = False

    while index < length:
        char = source[index]
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
                    parsed = _parse_load_form(form, path=path)
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
                    kind, payload = parsed
                    occurrences.append(
                        _LexicalOccurrence(
                            start=index,
                            end=close,
                            kind=kind,
                            payload=payload,
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
    seen_spans: set[tuple[int, int]] = set()
    unique: list[_LexicalOccurrence] = []
    for occurrence in occurrences:
        key = (occurrence.start, occurrence.end)
        if key in seen_spans:
            continue
        seen_spans.add(key)
        unique.append(occurrence)
    return tuple(unique)


def _parse_load_form(
    form: str,
    *,
    path: Path,
) -> tuple[SourceAssemblyEventKind, SourceAssemblyEventPayload] | None:
    body = form[1:-1].strip()
    match = re.fullmatch(r'load\s+"((?:\\.|[^"\\])*)"', body)
    if match:
        return (
            SourceAssemblyEventKind.LOAD,
            LoadEventPayload(
                syntax=SourceLoadSyntax.PAREN_LOAD,
                target_text=_decode_string(match.group(1)),
            ),
        )

    random_match = re.fullmatch(r"load-random\b(.*)", body, re.DOTALL)
    if random_match:
        entries = _parse_random_entries(
            random_match.group(1).strip(),
            path=path,
            line=1,
            column=1,
        )
        return (
            SourceAssemblyEventKind.LOAD_RANDOM,
            LoadRandomEventPayload(
                syntax=SourceLoadSyntax.PAREN_LOAD,
                entries=entries,
            ),
        )

    if body.startswith("load"):
        raise ValueError("malformed load directive")

    return None


def _parse_random_entries(
    body: str,
    *,
    path: Path,
    line: int,
    column: int,
) -> tuple[LoadRandomEntry, ...]:
    if not body:
        raise SourceGraphError(
            "SOURCE-GRAPH-009",
            "malformed load-random directive",
            path=path,
            line=line,
            column=column,
        )

    entries: list[LoadRandomEntry] = []
    index = 0
    token_re = re.compile(
        r"[ \t]*"
        r"(?:(?P<weight>[0-9]+)[ \t]+)?"
        r'"(?P<target>(?:\\.|[^"\\])*)"'
    )
    while index < len(body):
        match = token_re.match(body, index)
        if match is None:
            raise SourceGraphError(
                "SOURCE-GRAPH-009",
                "malformed load-random directive; entries require an optional weight and quoted target",
                path=path,
                line=line,
                column=column,
            )
        entries.append(
            LoadRandomEntry(
                target_text=_decode_string(match.group("target")),
                weight=(
                    int(match.group("weight"))
                    if match.group("weight") is not None
                    else None
                ),
            )
        )
        index = match.end()

    if not entries:
        raise SourceGraphError(
            "SOURCE-GRAPH-009",
            "malformed load-random directive",
            path=path,
            line=line,
            column=column,
        )
    return tuple(entries)


def _mask_inactive_lines(
    source: SourceFile,
    events: tuple[SourceAssemblyEvent, ...],
    symbols: LoadSymbolEnvironment,
) -> str:
    lines = source.text.splitlines(keepends=True)
    conditional_by_line = {
        event.span.start_line: event
        for event in events
        if event.kind
        in {
            SourceAssemblyEventKind.CONDITIONAL_OPEN,
            SourceAssemblyEventKind.CONDITIONAL_ELSE,
            SourceAssemblyEventKind.CONDITIONAL_END,
        }
    }

    context = ConditionContext()
    masked: list[str] = []
    for number, raw_line in enumerate(lines, 1):
        event = conditional_by_line.get(number)
        if event is not None:
            masked.append(
                "".join(
                    "\n" if char == "\n"
                    else "\r" if char == "\r"
                    else " "
                    for char in raw_line
                )
            )
            context = event.condition_after
            continue

        active = context.evaluate(symbols)
        if active:
            masked.append(raw_line)
        else:
            masked.append(
                "".join(
                    "\n" if char == "\n"
                    else "\r" if char == "\r"
                    else " "
                    for char in raw_line
                )
            )
    return "".join(masked)


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
