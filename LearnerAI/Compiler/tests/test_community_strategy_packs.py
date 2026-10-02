import unittest

from Compiler.clients.basilisk import ByzantineProfile, resolve_effective_civ
from Compiler.ir.community_strategy_packs import build_byzantine_stock_strategy
from Compiler.ir.strategy import (
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

    def test_verified_imperial_land_escalation_is_present(self):
        profile = build_byzantine_stock_strategy(self.effective)
        demands = {demand.identity: demand for demand in profile.demands}

        for identity in (
            "imperial-cavalier-floor",
            "imperial-hussar-floor",
            "imperial-onager-floor",
            "imperial-siege-ram-floor",
            "imperial-trebuchet-floor",
        ):
            self.assertIn(identity, demands)
            self.assertIn(
                "(current-age >= imperial-age)",
                demands[identity].execution.requirements,
            )

        observations = {item.identity for item in profile.observations}
        self.assertIn("strategy-enemy-siege-cleared", observations)
        self.assertIn("strategy-enemy-castle-cleared", observations)

    def test_imperial_land_research_pack_has_verified_witnesses(self):
        profile = build_byzantine_stock_strategy(self.effective)
        observations = {item.identity for item in profile.observations}

        for identity in (
            "research-cavalier",
            "research-hussar",
            "research-onager",
            "research-siege-ram",
        ):
            self.assertIn(identity, {demand.identity for demand in profile.demands})
            self.assertIn(f"{identity}-pending", observations)
            self.assertIn(f"{identity}-complete", observations)

    def test_imperial_land_slice_emits_native_training_actions(self):
        from Compiler.clients.basilisk import compile_strategy_profile

        profile = build_byzantine_stock_strategy(self.effective)
        output = compile_strategy_profile(profile, self.effective)

        for action in (
            "(train cavalier)",
            "(train hussar)",
            "(train onager)",
            "(train battering-ram-line)",
            "(train trebuchet)",
        ):
            self.assertIn(action, output)
    def test_verified_water_escalation_is_present(self):
        profile = build_byzantine_stock_strategy(self.effective)
        demands = {demand.identity: demand for demand in profile.demands}

        for identity in (
            "water-fishing-lines",
            "water-gillnets",
            "water-warships",
            "water-heavy-warships",
            "water-greek-fire",
            "water-fire-ship-floor",
            "water-galleon-floor",
            "water-dromon-floor",
        ):
            self.assertIn(identity, demands)
            self.assertEqual(
                demands[identity].required_primary_intent.name,
                "WATER",
            )

    def test_water_escalation_emits_native_actions(self):
        from Compiler.clients.basilisk import compile_strategy_profile

        profile = build_byzantine_stock_strategy(self.effective)
        output = compile_strategy_profile(profile, self.effective)

        for action in (
            "(research 906)",
            "(research 65)",
            "(research 34)",
            "(research 35)",
            "(research 464)",
            "(train fire-ship)",
            "(train galleon)",
            "(train dromon)",
        ):
            self.assertIn(action, output)

    def test_water_and_core_land_capabilities_have_world_loss_recovery(self):
        profile = build_byzantine_stock_strategy(self.effective)
        demands = {demand.identity: demand for demand in profile.demands}

        for identity in (
            "water-fishing-continuity",
            "water-transport-capability",
            "water-naval-defense",
            "water-naval-control",
            "castle-stable-capability",
            "castle-siege-capability",
            "castle-monastery-capability",
            "imperial-university-capability",
            "castle-cataphract-floor",
            "castle-mangonel-floor",
        ):
            self.assertTrue(demands[identity].recovery_on_world_loss)

    def test_final_byzantine_strategy_breadth_is_present(self):
        profile = build_byzantine_stock_strategy(self.effective)
        demands = {demand.identity: demand for demand in profile.demands}

        for identity in (
            "research-arbalester",
            "research-halberdier",
            "research-heavy-camel",
            "research-logistica",
            "imperial-arbalester-floor",
            "imperial-petard-floor",
            "adaptive-watch-tower",
            "adaptive-stone-wall",
        ):
            self.assertIn(identity, demands)

        for identity in (
            "adaptive-watch-tower",
            "adaptive-stone-wall",
            "imperial-arbalester-floor",
            "imperial-petard-floor",
        ):
            self.assertTrue(demands[identity].recovery.preserve_strategic_demand)

    def test_final_byzantine_strategy_emits_late_land_actions(self):
        from Compiler.clients.basilisk import compile_strategy_profile

        profile = build_byzantine_stock_strategy(self.effective)
        output = compile_strategy_profile(profile, self.effective)

        for action in (
            "(research 237)",
            "(research 429)",
            "(research 236)",
            "(research 61)",
            "(train arbalester)",
            "(train petard)",
            "(build watch-tower)",
            "(build stone-wall)",
        ):
            self.assertIn(action, output)

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
