import unittest

from community_engine import (
    CapabilityTransition,
    PracticeStatus,
    classify_capability_transition,
    default_community_engine_registry,
)


class EngineSemanticsTests(unittest.TestCase):
    def test_loss_requires_true_to_false(self):
        self.assertIs(
            classify_capability_transition(True, False),
            CapabilityTransition.LOST,
        )

    def test_recovery_requires_false_to_true(self):
        self.assertIs(
            classify_capability_transition(False, True),
            CapabilityTransition.RECOVERED,
        )

    def test_unknown_history_is_not_loss(self):
        self.assertIs(
            classify_capability_transition(None, False),
            CapabilityTransition.UNKNOWN,
        )

    def test_same_truth_is_not_a_transition(self):
        self.assertIs(
            classify_capability_transition(True, True),
            CapabilityTransition.NO_CHANGE,
        )

    def test_registry_contains_the_engine_practices_that_matter(self):
        registry = default_community_engine_registry()
        self.assertIn("state.goal.persistent", {p.identity for p in registry.practices})
        self.assertIn("duc.search-state-retained", {p.identity for p in registry.practices})
        self.assertIn("attack.group-state-control", {p.identity for p in registry.practices})
        self.assertEqual(registry.practice("state.sn.engine-control").status, PracticeStatus.PARTIAL)
        self.assertEqual(registry.lifecycle("build").feasibility_fact, "can-build")
        self.assertFalse(registry.lifecycle("build").pending_is_completion)

    def test_registry_rejects_duplicate_or_uncontradicted_contracts(self):
        registry = default_community_engine_registry()
        registry.validate()


if __name__ == "__main__":
    unittest.main()
