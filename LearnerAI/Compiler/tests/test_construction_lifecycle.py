import unittest

from Compiler.compiler import compile_source
from Compiler.primitives import NativeSupportState, default_de_registry
from Compiler.ir.construction import ConstructionObservation, ConstructionPhase
from Compiler.ir.model import LifecycleState
from Compiler.semantic.construction import construction_transition_rules, transition_construction
from Compiler.semantic.native_building_catalog import resolve_building_id


class ConstructionTransitionTests(unittest.TestCase):
    def test_complete_has_precedence_over_foundation_and_placement(self):
        state = transition_construction(
            LifecycleState.PENDING,
            ConstructionObservation(
                completed=True,
                foundation_pending=True,
                placement_pending=True,
            ),
        )

        self.assertEqual(state.lifecycle, LifecycleState.COMPLETE)
        self.assertEqual(state.phase, ConstructionPhase.COMPLETE)

    def test_foundation_pending_has_precedence_over_placement_pending(self):
        state = transition_construction(
            LifecycleState.ISSUED,
            ConstructionObservation(
                completed=False,
                foundation_pending=True,
                placement_pending=True,
            ),
        )

        self.assertEqual(state.lifecycle, LifecycleState.PENDING)
        self.assertEqual(state.phase, ConstructionPhase.FOUNDATION_PENDING)

    def test_placement_pending_enters_pending_without_reissuing(self):
        state = transition_construction(
            LifecycleState.ISSUED,
            ConstructionObservation(placement_pending=True),
        )

        self.assertEqual(state.lifecycle, LifecycleState.PENDING)
        self.assertEqual(state.phase, ConstructionPhase.PLACEMENT_PENDING)

    def test_no_native_work_returns_original_demand_to_active_for_retry(self):
        state = transition_construction(
            LifecycleState.PENDING,
            ConstructionObservation(),
        )

        self.assertEqual(state.lifecycle, LifecycleState.ACTIVE)
        self.assertEqual(state.phase, ConstructionPhase.NONE)

    def test_invalidation_precedes_construction_observation(self):
        state = transition_construction(
            LifecycleState.PENDING,
            ConstructionObservation(
                completed=True,
                foundation_pending=True,
                placement_pending=True,
                invalidated=True,
            ),
        )

        self.assertEqual(state.lifecycle, LifecycleState.CANCELLED)
        self.assertEqual(state.phase, ConstructionPhase.NONE)

    def test_non_construction_lifecycle_is_not_reopened(self):
        state = transition_construction(
            LifecycleState.COMPLETE,
            ConstructionObservation(),
        )

        self.assertEqual(state.lifecycle, LifecycleState.COMPLETE)
        self.assertEqual(state.phase, ConstructionPhase.COMPLETE)


    def test_native_placement_pending_fact_is_executable_safe(self):
        registry = default_de_registry()
        self.assertIs(
            registry.support_state("up-pending-placement"),
            NativeSupportState.EXECUTABLE_SAFE,
        )

    def test_build_emission_uses_phase_observers_and_retry(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        output = compile_source(source)

        self.assertIn("(up-pending-objects c: castle >= 1)", output)
        self.assertIn("(up-pending-placement c: castle)", output)
        self.assertIn("(not (up-pending-placement c: castle))", output)
        self.assertIn("; COMPLETE | ISSUED/PENDING -> COMPLETE", output)
        self.assertIn(
            "; FOUNDATION_PENDING | ISSUED/PENDING -> PENDING",
            output,
        )
        self.assertIn(
            "; PLACEMENT_PENDING | ISSUED/PENDING -> PENDING",
            output,
        )
        self.assertIn("; RETRY | ISSUED/PENDING -> ACTIVE", output)
        self.assertNotIn(
            "; Pending admission: castle | ISSUED -> PENDING",
            output,
        )


    def test_native_building_catalog_resolves_castle_to_object_id(self):
        self.assertEqual(resolve_building_id("castle"), 82)

    def test_unknown_building_target_fails_closed(self):
        source = """
        demand unknown-building {
            require (can-build unknown-building)
            action (build unknown-building)
            witness (building-type-count unknown-building > 0)
            release (building-type-count unknown-building > 0)
        }
        """
        with self.assertRaisesRegex(
            CompileError,
            r"CONSTRUCTION-BUILD-ID: demand 'unknown-building' cannot resolve BuildingId 'unknown-building'",
        ):
            compile_source(source)

    def test_build_completion_witness_must_match_target(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count town-center > 0)
            release (building-type-count castle > 0)
        }
        """
        with self.assertRaisesRegex(
            CompileError,
            r"CONSTRUCTION-WITNESS: demand 'castle' build completion witness must target 'castle'",
        ):
            compile_source(source)

    def test_build_completion_witness_rejects_total_count(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count-total castle > 0)
            release (building-type-count castle > 0)
        }
        """
        with self.assertRaisesRegex(
            CompileError,
            r"CONSTRUCTION-WITNESS: demand 'castle' build completion witness must use building-type-count",
        ):
            compile_source(source)

    def test_build_completion_witness_rejects_nonexistence_threshold(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 1)
            release (building-type-count castle > 0)
        }
        """
        with self.assertRaisesRegex(
            CompileError,
            r"CONSTRUCTION-WITNESS: demand 'castle' build completion witness must establish at least one completed building",
        ):
            compile_source(source)

    def test_build_completion_witness_is_canonicalized_to_native_presence(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        output = compile_source(source)
        self.assertIn("(building-type-count castle >= 1)", output)

    def test_shared_construction_transition_plan_preserves_precedence(self):
        self.assertEqual(
            tuple(rule.kind for rule in construction_transition_rules()),
            ("COMPLETE", "FOUNDATION_PENDING", "PLACEMENT_PENDING", "RETRY"),
        )

    def test_retry_has_a_same_pass_barrier_and_later_pass_reset(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        output = compile_source(source)
        retry_rule = output.index("; RETRY | ISSUED/PENDING -> ACTIVE")
        issuance_rule = output.index("; Action issuance: castle | ACTIVE -> ISSUED")
        reset_rule = output.index("(set-goal construction-retry-barrier-castle 0)")
        retry_set = output.index("(set-goal construction-retry-barrier-castle 1)")
        issuance_guard = output.index("(goal construction-retry-barrier-castle 0)", issuance_rule)

        self.assertLess(reset_rule, retry_rule)
        self.assertLess(retry_rule, retry_set)
        self.assertLess(retry_set, issuance_rule)
        self.assertLess(issuance_guard, output.index("=>", issuance_rule))
        self.assertIn("(up-pending-objects c: 82 >= 1)", output)
        self.assertIn("(up-pending-placement c: 82)", output)
        self.assertIn("(not (up-pending-placement c: 82))", output)

if __name__ == "__main__":
    unittest.main()
