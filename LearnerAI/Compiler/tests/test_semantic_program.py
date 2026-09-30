import unittest

from Compiler.compiler import compile_source
from Compiler.ir import CompilerSemanticProgram, SemanticId
from Compiler.parser import parse
from Compiler.primitives import default_de_registry
from Compiler.semantic import analyze

from test_military_composition_proof import _proof


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

    def test_program_with_military_proof_is_not_empty(self):
        program, _ = _proof()
        self.assertFalse(program.empty)

    def test_program_rejects_duplicate_demand_identity(self):
        demands = self._demands()
        with self.assertRaises(ValueError):
            CompilerSemanticProgram(demands=(demands[0], demands[0]))

    def test_program_preserves_existing_compiler_output(self):
        self.assertIn("(build house)", compile_source(_SOURCE))


if __name__ == "__main__":
    unittest.main()
