import unittest

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


if __name__ == "__main__":
    unittest.main()
