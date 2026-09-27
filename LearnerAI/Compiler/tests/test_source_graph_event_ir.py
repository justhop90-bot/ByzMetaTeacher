from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from Compiler.ir.source_graph import (
    ConditionalElsePayload,
    ConditionalEndPayload,
    ConditionalOpenPayload,
    LoadEventPayload,
    LoadRandomEventPayload,
    LoadSymbolEnvironment,
    LoadSymbolState,
    SourceAssemblyEventKind,
    SourceLoadSyntax,
)
from Compiler.semantic.source_graph_validation import (
    SourceGraphDiagnosticCode,
    validate_effective_source_graph,
)
from Compiler.source_graph import SourceGraphRequest, SourceGraphResolver


class SourceAssemblyEventTests(unittest.TestCase):
    def _write_linear_conditional(self, root: Path) -> Path:
        (root / "defined.perdsl").write_text("defined-body\n", encoding="utf-8")
        (root / "undefined.perdsl").write_text(
            "undefined-body\n",
            encoding="utf-8",
        )
        (root / "tail.perdsl").write_text("tail-body\n", encoding="utf-8")
        entry = root / "root.perdsl"
        entry.write_text(
            "#load-if-defined TEST\n"
            '(load "defined.perdsl")\n'
            "#else\n"
            '(load "undefined.perdsl")\n'
            "#end-if\n"
            '(load "tail.perdsl")\n',
            encoding="utf-8",
        )
        return entry

    def test_events_are_one_authoritative_lexical_stream(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry = self._write_linear_conditional(Path(tmp))
            graph = SourceGraphResolver().resolve(
                SourceGraphRequest(
                    entrypoint=entry,
                    load_symbols=LoadSymbolEnvironment(
                        (("TEST", LoadSymbolState.DEFINED),)
                    ),
                )
            )
            root_events = [
                event
                for event in graph.events
                if event.source_instance == graph.root.identity
            ]
            self.assertEqual(
                [event.kind for event in root_events],
                [
                    SourceAssemblyEventKind.CONDITIONAL_OPEN,
                    SourceAssemblyEventKind.LOAD,
                    SourceAssemblyEventKind.CONDITIONAL_ELSE,
                    SourceAssemblyEventKind.LOAD,
                    SourceAssemblyEventKind.CONDITIONAL_END,
                    SourceAssemblyEventKind.LOAD,
                ],
            )
            self.assertEqual(
                [event.lexical_ordinal for event in root_events],
                list(range(6)),
            )
            load_ordinals = [
                event.lexical_ordinal
                for event in root_events
                if event.kind is SourceAssemblyEventKind.LOAD
            ]
            self.assertEqual(load_ordinals, [1, 3, 5])

    def test_condition_before_after_are_authoritative_stack_transitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry = self._write_linear_conditional(Path(tmp))
            graph = SourceGraphResolver().resolve(
                SourceGraphRequest(
                    entrypoint=entry,
                    load_symbols=LoadSymbolEnvironment(
                        (("TEST", LoadSymbolState.DEFINED),)
                    ),
                )
            )
            events = [
                event
                for event in graph.events
                if event.source_instance == graph.root.identity
            ]
            opened, defined_load, else_event, undefined_load, ended, tail = events

            self.assertIsInstance(opened.payload, ConditionalOpenPayload)
            self.assertEqual(opened.condition_before.depth, 0)
            self.assertEqual(opened.condition_after.depth, 1)
            self.assertEqual(opened.condition_after.predicates[0].symbol, "TEST")
            self.assertIs(
                opened.condition_after.predicates[0].expected,
                LoadSymbolState.DEFINED,
            )

            self.assertEqual(defined_load.condition_before, opened.condition_after)
            self.assertEqual(defined_load.condition_after, opened.condition_after)

            self.assertIsInstance(else_event.payload, ConditionalElsePayload)
            self.assertEqual(
                else_event.payload.open_event,
                opened.identity,
            )
            self.assertIs(
                else_event.condition_after.predicates[0].expected,
                LoadSymbolState.UNDEFINED,
            )
            self.assertEqual(
                undefined_load.condition_before,
                else_event.condition_after,
            )

            self.assertIsInstance(ended.payload, ConditionalEndPayload)
            self.assertEqual(ended.payload.open_event, opened.identity)
            self.assertEqual(ended.payload.else_event, else_event.identity)
            self.assertEqual(ended.condition_after.depth, 0)
            self.assertEqual(tail.condition_before.depth, 0)

    def test_load_event_and_edge_back_references_are_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry = self._write_linear_conditional(Path(tmp))
            graph = SourceGraphResolver().resolve(
                SourceGraphRequest(
                    entrypoint=entry,
                    load_symbols=LoadSymbolEnvironment(
                        (("TEST", LoadSymbolState.DEFINED),)
                    ),
                )
            )
            events = {
                event.identity: event
                for event in graph.events
            }
            for edge in graph.edges:
                event = events[edge.event]
                self.assertIs(event.edge, edge.identity)
                self.assertEqual(edge.source, event.source_instance)
                self.assertEqual(edge.span, event.span)
                self.assertIn(
                    event.kind,
                    {
                        SourceAssemblyEventKind.LOAD,
                        SourceAssemblyEventKind.LOAD_RANDOM,
                    },
                )

    def test_event_spans_are_source_exact_and_non_overlapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry = self._write_linear_conditional(Path(tmp))
            graph = SourceGraphResolver().resolve(
                SourceGraphRequest(
                    entrypoint=entry,
                    load_symbols=LoadSymbolEnvironment(
                        (("TEST", LoadSymbolState.DEFINED),)
                    ),
                )
            )
            source = graph.root.physical
            events = sorted(
                [
                    event
                    for event in graph.events
                    if event.source_instance == graph.root.identity
                ],
                key=lambda item: item.lexical_ordinal,
            )
            for left, right in zip(events, events[1:]):
                self.assertLess(left.span.start_offset, right.span.start_offset)
                self.assertLessEqual(left.span.end_offset, right.span.start_offset)
            for event in events:
                self.assertEqual(event.span.source, source.identity)
                self.assertEqual(
                    source.text[event.span.start_offset:event.span.end_offset]
                    .strip()
                    .splitlines()[0],
                    source.text[
                        event.span.start_offset:event.span.end_offset
                    ].strip().splitlines()[0],
                )

    def test_comment_parenthesized_load_is_not_treated_as_assembly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = root / "root.perdsl"
            entry.write_text(
                '; (load "missing.perdsl")\n'
                "body\n",
                encoding="utf-8",
            )
            graph = SourceGraphResolver().resolve(
                SourceGraphRequest(entrypoint=entry)
            )
            self.assertFalse(
                any(
                    event.kind is SourceAssemblyEventKind.LOAD
                    for event in graph.events
                )
            )
            self.assertEqual(
                tuple(item.path for item in graph.files),
                (entry.resolve(),),
            )

    def test_random_load_payload_preserves_entries_without_materializing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.perdsl").write_text("a\n", encoding="utf-8")
            (root / "b.perdsl").write_text("b\n", encoding="utf-8")
            entry = root / "root.perdsl"
            entry.write_text(
                "#load-if-defined NEVER\n"
                '(load-random 2 "a.perdsl" "b.perdsl")\n'
                "#end-if\n",
                encoding="utf-8",
            )
            graph = SourceGraphResolver().resolve(
                SourceGraphRequest(
                    entrypoint=entry,
                    load_symbols=LoadSymbolEnvironment(
                        (("NEVER", LoadSymbolState.UNDEFINED),)
                    ),
                )
            )
            random_event = next(
                event
                for event in graph.events
                if event.kind is SourceAssemblyEventKind.LOAD_RANDOM
            )
            self.assertIsInstance(random_event.payload, LoadRandomEventPayload)
            payload = random_event.payload
            self.assertEqual(
                payload.syntax,
                SourceLoadSyntax.PAREN_LOAD,
            )
            self.assertEqual(
                [(item.weight, item.target_text) for item in payload.entries],
                [(2, "a.perdsl"), (None, "b.perdsl")],
            )

    def test_validator_rejects_wrong_event_edge_back_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry = self._write_linear_conditional(Path(tmp))
            graph = SourceGraphResolver().resolve(
                SourceGraphRequest(
                    entrypoint=entry,
                    load_symbols=LoadSymbolEnvironment(
                        (("TEST", LoadSymbolState.DEFINED),)
                    ),
                )
            )
            load_event = next(
                event
                for event in graph.events
                if event.kind is SourceAssemblyEventKind.LOAD
            )
            forged_events = list(graph.events)
            event_index = forged_events.index(load_event)
            forged_events[event_index] = replace(
                load_event,
                edge=None,
            )
            forged = replace(graph, events=tuple(forged_events))
            report = validate_effective_source_graph(forged)
            self.assertFalse(report.valid)
            self.assertIn(
                SourceGraphDiagnosticCode.EVENT_EDGE_MISMATCH,
                {item.code for item in report.errors},
            )

    def test_validator_rejects_crossed_conditional_pairing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = root / "root.perdsl"
            entry.write_text(
                "#load-if-defined A\n"
                "#load-if-defined B\n"
                "#end-if\n"
                "#end-if\n",
                encoding="utf-8",
            )
            graph = SourceGraphResolver().resolve(
                SourceGraphRequest(
                    entrypoint=entry,
                    load_symbols=LoadSymbolEnvironment(
                        (
                            ("A", LoadSymbolState.DEFINED),
                            ("B", LoadSymbolState.DEFINED),
                        )
                    ),
                )
            )
            events = [
                event
                for event in graph.events
                if event.source_instance == graph.root.identity
            ]
            outer_open, inner_open, inner_end, outer_end = events
            forged_events = list(graph.events)
            forged_events[forged_events.index(inner_end)] = replace(
                inner_end,
                payload=ConditionalEndPayload(
                    open_event=outer_open.identity,
                    else_event=None,
                ),
            )
            forged = replace(graph, events=tuple(forged_events))
            report = validate_effective_source_graph(forged)
            self.assertFalse(report.valid)
            self.assertIn(
                SourceGraphDiagnosticCode.EVENT_PAIRING_INVALID,
                {item.code for item in report.errors},
            )


if __name__ == "__main__":
    unittest.main()

# Regression anchor: authoritative conditional event ordering and branch activity are tested above.
