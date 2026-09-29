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


    def test_train_pending_admission_is_queue_guarded(self):
        source = """
        demand spears {
            require (can-train spearman)
            action (train spearman)
            witness (unit-type-count spearman >= 1)
            release (unit-type-count spearman >= 1)
        }
        """
        output = compile_source(source)
        pending_start = output.index("; Pending admission: spears")
        pending_end = output.index("; Action issuance: spears", pending_start)
        pending_block = output[pending_start:pending_end]

        self.assertIn("(up-pending-objects c: 93 >= 1)", pending_block)
        self.assertIn("(goal demand-spears 42)", pending_block)
        self.assertIn("(set-goal demand-spears 42)", pending_block)

    def test_train_retry_is_barriered_to_a_later_pass(self):
        source = """
        demand spears {
            require (can-train spearman)
            action (train spearman)
            witness (unit-type-count spearman >= 1)
            release (unit-type-count spearman >= 1)
        }
        """
        output = compile_source(source)
        retry = output.index("; RETRY | ISSUED/PENDING -> ACTIVE")
        issuance = output.index("; Action issuance: spears | ACTIVE -> ISSUED")
        reset = output.index("(set-goal production-retry-barrier-spears 0)")
        set_barrier = output.index("(set-goal production-retry-barrier-spears 1)")
        guard = output.index("(goal production-retry-barrier-spears 0)", issuance)

        self.assertLess(reset, retry)
        self.assertLess(retry, set_barrier)
        self.assertLess(set_barrier, issuance)
        self.assertIn("(not (up-pending-objects c: 93 >= 1))", output[retry:issuance])
        self.assertIn("(goal production-retry-barrier-spears 0)", output[issuance:])

    def test_train_uses_production_retry_storage_but_build_does_not(self):
        train = compile_source(
            """
            demand spears {
                require (can-train spearman)
                action (train spearman)
                witness (unit-type-count spearman >= 1)
                release (unit-type-count spearman >= 1)
            }
            """
        )
        build = compile_source(
            """
            demand castle {
                require (can-build castle)
                action (build castle)
                witness (building-type-count castle > 0)
                release (building-type-count castle > 0)
            }
            """
        )

        self.assertIn("production-retry-barrier-spears", train)
        self.assertNotIn("production-retry-barrier-castle", build)


    def test_research_lifecycle_uses_native_in_progress_status(self):
        from Compiler.semantic.native_tech_catalog import resolve_tech_id

        output = compile_source(
            """
            demand wheelbarrow {
                require (can-research ri-wheelbarrow)
                action (research ri-wheelbarrow)
                witness (research-completed ri-wheelbarrow)
                release (research-completed ri-wheelbarrow)
            }
            """
        )
        native_tech_id = resolve_tech_id("ri-wheelbarrow")
        self.assertIn("research-retry-barrier-wheelbarrow", output)
        pending_start = output.index("; Completion witness: wheelbarrow")
        action_start = output.index("; Action issuance: wheelbarrow")
        lifecycle = output[pending_start:action_start]
        self.assertIn(
            f"(up-research-status c: {native_tech_id} >= 2)",
            lifecycle,
        )
        self.assertIn(
            f"(not (up-research-status c: {native_tech_id} >= 2))",
            lifecycle,
        )


    def test_research_lifecycle_has_typed_native_status_contract(self):
        from Compiler.ir.research import ResearchState
        from Compiler.semantic.analyzer import analyze
        from Compiler.parser import parse
        from Compiler.primitives import default_de_registry

        semantic = analyze(
            parse(
                """
                demand wheelbarrow {
                    require (can-research ri-wheelbarrow)
                    action (research ri-wheelbarrow)
                    witness (research-completed ri-wheelbarrow)
                    release (research-completed ri-wheelbarrow)
                }
                """
            ),
            default_de_registry(),
            source_unit="test",
        )
        lifecycle = semantic[0].research_lifecycle
        self.assertIsNotNone(lifecycle)
        self.assertEqual(lifecycle.pending_state, ResearchState.PENDING)
        self.assertEqual(int(ResearchState.UNAVAILABLE), 0)
        self.assertEqual(int(ResearchState.AVAILABLE), 1)
        self.assertEqual(int(ResearchState.PENDING), 2)
        self.assertEqual(int(ResearchState.COMPLETE), 3)
        self.assertEqual(lifecycle.pending_fact.args[0], "c:")
        self.assertEqual(int(lifecycle.pending_fact.args[1]), lifecycle.native_tech_id)
        self.assertEqual(lifecycle.pending_fact.args[2], ">=")
        self.assertEqual(lifecycle.pending_fact.args[3], str(int(ResearchState.PENDING)))

    def test_research_retry_is_barriered_to_a_later_pass(self):
        output = compile_source(
            """
            demand wheelbarrow {
                require (can-research ri-wheelbarrow)
                action (research ri-wheelbarrow)
                witness (research-completed ri-wheelbarrow)
                release (research-completed ri-wheelbarrow)
            }
            """
        )
        issuance = output.index("; Action issuance: wheelbarrow")
        action_block = output[issuance:]
        self.assertIn("(goal research-retry-barrier-wheelbarrow 0)", action_block)
        retry_start = output.index("; RETRY | ISSUED/PENDING -> ACTIVE")
        retry_block = output[retry_start:issuance]
        self.assertIn(
            "(set-goal research-retry-barrier-wheelbarrow 1)",
            retry_block,
        )


if __name__ == "__main__":
    unittest.main()
