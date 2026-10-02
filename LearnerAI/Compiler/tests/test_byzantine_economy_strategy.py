import unittest

from Compiler.clients.basilisk import (
    ByzantineProfile,
    EconomyMode,
    build_byzantine_strategy,
    compile_strategy_profile,
    lower_strategy_profile,
)
from Compiler.ir.civ_profile import resolve_effective_civ


class ByzantineEconomyStrategyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())

    def test_economic_continuity_demands_are_bounded_and_recoverable(self):
        profile = build_byzantine_strategy(self.effective)
        demands = {item.identity: item for item in profile.demands}

        expected = {
            "economy-house-floor-1",
            "economy-house-floor-4",
            "economy-house-floor-8",
            "economy-house-floor-12",
            "economy-house-floor-16",
            "economy-farm-floor-feudal-4",
            "economy-farm-floor-feudal-8",
            "economy-farm-floor-castle-12",
            "economy-farm-floor-imperial-16",
            "economy-lumber-camp-floor-1",
            "economy-lumber-camp-floor-2",
            "economy-mining-camp-floor-1",
            "economy-mining-camp-floor-2",
            "economy-food-mill-floor-1",
            "economy-market-floor-1",
        }
        self.assertTrue(expected.issubset(demands))
        for identity in expected:
            demand = demands[identity]
            self.assertTrue(demand.recovery_on_world_loss)
            self.assertTrue(demand.recovery.preserve_strategic_demand)
            self.assertTrue(demand.recovery.reopen_on_recovery)

    def test_economy_observations_use_native_resource_and_headroom_facts(self):
        profile = build_byzantine_strategy(self.effective)
        observations = {item.identity: item.expression for item in profile.observations}

        self.assertEqual(observations["strategy-housing-pressure"], "(housing-headroom < 4)")
        self.assertEqual(observations["strategy-food-shortage"], "(food-amount < 350)")
        self.assertIn("resource-found wood", observations["strategy-wood-resource-opportunity"])
        self.assertIn("dropsite-min-distance wood", observations["strategy-wood-dropsite-distant"])

    def test_economy_emits_houses_farms_dropsites_and_market(self):
        profile = build_byzantine_strategy(self.effective)
        output = compile_strategy_profile(profile, self.effective)
        for action in (
            "(build house)",
            "(build farm)",
            "(build lumber-camp)",
            "(build mining-camp)",
            "(build mill)",
            "(build market)",
        ):
            self.assertIn(action, output)
        self.assertIn("(housing-headroom < 4)", output)
        self.assertIn("(food-amount < 350)", output)
        self.assertIn("(dropsite-min-distance wood > 12)", output)

    def test_food_recovery_overrides_normal_economy_posture(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        self.assertIn(EconomyMode.FOOD_RECOVERY, {item.mode for item in profile.economy_controller.policies})
        recovery = next(
            rule for rule in control.rules
            if rule.identity == "economy-controller-select-food-recovery"
        )
        self.assertIn("(food-amount < 350)", recovery.facts[0].source)
        self.assertIn("(set-goal economy-posture 8)", recovery.actions[0].source)

        output = compile_strategy_profile(profile, self.effective)
        self.assertIn("(defconst sn-food-gatherer-percentage 117)", output)
        self.assertIn("(set-goal economy-posture 8)", output)
        self.assertIn("(set-strategic-number sn-food-gatherer-percentage 70)", output)
        self.assertIn("(set-strategic-number sn-wood-gatherer-percentage 20)", output)
        self.assertIn("(set-strategic-number sn-gold-gatherer-percentage 10)", output)


if __name__ == "__main__":
    unittest.main()
