import unittest

from Compiler.ir.game_data import Age

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

    def test_stock_profile_scales_military_provider_depth_from_standing_demand(self):
        profile = build_byzantine_stock_strategy(self.effective)
        by_id = {item.identity: item for item in profile.demands}

        expected = (
            ("castle-barracks-depth-2", "barracks", 2),
            ("imperial-barracks-depth-3", "barracks", 3),
            ("imperial-barracks-depth-4", "barracks", 4),
            ("castle-stable-depth-2", "stable", 2),
            ("imperial-stable-depth-3", "stable", 3),
            ("imperial-stable-depth-4", "stable", 4),
            ("castle-range-depth-2", "archery-range", 2),
            ("imperial-range-depth-3", "archery-range", 3),
            ("imperial-range-depth-4", "archery-range", 4),
            ("castle-siege-depth-2", "siege-workshop", 2),
            ("imperial-siege-depth-3", "siege-workshop", 3),
            ("imperial-siege-depth-4", "siege-workshop", 4),
        )

        for identity, building, floor in expected:
            self.assertIn(identity, by_id)
            demand = by_id[identity]
            self.assertEqual(
                demand.execution.action,
                f"(build {building})",
            )
            self.assertIn(
                f"(building-type-count-total {building} < {floor})",
                demand.execution.requirements,
            )
            self.assertEqual(
                demand.execution.witness,
                f"(building-type-count {building} >= {floor})",
            )
            self.assertEqual(demand.execution.release, demand.execution.witness)

        observation_by_id = {item.identity: item.expression for item in profile.observations}
        self.assertIn(
            "(unit-type-count-total cataphract-line >= 6)",
            observation_by_id["strategy-production-stable-depth-6"],
        )
        self.assertIn(
            "(unit-type-count-total camel-rider-line >= 6)",
            observation_by_id["strategy-production-stable-depth-6"],
        )
        for demand in by_id.values():
            if "-depth-" in demand.identity:
                self.assertFalse(
                    any(
                        "up-pending-objects" in requirement
                        for requirement in demand.execution.requirements
                    ),
                    demand.identity,
                )

    def test_imperial_spend_envelope_uses_bounded_resource_thresholds(self):
        profile = build_byzantine_stock_strategy(self.effective)
        observations = {item.identity: item.expression for item in profile.observations}

        self.assertEqual(
            observations["strategy-imperial-spend-food"],
            "(and (current-age >= imperial-age) (food-amount >= 2200))",
        )
        self.assertEqual(
            observations["strategy-imperial-spend-wood"],
            "(and (current-age >= imperial-age) (wood-amount >= 2200))",
        )
        self.assertEqual(
            observations["strategy-imperial-spend-gold"],
            "(and (current-age >= imperial-age) (gold-amount >= 2500))",
        )

    def test_imperial_replacement_demands_follow_standing_floor_loss_and_spend_envelope(self):
        profile = build_byzantine_stock_strategy(self.effective)
        by_id = {item.identity: item for item in profile.demands}

        cataphract = by_id["imperial-cataphract-sustain"]
        self.assertEqual(cataphract.target.minimum, 30)
        self.assertEqual(
            tuple(item.observation_ref for item in cataphract.reason),
            (
                "strategy-imperial-spend-food",
                "strategy-imperial-spend-gold",
                "strategy-imperial-cataphract-replacement",
            ),
        )
        self.assertIn(
            "(unit-type-count-total cataphract-line < 30)",
            cataphract.execution.requirements,
        )
        self.assertIn(
            "strategy-imperial-cataphract-replacement",
            [item.observation_ref for item in cataphract.reason],
        )

        ram = by_id["imperial-ram-sustain"]
        self.assertEqual(ram.target.minimum, 8)
        self.assertIn(
            "strategy-imperial-ram-replacement",
            [item.observation_ref for item in ram.reason],
        )
        self.assertIn(
            "(unit-type-count-total battering-ram-line < 8)",
            ram.execution.requirements,
        )

    def test_imperial_sustain_demands_run_to_their_declared_targets(self):
        profile = build_byzantine_stock_strategy(self.effective)
        by_id = {item.identity: item for item in profile.demands}
        expected = {
            "imperial-cataphract-sustain": 30,
            "imperial-varangian-sustain": 24,
            "imperial-ram-sustain": 8,
            "imperial-trebuchet-sustain": 8,
        }
        for identity, minimum in expected.items():
            demand = by_id[identity]
            self.assertIn(
                f"(unit-type-count-total {demand.execution.action.split()[-1].rstrip(')')} < {minimum})",
                demand.execution.requirements,
            )
            self.assertFalse(
                any("< 12)" in requirement or "< 2)" in requirement for requirement in demand.execution.requirements),
                demand.identity,
            )

    def test_imperial_provider_depth_reopens_after_attrition_floor_loss(self):
        profile = build_byzantine_stock_strategy(self.effective)
        by_id = {item.identity: item for item in profile.demands}
        observations = {item.identity: item.expression for item in profile.observations}

        self.assertIn(
            "strategy-production-barracks-replacement",
            observations,
        )
        self.assertEqual(
            observations["strategy-production-barracks-replacement"],
            "(and (current-age >= imperial-age) "
            "(or (unit-type-count halberdier < 18) "
            "(or (unit-type-count varangian-guard < 12) "
            "(unit-type-count 359 < 12)))",
        )
        self.assertIn(
            "strategy-production-barracks-replacement",
            [
                evidence.observation_ref
                for evidence in by_id["imperial-barracks-depth-3"].reason
            ],
        )
        self.assertIn(
            "strategy-production-barracks-replacement",
            [
                evidence.observation_ref
                for evidence in by_id["imperial-barracks-depth-4"].reason
            ],
        )

    def test_imperial_military_backbone_and_scaling_demands_are_exact(self):
        profile = build_byzantine_stock_strategy(self.effective)
        by_id = {item.identity: item for item in profile.demands}
        for identity, minimum in (
            ("imperial-halberdier-floor", 18),
            ("imperial-elite-skirmisher-floor", 18),
            ("imperial-hussar-floor", 12),
            ("imperial-premium-gold-floor", 12),
            ("imperial-trebuchet-floor", 4),
            ("imperial-open-halberdier-band", 24),
            ("imperial-open-elite-skirmisher-band", 24),
            ("imperial-open-hussar-band", 16),
            ("imperial-fortified-halberdier-band", 24),
            ("imperial-fortified-elite-skirmisher-band", 20),
            ("imperial-fortified-hussar-band", 12),
            ("imperial-trashwar-halberdier-band", 30),
            ("imperial-trashwar-elite-skirmisher-band", 30),
            ("imperial-trashwar-hussar-band", 18),
        ):
            self.assertIn(identity, by_id)
            self.assertEqual(by_id[identity].target.minimum, minimum)

        self.assertIn(
            "(food-amount >= 2400)",
            by_id["imperial-open-halberdier-band"].execution.requirements,
        )
        self.assertIn(
            "(players-building-type-count any-enemy 104 >= 1)",
            by_id["imperial-fortified-elite-skirmisher-band"].execution.requirements,
        )
        self.assertIn(
            "(gold-amount <= 800)",
            by_id["imperial-trashwar-hussar-band"].execution.requirements,
        )

    def test_imperial_upgrade_ladder_has_required_technologies_and_gates(self):
        profile = build_byzantine_stock_strategy(self.effective)
        by_id = {item.identity: item for item in profile.demands}
        for identity, gate in (
            ("research-pikeman", "(unit-type-count-total spearman-line >= 6)"),
            ("research-elite-skirmisher", "(unit-type-count-total skirmisher-line >= 6)"),
            ("research-husbandry", "(unit-type-count-total scout-cavalry-line >= 6)"),
            ("research-halberdier", "(unit-type-count pikeman >= 8)"),
            ("research-hussar", "(unit-type-count-total scout-cavalry-line >= 6)"),
            ("research-bracer", "(unit-type-count-total skirmisher-line >= 12)"),
            ("research-plate-mail", "(unit-type-count halberdier >= 12)"),
            ("research-plate-barding", "(unit-type-count hussar >= 8)"),
        ):
            self.assertIn(identity, by_id)
            self.assertIn(gate, by_id[identity].execution.requirements)

        self.assertNotIn(
            "research-blast-furnace",
            by_id,
        )
        self.assertNotIn(
            "research-bloodlines",
            by_id,
        )
        self.assertNotIn(
            "research-siege-engineers",
            by_id,
        )

    def test_imperial_attack_strategic_numbers_are_owned_by_endgame_push_control(self):
        profile = build_byzantine_stock_strategy(self.effective)
        modes = {mode.identity: mode for mode in profile.strategic_number_modes}
        for identity in (
            "attack-groups-feudal",
            "attack-groups-castle",
            "attack-allocation-flush",
            "attack-allocation-rush",
            "attack-allocation-boom",
            "attack-allocation-castle-power",
        ):
            self.assertEqual(modes[identity].maximum_age, (
                Age.FEUDAL if identity == "attack-groups-feudal" else Age.CASTLE
            ))

    def test_stock_profile_has_explicit_control_and_water_modes(self):
        profile = build_byzantine_stock_strategy(self.effective)
        sn_ids = {mode.native_strategic_number_id for mode in profile.strategic_number_modes}
        self.assertTrue({18, 36, 42, 227}.issubset(sn_ids))
        self.assertIsNotNone(profile.attack_plan)
        self.assertIsNotNone(profile.duc_plan)
        self.assertIsNotNone(profile.endgame_plan)
        self.assertEqual(profile.endgame_plan.identity, "byzantine-endgame-v1")

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
