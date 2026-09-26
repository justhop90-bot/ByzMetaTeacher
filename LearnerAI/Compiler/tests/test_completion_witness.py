import unittest
from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.compiler import compile_source
from Compiler.errors import CompileError
from Compiler.ir import CompletionWitnessContract, WitnessEvidenceKind
from Compiler.parser import parse
from Compiler.primitives import default_de_registry
from Compiler.semantic import analyze
from Compiler.semantic.completion_witness import (
    WitnessDiagnosticCode,
    validate_completion_witnesses,
)


class CompletionWitnessTests(unittest.TestCase):
    def test_semantic_demand_has_typed_completion_witness_contract(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        ir = analyze(parse(source), default_de_registry(), source_unit="test")
        witness = ir[0].completion_witness

        self.assertIsNotNone(witness)
        self.assertEqual(witness.identity.local_name, "castle-witness")
        self.assertEqual(witness.evidence_kind, WitnessEvidenceKind.WORLD_STATE)
        self.assertEqual(witness.establishes.local_name, "castle")
        self.assertEqual(witness.primitive, "building-type-count")
        self.assertEqual(witness.source_order, 2)

    def test_witness_validation_rejects_timing_deterministically(self):
        with self.assertRaisesRegex(
            CompileError,
            r"TIMING-CANNOT-WITNESS: demand castle cannot use timing as completion witness",
        ):
            compile_source(
                """
                demand castle {
                    require (can-build castle)
                    action (build castle)
                    witness (game-time >= 600)
                    release (building-type-count castle > 0)
                }
                """
            )

    def test_witness_validation_rejects_action_coupling(self):
        with self.assertRaisesRegex(
            CompileError,
            r"WIT-004: completion witness for demand 'castle' reuses action primitive 'build'",
        ):
            compile_source(
                """
                demand castle {
                    require (can-build castle)
                    action (build castle)
                    witness (build castle)
                    release (building-type-count castle > 0)
                }
                """
            )

    def test_witness_validation_rejects_non_completion_native_observation(self):
        with self.assertRaisesRegex(
            CompileError,
            r"WIT-003: completion witness for demand 'castle' contains no completion-capable native observation",
        ):
            compile_source(
                """
                demand castle {
                    require (can-build castle)
                    action (build castle)
                    witness (building-type-count-total castle > 0)
                    release (building-type-count castle > 0)
                }
                """
            )

    def test_witness_validator_rejects_identity_mismatch_exactly(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        registry = default_de_registry()
        ir = analyze(parse(source), registry, source_unit="test")
        broken = replace(
            ir[0],
            completion_witness=replace(
                ir[0].completion_witness,
                establishes=replace(
                    ir[0].completion_witness.establishes,
                    local_name="other",
                ),
            ),
        )

        report = validate_completion_witnesses((broken,), registry)
        self.assertEqual(
            tuple(
                (
                    item.code.value,
                    item.severity.value,
                    item.status.value,
                    item.message,
                )
                for item in report.diagnostics
            ),
            (
                (
                    "WIT-005",
                    "error",
                    "CONFLICTING",
                    "completion witness for demand 'castle' establishes 'other', not 'castle'",
                ),
            ),
        )

    def test_witness_validator_accepts_real_world_state(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        registry = default_de_registry()
        ir = analyze(parse(source), registry, source_unit="test")

        report = validate_completion_witnesses(ir, registry)

        self.assertTrue(report.valid)
        self.assertEqual(report.diagnostics, ())


if __name__ == "__main__":
    unittest.main()

# TDD RED verification marker
