import tempfile
import unittest
from pathlib import Path

from Compiler.semantic.persistent_state import (
    PersistentStateAccessKind,
    PersistentStateKind,
    analyze_persistent_state,
)
from Compiler.semantic.rule_execution import analyze_effective_rules
from Compiler.source_graph import SourceGraphRequest, SourceGraphResolver


class PersistentStateTimerExtractionTests(unittest.TestCase):
    def _report(self, source: str):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = root / "root.per"
            entry.write_text(source, encoding="utf-8")
            graph = SourceGraphResolver().resolve(
                SourceGraphRequest(entrypoint=entry)
            )
            return analyze_persistent_state(
                analyze_effective_rules(graph)
            )

    def test_standard_timer_commands_are_typed_as_timer_reads_and_writes(self):
        report = self._report(
            "(defrule (true) => (enable-timer 1 30) (disable-timer 1))\n"
            "(defrule (timer-triggered 1) => (up-set-timer c: 1 c: 60))\n"
            "(defrule (up-timer-status 1 = timer-running) => (disable-self))\n"
        )

        self.assertEqual(
            [
                (item.state.kind, item.effect, item.state.identifier, item.command)
                for item in report.accesses
            ],
            [
                (PersistentStateKind.TIMER, PersistentStateAccessKind.WRITE, "1", "enable-timer"),
                (PersistentStateKind.TIMER, PersistentStateAccessKind.WRITE, "1", "disable-timer"),
                (PersistentStateKind.TIMER, PersistentStateAccessKind.READ, "1", "timer-triggered"),
                (PersistentStateKind.TIMER, PersistentStateAccessKind.WRITE, "1", "up-set-timer"),
                (PersistentStateKind.TIMER, PersistentStateAccessKind.READ, "1", "up-timer-status"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
