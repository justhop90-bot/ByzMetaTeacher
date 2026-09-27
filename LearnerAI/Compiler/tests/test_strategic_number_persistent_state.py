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


class PersistentStateStrategicNumberTests(unittest.TestCase):
    def _report(self, source: str):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = root / "root.per"
            entry.write_text(source, encoding="utf-8")
            graph = SourceGraphResolver().resolve(
                SourceGraphRequest(entrypoint=entry)
            )
            return analyze_persistent_state(analyze_effective_rules(graph))

    def test_up_modify_sn_is_tracked_as_persistent_sn_write(self):
        report = self._report(
            "(defrule (true) => (up-modify-sn 510 c:+ 1))
"
            "(defrule (strategic-number 510 >= 1) => (disable-self))
"
        )

        sn_writes = [
            access
            for access in report.accesses
            if access.state.kind is PersistentStateKind.STRATEGIC_NUMBER
            and access.effect is PersistentStateAccessKind.WRITE
        ]
        self.assertEqual(len(sn_writes), 1)
        self.assertEqual(sn_writes[0].state.identifier, "510")
        self.assertEqual(sn_writes[0].command, "up-modify-sn")

    def test_guard_up_modify_sn_is_visible_as_a_write_access(self):
        report = self._report(
            "(defrule (up-modify-sn 510 c:+ 1) => (disable-self))
"
        )

        writes = [
            access
            for access in report.accesses
            if access.command == "up-modify-sn"
        ]
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0].section, "GUARD")


if __name__ == "__main__":
    unittest.main()
