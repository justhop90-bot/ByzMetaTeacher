import unittest

from Compiler.compiler import compile_source
from Compiler.primitives import NativeSupportState, default_de_registry
from Compiler.ir.construction import ConstructionObservation, ConstructionPhase
from Compiler.ir.model import LifecycleState
from Compiler.semantic.construction import transition_construction


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


if __name__ == "__main__":
    unittest.main()
