import unittest
from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.compiler import compile_source
from Compiler.errors import CompileError
from Compiler.ir.model import (
    ActionIssuanceFailure,
    ActionIssuancePhase,
    LifecycleState,
)
from Compiler.parser import parse
from Compiler.primitives import default_de_registry
from Compiler.semantic.action_issuance import validate_action_issuance
from Compiler.semantic import analyze


class ActionIssuanceTests(unittest.TestCase):
    def test_semantic_demand_has_explicit_issuance_contract(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        ir = analyze(parse(source), default_de_registry(), source_unit="test")
        issuance = ir[0].action_issuance

        self.assertIsNotNone(issuance)
        self.assertEqual(issuance.phase, ActionIssuancePhase.ATTEMPT)
        self.assertEqual(issuance.issued_state, LifecycleState.ISSUED)
        self.assertEqual(issuance.pending_state, LifecycleState.PENDING)
        self.assertEqual(
            issuance.failure,
            ActionIssuanceFailure.RETAIN_ACTIVE,
        )

    def test_emitter_separates_issuance_from_pending_transition(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        output = compile_source(source)
        action = output.index("; Action issuance: castle")
        pending = output.index("; Pending admission: castle")
        witness = output.index("; Completion witness: castle")
        release = output.index("; Release: castle")

        self.assertLess(release, witness)
        self.assertLess(witness, pending)
        self.assertLess(pending, action)
        action_block = output[action:]
        self.assertIn("(set-goal demand-castle 44)", action_block)
        self.assertIn("(set-goal demand-castle 42)", output[pending:action])

    def test_emitter_records_native_pass_constraint_for_build_action(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        output = compile_source(source)
        self.assertIn(
            "; NATIVE-PASS-CONSTRAINT build maximum-successes=1",
            output,
        )

    def test_issuance_failure_does_not_enter_pending(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        output = compile_source(source)
        failure_marker = output.index("; Issuance failure: castle")
        release_marker = output.index("; Release: castle", failure_marker)
        failure_block = output[failure_marker:release_marker]

        self.assertIn("RETAIN-ACTIVE", failure_block)
        self.assertNotIn("(set-goal demand-castle", failure_block)

    def test_issuance_collapse_diagnostic_is_exact_and_deterministic(self):
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
        issuance = ir[0].action_issuance
        broken = replace(
            ir[0],
            action_issuance=replace(
                issuance,
                issued_state=LifecycleState.ISSUED,
                pending_state=LifecycleState.ISSUED,
            ),
        )

        first = validate_action_issuance((broken,), registry)
        second = validate_action_issuance((broken,), registry)

        expected = (
            (
                "ISS-003",
                "error",
                "CONFLICTING",
                "action issuance for demand 'castle' collapses ISSUED and PENDING",
            ),
        )
        actual = tuple(
            (
                item.code.value,
                item.severity.value,
                item.status.value,
                item.message,
            )
            for item in first.diagnostics
        )
        self.assertEqual(actual, expected)
        self.assertEqual(first.diagnostics, second.diagnostics)

    def test_invalid_issuance_contract_is_rejected_deterministically(self):
        with self.assertRaisesRegex(
            CompileError,
            r"ISS-002: action issuance for demand 'castle' has no native feasibility guard",
        ):
            compile_source(
                """
                demand castle {
                    require (building-available castle)
                    action (build castle)
                    witness (building-type-count castle > 0)
                    release (building-type-count castle > 0)
                }
                """
            )


if __name__ == "__main__":
    unittest.main()
