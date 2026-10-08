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

    def test_pacific_fishing_continuity_is_escrow_gated_and_pressure_aware(self):
        profile = build_byzantine_stock_strategy(self.effective)
        demand = profile.demand("water-fishing-continuity")
        requirements = tuple(demand.execution.requirements)
        requirement_text = " ".join(requirements)
        self.assertIn("(can-train fishing-ship)", requirements)
        self.assertIn(
            f"(or (not (map-type pacific-islands)) "
            f"(not {profile.observation('strategy-enemy-naval-pressure').expression}))",
            requirements,
        )
        self.assertIn("(can-train-with-escrow fishing-ship)", requirement_text)
        self.assertIn("(wood-amount >= 75)", requirement_text)
        refs = {
            evidence.observation_ref
            for evidence in demand.invalidation
            if evidence.observation_ref is not None
        }
        self.assertIn("strategy-enemy-naval-pressure", refs)

    def test_pacific_transport_escort_can_bootstrap_before_first_transport(self):
        profile = build_byzantine_stock_strategy(self.effective)
        demand = profile.demand("water-pacific-transport-escort")
        requirements = tuple(demand.execution.requirements)
        self.assertIn("(current-age >= feudal-age)", requirements)
        self.assertIn("(map-type pacific-islands)", requirements)
        self.assertIn("(building-type-count-total dock >= 1)", requirements)
        self.assertNotIn("(unit-type-count-total transport-ship >= 1)", requirements)
        self.assertNotIn("(goal pacific-transport-recovery 1)", requirements)
        self.assertIn("(can-train-with-escrow fire-galley)", requirements)

    def test_pacific_transport_escort_is_a_standing_feudal_support_capability(self):
        profile = build_byzantine_stock_strategy(self.effective)
        demand = profile.demand("water-pacific-transport-escort")
        self.assertEqual(demand.capability_intent.entity_type, "unit-line")
        self.assertEqual(demand.execution.action, "(train fire-galley)")
        self.assertIn("(can-train-with-escrow fire-galley)", demand.execution.requirements)

    def test_pacific_transport_recovery_is_a_standing_feudal_capability_after_landing(self):
        profile = build_byzantine_stock_strategy(self.effective)
        demand = profile.demand("water-pacific-transport-recovery")
        self.assertIn("(goal pacific-transport-recovery 1)", demand.execution.requirements)
        self.assertIn("(can-train-with-escrow transport-ship)", demand.execution.requirements)
        self.assertIn("(building-type-count-total dock >= 1)", demand.execution.requirements)

    def test_pacific_transport_recovery_is_pressure_suspended_but_escrow_gated(self):
        profile = build_byzantine_stock_strategy(self.effective)
        demand = profile.demand("water-pacific-transport-recovery")
        joined = " ".join(demand.execution.requirements)
        self.assertIn(
            f"(not {profile.observation('strategy-enemy-naval-pressure').expression})",
            joined,
        )
        self.assertIn("(can-train-with-escrow transport-ship)", joined)

    def test_pacific_harbor_defense_gates_naval_demands_on_pacific(self):
        profile = build_byzantine_stock_strategy(self.effective)
        for identity in ("water-naval-defense", "water-naval-control"):
            demand = profile.demand(identity)
            requirements = " ".join(demand.execution.requirements)
            self.assertIn("(goal pacific-harbor-defense 1)", requirements)
            self.assertIn("(can-train-with-escrow", requirements)

    def test_stock_profile_resolves_against_current_effective_data(self):
        profile = build_byzantine_stock_strategy(self.effective)
        resolved = resolve_strategy_profile(profile, self.effective)
        self.assertEqual(profile.profile_id, "byzantine-stock-v1")
        self.assertIn("imperial-conversion", resolved.demand_ids)
        self.assertIn("castle-second-town-center", resolved.demand_ids)
        self.assertIn("castle-cataphract-floor", resolved.demand_ids)
        self.assertIn("castle-mangonel-floor", resolved.demand_ids)
        self.assertIn("imperial-bombard-floor", resolved.demand_ids)
        for identity in (
            "imperial-halberdier-floor",
            "imperial-elite-skirmisher-floor",
            "imperial-hussar-floor",
            "research-pikeman",
            "research-elite-skirmisher",
            "research-husbandry",
            "research-halberdier",
            "research-hussar",
            "research-bracer",
        ):
            self.assertIn(identity, resolved.demand_ids)
        self.assertIn("water-fishing-continuity", resolved.demand_ids)

    def test_islands_opening_has_first_dock_capability_before_fishing(self):
        profile = build_byzantine_stock_strategy(self.effective)
        demand = profile.demand("water-dock-capability")

        self.assertEqual(demand.owner, "water-economy")
        self.assertEqual(demand.priority, StrategicPriority.CORE)
        self.assertEqual(demand.capability_intent.kind.name, "BUILD")
        self.assertEqual(demand.capability_intent.entity_type, "building")
        self.assertEqual(demand.execution.action, "(build dock)")
        self.assertIn("(or (map-type islands) (map-type pacific-islands))", demand.execution.requirements)
        self.assertIn("(building-type-count-total dock < 1)", demand.execution.requirements)
        self.assertIn("(can-build dock)", demand.execution.requirements)
        self.assertEqual(demand.execution.witness, "(building-type-count dock >= 1)")
        self.assertEqual(demand.execution.release, "(building-type-count dock >= 1)")

    def test_water_map_observation_includes_pacific_islands(self):
        profile = build_byzantine_stock_strategy(self.effective)
        observation = profile.observation("strategy-water-map")

        self.assertEqual(
            observation.expression,
            "(or (map-type islands) (map-type pacific-islands))",
        )
        island_profile = next(item for item in profile.map_profile if item.identity.value == "ISLANDS")
        self.assertEqual(
            island_profile.native_map_expression,
            "(or (map-type islands) (map-type pacific-islands))",
        )

        self.assertIn("(goal water-transport-objective 1)", {
            item.expression for item in profile.observations
            if item.identity == "strategy-transport-required"
        })

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
            "research-forging",
            "research-pikeman",
            "research-elite-skirmisher",
            "research-husbandry",
            "research-iron-casting",
            "research-padded-archer-armor",
            "research-leather-archer-armor",
            "research-halberdier",
            "research-hussar",
            "research-bracer",
            "research-ring-archer-armor",
            "research-plate-barding-armor",
            "research-scale-mail-armor",
            "research-chain-mail-armor",
            "research-plate-mail-armor",
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
            "(unit-type-count-total 441 >= 6)",
            observation_by_id["strategy-production-stable-depth-6"],
        )
        self.assertIn(
            "(unit-type-count-total 6 >= 6)",
            observation_by_id["strategy-production-range-depth-6"],
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
        self.assertEqual(cataphract.target.minimum, 18)
        self.assertEqual(
            tuple(item.observation_ref for item in cataphract.reason),
            (
                "strategy-imperial-spend-food",
                "strategy-imperial-spend-gold",
                "strategy-imperial-cataphract-replacement",
            ),
        )
        self.assertIn(
            "(unit-type-count-total cataphract-line < 18)",
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
            "imperial-cataphract-sustain": 18,
            "imperial-varangian-sustain": 14,
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


    def test_imperial_trash_backbone_has_exact_standing_floors(self):
        profile = build_byzantine_stock_strategy(self.effective)
        by_id = {item.identity: item for item in profile.demands}
        expected = {
            "imperial-halberdier-floor": ("halberdier", 18),
            "imperial-elite-skirmisher-floor": ("skirmisher-line", 18),
            "imperial-hussar-floor": ("hussar", 12),
        }
        for identity, (witness, minimum) in expected.items():
            demand = by_id[identity]
            self.assertIn(f"(unit-type-count {witness} >= {minimum})", demand.execution.witness)
            action_unit = (
                demand.execution.action.removeprefix("(train ").removesuffix(")")
            )
            self.assertIn(
                f"(unit-type-count-total {action_unit} < {minimum})",
                demand.execution.requirements,
            )
            if identity == "imperial-elite-skirmisher-floor":
                self.assertEqual(
                    demand.execution.release,
                    f"(unit-type-count 6 >= {minimum})",
                )

    def test_imperial_elite_skirmisher_production_requires_completed_upgrade(self):
        profile = build_byzantine_stock_strategy(self.effective)
        by_id = {item.identity: item for item in profile.demands}
        expected = (
            "imperial-elite-skirmisher-floor",
            "imperial-open-elite-skirmisher-standard",
            "imperial-open-elite-skirmisher-pressure",
            "imperial-open-elite-skirmisher-severe",
            "imperial-fortified-elite-skirmisher",
            "imperial-trash-elite-skirmisher-standard",
            "imperial-trash-elite-skirmisher-high",
        )
        for identity in expected:
            self.assertIn(
                "(up-research-status c: 98 >= 3)",
                by_id[identity].execution.requirements,
                identity,
            )

    def test_imperial_band_scaling_is_mutually_exclusive_and_exact(self):
        profile = build_byzantine_stock_strategy(self.effective)
        by_id = {item.identity: item for item in profile.demands}
        checks = {
            "imperial-open-halberdier-standard": ("(up-compare-goal byzantine-imperial-band-state == 1)", 24),
            "imperial-open-halberdier-pressure": ("(up-compare-goal byzantine-imperial-band-state == 1)", 30),
            "imperial-open-halberdier-severe": ("(up-compare-goal byzantine-imperial-band-state == 1)", 36),
            "imperial-open-elite-skirmisher-standard": ("(up-compare-goal byzantine-imperial-band-state == 1)", 24),
            "imperial-open-elite-skirmisher-pressure": ("(up-compare-goal byzantine-imperial-band-state == 1)", 30),
            "imperial-open-elite-skirmisher-severe": ("(up-compare-goal byzantine-imperial-band-state == 1)", 36),
            "imperial-open-hussar-standard": ("(up-compare-goal byzantine-imperial-band-state == 1)", 16),
            "imperial-open-hussar-mobile": ("(up-compare-goal byzantine-imperial-band-state == 1)", 20),
            "imperial-fortified-halberdier": ("(up-compare-goal byzantine-imperial-band-state == 2)", 24),
            "imperial-fortified-elite-skirmisher": ("(up-compare-goal byzantine-imperial-band-state == 2)", 20),
            "imperial-fortified-hussar": ("(up-compare-goal byzantine-imperial-band-state == 2)", 10),
            "imperial-trash-halberdier-standard": ("(up-compare-goal byzantine-imperial-band-state == 3)", 30),
            "imperial-trash-halberdier-high": ("(up-compare-goal byzantine-imperial-band-state == 3)", 36),
            "imperial-trash-elite-skirmisher-standard": ("(up-compare-goal byzantine-imperial-band-state == 3)", 30),
            "imperial-trash-elite-skirmisher-high": ("(up-compare-goal byzantine-imperial-band-state == 3)", 36),
            "imperial-trash-hussar-standard": ("(up-compare-goal byzantine-imperial-band-state == 3)", 18),
            "imperial-trash-hussar-high": ("(up-compare-goal byzantine-imperial-band-state == 3)", 24),
        }
        for identity, (band_guard, minimum) in checks.items():
            demand = by_id[identity]
            self.assertIn(band_guard, demand.execution.requirements)
            self.assertIn(f"< {minimum})", " ".join(demand.execution.requirements))
            self.assertEqual(demand.execution.action.count("(train "), 1)
            if "elite-skirmisher" in identity:
                self.assertEqual(
                    demand.execution.witness,
                    f"(unit-type-count skirmisher-line >= {minimum})",
                )
                self.assertEqual(
                    demand.execution.release,
                    f"(unit-type-count 6 >= {minimum})",
                )

    def test_imperial_ranged_pressure_uses_native_archer_line(self):
        profile = build_byzantine_stock_strategy(self.effective)
        by_id = {item.identity: item for item in profile.demands}

        ranged_requirements = []
        for demand in by_id.values():
            if demand.identity.startswith("imperial-"):
                ranged_requirements.extend(demand.execution.requirements)

        joined = " ".join(ranged_requirements)
        self.assertIn(
            "(players-unit-type-count any-enemy archer-line >= 8)",
            joined,
        )
        self.assertIn(
            "(players-unit-type-count any-enemy archer-line >= 12)",
            joined,
        )
        self.assertNotIn("crossbow-line", joined)

    def test_imperial_package_excludes_unavailable_blacksmith_techs(self):
        identities = {d.identity for d in build_byzantine_stock_strategy(self.effective).demands}
        self.assertNotIn("research-blast-furnace", identities)
        self.assertNotIn("research-bloodlines", identities)

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
            "(or (unit-type-count varangian-guard < 14) "
            "(unit-type-count 359 < 18)))",
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

        self.assertEqual(
            observations["strategy-production-stable-replacement"],
            "(and (current-age >= imperial-age) "
            "(or (unit-type-count cataphract < 18) "
            "(unit-type-count 441 < 12)))",
        )
        self.assertEqual(
            observations["strategy-production-range-replacement"],
            "(and (current-age >= imperial-age) "
            "(or (unit-type-count 6 < 18) "
            "(unit-type-count 492 < 14)))",
        )
        self.assertEqual(
            observations["strategy-production-siege-replacement"],
            "(and (current-age >= imperial-age) "
            "(or (unit-type-count trebuchet < 4) "
            "(or (unit-type-count bombard-cannon < 4) "
            "(unit-type-count-total mangonel-line < 4))))",
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
