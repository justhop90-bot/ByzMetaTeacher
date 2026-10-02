import unittest

from Compiler.clients.basilisk import ByzantineProfile, resolve_effective_civ
from Compiler.ir.strategy import build_byzantine_strategy, lower_strategy_profile
from Compiler.ir.water import (
    TransportExecutionPhase,
    WaterExecutionState,
    transition_transport_execution,
)


class WaterTransportExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())

    def test_transport_state_preserves_intent_and_enters_recovery_when_capability_is_lost(self):
        ready = WaterExecutionState(
            transport_required=True,
            transport_capable=True,
            phase=TransportExecutionPhase.READY,
        )
        recovered = transition_transport_execution(ready, transport_required=True, transport_capable=False)

        self.assertEqual(recovered.phase, TransportExecutionPhase.RECOVER)
        self.assertTrue(recovered.transport_required)
        self.assertFalse(recovered.transport_capable)

    def test_stock_strategy_exposes_typed_water_execution_plan(self):
        profile = build_byzantine_strategy(self.effective)

        self.assertIsNotNone(profile.water_execution_plan)
        self.assertIn("strategy-water-islands", {
            item.identity for item in profile.observations
        })

    def test_water_plan_lowers_into_persistent_posture_and_transport_state(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)

        self.assertIsNotNone(compilation.control_plan)
        state_ids = {state.identifier for state in compilation.control_plan.states}
        self.assertIn("water-posture", state_ids)
        self.assertIn("transport-phase", state_ids)

        rule_ids = {rule.identity for rule in compilation.control_plan.rules}
        self.assertIn("transport-phase-recover-on-capability-loss", rule_ids)
        self.assertIn("transport-phase-ready", rule_ids)
        self.assertIn("water-posture-naval-defense", rule_ids)
        self.assertIn("water-posture-naval-control", rule_ids)

    def test_stock_strategy_has_transport_and_naval_execution_demands(self):
        profile = build_byzantine_strategy(self.effective)
        demand_ids = {item.identity for item in profile.demands}

        self.assertIn("water-transport-capability", demand_ids)
        self.assertIn("water-naval-defense", demand_ids)
        self.assertIn("water-naval-control", demand_ids)


if __name__ == "__main__":
    unittest.main()
