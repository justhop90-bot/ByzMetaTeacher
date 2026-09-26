import unittest
from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.compiler import compile_source
from Compiler.errors import CompileError
from Compiler.ir import (
    CancellationStateContract,
    InvalidationEvidenceKind,
    InvalidationContract,
    LifecycleState,
)
from Compiler.parser import parse
from Compiler.primitives import default_de_registry
from Compiler.semantic import analyze
from Compiler.semantic.invalidation import (
    InvalidationDiagnosticCode,
    validate_invalidation_contracts,
)


class InvalidationTests(unittest.TestCase):
    def test_semantic_demand_has_typed_invalidation_and_cancellation_contracts(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
            invalidate (not (building-available castle))
        }
        """
        ir = analyze(parse(source), default_de_registry(), source_unit="test")
        demand = ir[0]

        self.assertIsNotNone(demand.invalidation)
        self.assertEqual(
            demand.invalidation.evidence_kind,
            InvalidationEvidenceKind.WORLD_STATE,
        )
        self.assertEqual(demand.invalidation.invalidates, demand.identity)
        self.assertEqual(demand.invalidation.primitive, "not")

        self.assertIsNotNone(demand.cancellation)
        self.assertEqual(
            demand.cancellation.from_states,
            (
                LifecycleState.ACTIVE,
                LifecycleState.ISSUED,
                LifecycleState.PENDING,
            ),
        )
        self.assertEqual(
            demand.cancellation.to_state,
            LifecycleState.CANCELLED,
        )

    def test_invalidation_cancels_before_release(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
            invalidate (not (building-available castle))
        }
        """
        output = compile_source(source)
        invalidation = output.index("; Invalidation: castle")
        release = output.index("; Release: castle")
        action = output.index("; Action issuance: castle")

        self.assertLess(invalidation, release)
        self.assertLess(invalidation, action)
        block = output[invalidation:release]
        self.assertIn("CANCELLED", block)
        self.assertIn("(set-goal demand-castle 1004)", block)

    def test_timing_invalidation_is_rejected_deterministically(self):
        with self.assertRaisesRegex(
            CompileError,
            r"INV-002: invalidation for demand 'castle' contains timing evidence",
        ):
            compile_source(
                """
                demand castle {
                    require (can-build castle)
                    action (build castle)
                    witness (building-type-count castle > 0)
                    release (building-type-count castle > 0)
                    invalidate (game-time >= 900)
                }
                """
            )

    def test_action_coupled_invalidation_is_rejected_deterministically(self):
        with self.assertRaisesRegex(
            CompileError,
            r"INV-003: invalidation for demand 'castle' reuses action primitive 'build'",
        ):
            compile_source(
                """
                demand castle {
                    require (can-build castle)
                    action (build castle)
                    witness (building-type-count castle > 0)
                    release (building-type-count castle > 0)
                    invalidate (build castle)
                }
                """
            )

    def test_cancellation_contract_cannot_cancel_complete_state(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
            invalidate (not (building-available castle))
        }
        """
        registry = default_de_registry()
        ir = analyze(parse(source), registry, source_unit="test")
        broken = replace(
            ir[0],
            cancellation=replace(
                ir[0].cancellation,
                from_states=(LifecycleState.COMPLETE,),
            ),
        )

        report = validate_invalidation_contracts((broken,), registry)
        self.assertEqual(
            tuple(item.code.value for item in report.diagnostics),
            ("CXL-002",),
        )

    def test_invalidation_identity_mismatch_is_exact(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
            invalidate (not (building-available castle))
        }
        """
        registry = default_de_registry()
        ir = analyze(parse(source), registry, source_unit="test")
        broken = replace(
            ir[0],
            invalidation=replace(
                ir[0].invalidation,
                invalidates=replace(
                    ir[0].identity,
                    local_name="other",
                ),
            ),
        )

        report = validate_invalidation_contracts((broken,), registry)
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
                    "INV-005",
                    "error",
                    "CONFLICTING",
                    "invalidation for demand 'castle' invalidates 'other', not 'castle'",
                ),
            ),
        )


if __name__ == "__main__":
    unittest.main()

# final invalidation verification marker
