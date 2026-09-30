import unittest

from Compiler.ir.capability import (
    CapabilityRecoveryContract,
    CapabilityRecoveryEvent,
    CapabilityRecoveryState,
    CapabilityRecoveryStateKind,
    DemandId,
)


class CapabilityRecoveryContractTests(unittest.TestCase):
    def setUp(self):
        self.demand = DemandId("fixture", "castle")

    def test_loss_blocks_same_demand_without_invalidating_it(self):
        state = CapabilityRecoveryState(
            demand=self.demand,
            kind=CapabilityRecoveryStateKind.ACTIVE,
        )
        recovered = state.transition(
            CapabilityRecoveryEvent.LOST,
            CapabilityRecoveryContract(),
        )

        self.assertEqual(recovered.demand, self.demand)
        self.assertEqual(recovered.kind, CapabilityRecoveryStateKind.BLOCKED)

    def test_recovery_reopens_same_demand(self):
        state = CapabilityRecoveryState(
            demand=self.demand,
            kind=CapabilityRecoveryStateKind.BLOCKED,
        )
        reopened = state.transition(
            CapabilityRecoveryEvent.RECOVERED,
            CapabilityRecoveryContract(),
        )

        self.assertEqual(reopened.demand, self.demand)
        self.assertEqual(reopened.kind, CapabilityRecoveryStateKind.ACTIVE)

    def test_completed_demand_does_not_reopen_after_late_recovery(self):
        state = CapabilityRecoveryState(
            demand=self.demand,
            kind=CapabilityRecoveryStateKind.COMPLETE,
        )

        reopened = state.transition(
            CapabilityRecoveryEvent.RECOVERED,
            CapabilityRecoveryContract(),
        )

        self.assertEqual(reopened.kind, CapabilityRecoveryStateKind.COMPLETE)

    def test_contract_cannot_release_demand_on_capability_loss(self):
        with self.assertRaises(ValueError):
            CapabilityRecoveryContract(preserve_demand=False)

    def test_contract_cannot_release_opportunity_cost_on_loss(self):
        with self.assertRaises(ValueError):
            CapabilityRecoveryContract(preserve_opportunity_cost=False)

    def test_repeated_loss_keeps_same_demand_blocked(self):
        state = CapabilityRecoveryState(
            demand=self.demand,
            kind=CapabilityRecoveryStateKind.BLOCKED,
        )

        blocked = state.transition(
            CapabilityRecoveryEvent.LOST,
            CapabilityRecoveryContract(),
        )

        self.assertEqual(blocked, state)

    def test_invalidated_demand_cannot_be_reopened_by_capability_recovery(self):
        state = CapabilityRecoveryState(
            demand=self.demand,
            kind=CapabilityRecoveryStateKind.INVALIDATED,
        )

        with self.assertRaisesRegex(ValueError, "invalidated demand"):
            state.transition(
                CapabilityRecoveryEvent.RECOVERED,
                CapabilityRecoveryContract(),
            )

    def test_contract_cannot_disable_reopen(self):
        with self.assertRaises(ValueError):
            CapabilityRecoveryContract(reopen_on_recovery=False)


if __name__ == "__main__":
    unittest.main()
