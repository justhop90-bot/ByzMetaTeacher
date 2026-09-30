import unittest

from Compiler.compiler import compile_source
from Compiler.ir import CompilerSemanticProgram, PersistentControlKind, SemanticId
from Compiler.parser import parse
from Compiler.primitives import default_de_registry
from Compiler.semantic import analyze


_SOURCE = """
demand bootstrap {
    require (can-build house)
    action (build house)
    witness (building-type-count house >= 1)
    release (building-type-count house >= 1)
}
"""


class CompilerSemanticProgramTests(unittest.TestCase):
    def _demands(self):
        return tuple(
            analyze(
                parse(
                    _SOURCE,
                    source_unit="<semantic-program-test>",
                ),
                default_de_registry(),
                source_unit="<semantic-program-test>",
            )
        )

    def test_program_envelopes_existing_compiler_semantics(self):
        demands = self._demands()
        program = CompilerSemanticProgram(demands=demands)

        self.assertEqual(program.demands, demands)
        self.assertFalse(program.operational_plan.contracts)
        self.assertIsNone(program.control_plan)
        self.assertEqual(
            program.demands[0].identity,
            SemanticId("<semantic-program-test>", "bootstrap"),
        )

    def test_program_contains_projected_timer_controls(self):
        source = """
        demand timer_gate {
            timer cooldown
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        demands = tuple(
            analyze(
                parse(source, source_unit="timer-program-test"),
                default_de_registry(),
                source_unit="timer-program-test",
            )
        )
        program = CompilerSemanticProgram(
            demands=demands,
            persistent_controls=demands[0].persistent_controls,
        )

        self.assertEqual(len(program.persistent_controls), 1)
        self.assertEqual(program.persistent_controls[0].kind, PersistentControlKind.TIMER)
        self.assertEqual(program.persistent_controls[0].owner, demands[0].identity)
        self.assertFalse(program.empty)

    def test_program_rejects_persistent_control_with_unknown_owner(self):
        demands = self._demands()
        control = demands[0].persistent_controls[0] if demands[0].persistent_controls else None
        if control is None:
            from Compiler.ir import PersistentControlId, PersistentControlRef
            control = PersistentControlRef(
                id=PersistentControlId("<semantic-program-test>", "timer:orphan"),
                kind=PersistentControlKind.TIMER,
                owner=SemanticId("<semantic-program-test>", "orphan"),
            )

        with self.assertRaises(ValueError):
            CompilerSemanticProgram(
                demands=demands,
                persistent_controls=(control,),
            )

    def test_program_rejects_duplicate_demand_identity(self):
        demands = self._demands()
        with self.assertRaises(ValueError):
            CompilerSemanticProgram(demands=(demands[0], demands[0]))

    def test_program_preserves_existing_compiler_output(self):
        self.assertIn("(build house)", compile_source(_SOURCE))


if __name__ == "__main__":
    unittest.main()
