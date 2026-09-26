import unittest
from dataclasses import replace
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.compiler import compile_source
from Compiler.errors import CompileError
from Compiler.ir import (
    LifecycleState,
    ReleaseEvidenceKind,
    ReleaseStateContract,
)
from Compiler.parser import parse
from Compiler.primitives import default_de_registry
from Compiler.semantic import analyze
from Compiler.semantic.release_state import (
    ReleaseDiagnosticCode,
    validate_release_states,
)


class ReleaseStateTests(unittest.TestCase):
    def test_semantic_demand_has_typed_release_state_contract(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        ir = analyze(parse(source), default_de_registry(), source_unit="test")
        release = ir[0].release_state

        self.assertIsNotNone(release)
        self.assertEqual(release.identity.local_name, "castle-release")
        self.assertEqual(release.evidence_kind, ReleaseEvidenceKind.WORLD_STATE)
        self.assertEqual(release.from_state, LifecycleState.COMPLETE)
        self.assertEqual(release.to_state, LifecycleState.RELEASED)
        self.assertEqual(release.source_order, 0)
        self.assertEqual(release.witness_source_order, 2)

    def test_release_must_be_guarded_by_complete_state(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        output = compile_source(source)
        release = output.index("; Release: castle | COMPLETE -> RELEASED")
        witness = output.index("; Completion witness: castle | PENDING -> COMPLETE")
        block = output[release:witness]

        self.assertIn("(goal demand-castle 1002)", block)
        self.assertIn("(set-goal demand-castle 0)", block)
        self.assertNotIn("(goal demand-castle 1001)", block)
        self.assertNotIn("(goal demand-castle 1003)", block)

    def test_timing_release_is_rejected_deterministically(self):
        with self.assertRaisesRegex(
            CompileError,
            r"REL-002: release for demand 'castle' contains timing evidence",
        ):
            compile_source(
                """
                demand castle {
                    require (can-build castle)
                    action (build castle)
                    witness (building-type-count castle > 0)
                    release (game-time >= 600)
                }
                """
            )

    def test_action_coupled_release_is_rejected_deterministically(self):
        with self.assertRaisesRegex(
            CompileError,
            r"REL-004: release for demand 'castle' reuses action primitive 'build'",
        ):
            compile_source(
                """
                demand castle {
                    require (can-build castle)
                    action (build castle)
                    witness (building-type-count castle > 0)
                    release (build castle)
                }
                """
            )

    def test_release_identity_mismatch_is_exact(self):
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
            release_state=replace(
                ir[0].release_state,
                establishes=replace(
                    ir[0].release_state.establishes,
                    local_name="other",
                ),
            ),
        )

        report = validate_release_states((broken,), registry)
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
                    "REL-005",
                    "error",
                    "CONFLICTING",
                    "release for demand 'castle' establishes 'other', not 'castle'",
                ),
            ),
        )

    def test_release_transition_must_be_complete_to_released(self):
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
            release_state=replace(
                ir[0].release_state,
                from_state=LifecycleState.PENDING,
                to_state=LifecycleState.RELEASED,
            ),
        )

        report = validate_release_states((broken,), registry)
        self.assertEqual(
            tuple(item.code.value for item in report.diagnostics),
            ("REL-006",),
        )

    def test_real_world_state_release_is_valid(self):
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

        report = validate_release_states(ir, registry)

        self.assertTrue(report.valid)
        self.assertEqual(report.diagnostics, ())


if __name__ == "__main__":
    unittest.main()

# final release-state verification marker
