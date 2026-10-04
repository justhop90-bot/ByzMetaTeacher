import unittest

from Compiler.clients.basilisk import ByzantineProfile, resolve_effective_civ
from Compiler.ir.community_strategy_packs import build_byzantine_stock_strategy
from Compiler.ir.strategy import (
    StrategicPriority,
    resolve_strategy_profile,
    lower_strategy_profile,
)


class ByzantineCommunityStrategyPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())

    def test_stock_profile_resolves_against_current_effective_data(self):
        profile = build_byzantine_stock_strategy(self.effective)
        resolved = resolve_strategy_profile(profile, self.effective)
        self.assertEqual(profile.profile_id, "byzantine-stock-v1")
        self.assertIn("imperial-conversion", resolved.demand_ids)
        self.assertIn("castle-second-town-center", resolved.demand_ids)
        self.assertIn("castle-cataphract-floor", resolved.demand_ids)
        self.assertIn("castle-mangonel-floor", resolved.demand_ids)
        self.assertIn("imperial-bombard-floor", resolved.demand_ids)
        self.assertIn("water-fishing-continuity", resolved.demand_ids)

    def test_stock_profile_contains_complete_research_witnesses(self):
        profile = build_byzantine_stock_strategy(self.effective)
        observations = {item.identity for item in profile.observations}
        for identity in (
            "research-wheelbarrow",
            "research-double-bit-axe",
            "research-horse-collar",
            "research-hand-cart",
            "research-bow-saw",
            "research-two-man-saw",
            "research-bodkin-arrow",
            "research-conscription",
            "research-chemistry",
            "research-gold-mining",
            "research-gold-shaft-mining",
            "research-heavy-plow",
            "research-fletching",
        ):
            self.assertIn(f"{identity}-pending", observations)
            self.assertIn(f"{identity}-complete", observations)

    def test_feudal_economic_multipliers_precede_generic_support_research(self):
        profile = build_byzantine_stock_strategy(self.effective)
        by_id = {item.identity: item for item in profile.demands}
        dba = by_id["research-double-bit-axe"]
        horse_collar = by_id["research-horse-collar"]
        wheelbarrow = by_id["research-wheelbarrow"]

        self.assertEqual(dba.priority, StrategicPriority.ECONOMIC_MULTIPLIER)
        self.assertEqual(horse_collar.priority, StrategicPriority.ECONOMIC_MULTIPLIER)
        self.assertEqual(wheelbarrow.priority, StrategicPriority.ECONOMIC_MULTIPLIER)
        self.assertGreater(dba.priority, StrategicPriority.DEFENSE)
        self.assertIn(
            "(not (can-research-with-escrow castle-age))",
            dba.execution.requirements,
        )
        self.assertIn(
            "(not (can-research-with-escrow castle-age))",
            horse_collar.execution.requirements,
        )
        self.assertIn(
            "(not (can-research-with-escrow castle-age))",
            wheelbarrow.execution.requirements,
        )

        feudal_research_order = [
            demand.identity
            for demand in profile.demands
            if demand.identity in {
                "research-double-bit-axe",
                "research-horse-collar",
                "research-wheelbarrow",
            }
        ]
        self.assertEqual(
            feudal_research_order,
            [
                "research-double-bit-axe",
                "research-horse-collar",
                "research-wheelbarrow",
            ],
        )

    def test_stock_profile_has_explicit_control_and_water_modes(self):
        profile = build_byzantine_stock_strategy(self.effective)
        sn_ids = {mode.native_strategic_number_id for mode in profile.strategic_number_modes}
        self.assertTrue({18, 36, 42, 227}.issubset(sn_ids))
        self.assertIsNotNone(profile.attack_plan)
        self.assertIsNotNone(profile.duc_plan)

    def test_stock_profile_lowers_without_creating_a_second_lifecycle_model(self):
        profile = build_byzantine_stock_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        self.assertGreater(len(compilation.demands), 10)
        self.assertIsNotNone(compilation.control_plan)
        self.assertIsNotNone(compilation.attack_plan)
        self.assertIsNotNone(compilation.duc_plan)

    def test_water_continuity_can_be_disabled_without_removing_land_strategy(self):
        profile = build_byzantine_stock_strategy(
            self.effective,
            include_water_continuity=False,
        )
        self.assertNotIn(
            "water-fishing-continuity",
            {demand.identity for demand in profile.demands},
        )
        self.assertIn(
            "castle-cataphract-floor",
            {demand.identity for demand in profile.demands},
        )


if __name__ == "__main__":
    unittest.main()
