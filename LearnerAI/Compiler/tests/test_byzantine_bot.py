"""Focused tests for the deployable Byzantine bot policy."""

from __future__ import annotations

import unittest

from Compiler.clients.basilisk import ByzantineProfile, resolve_effective_civ
from Compiler.clients.basilisk.compiler import compile_strategy_profile
from Compiler.bots.byzantine import build_byzantine_bot_profile


class ByzantineBotPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        cls.profile = build_byzantine_bot_profile(cls.effective)

    def test_profile_has_real_castle_age_transition(self):
        demand = self.profile.demand("castle-age-transition")
        self.assertEqual(demand.execution.action, "(research castle-age)")
        self.assertIn("(can-research-with-escrow castle-age)", demand.execution.requirements)

    def test_profile_has_staged_villager_production(self):
        identities = {item.identity for item in self.profile.demands}
        self.assertIn("villagers-dark-22", identities)
        self.assertIn("villagers-dark-counter-24", identities)
        self.assertIn("villagers-dark-fast-castle-26", identities)
        self.assertIn("villagers-dark-water-24", identities)
        self.assertIn("villagers-feudal-30", identities)
        self.assertIn("villagers-castle-45", identities)
        self.assertIn("villagers-imperial-70", identities)

    def test_opening_plan_demands_consume_underlying_observations(self):
        demands = {item.identity: item for item in self.profile.demands}
        self.assertIn(
            "(and (not (map-type islands)) (and (not (map-type arena)) (players-unit-type-count any-enemy militia-line >= 5)))",
            demands["villagers-dark-counter-24"].execution.requirements,
        )
        self.assertIn(
            "(and (map-type arena) (not (players-unit-type-count any-enemy militia-line >= 5)))",
            demands["villagers-dark-fast-castle-26"].execution.requirements,
        )
        self.assertIn(
            "(map-type islands)",
            demands["villagers-dark-water-24"].execution.requirements,
        )
        for identity in (
            "villagers-dark-counter-24",
            "villagers-dark-fast-castle-26",
            "villagers-dark-water-24",
        ):
            requirements = demands[identity].execution.requirements
            self.assertFalse(any("(goal opening-plan" in item for item in requirements))
            self.assertFalse(any("(up-compare-goal opening-plan" in item for item in requirements))

    def test_profile_has_conditional_feudal_and_castle_responses(self):
        demands = {item.identity: item for item in self.profile.demands}
        self.assertIn(
            "(players-unit-type-count any-enemy scout-cavalry-line >= 3)",
            demands["counter-mounted-spears"].execution.requirements,
        )
        self.assertIn(
            "(players-unit-type-count any-enemy archer-line >= 3)",
            demands["counter-ranged-skirmishers"].execution.requirements,
        )
        self.assertIn(
            "(players-unit-type-count any-enemy archer-line >= 3)",
            demands["feudal-archery-range"].execution.requirements,
        )
        self.assertIn(
            "(players-unit-type-count any-enemy militia-line >= 5)",
            demands["castle-varangian-guard-floor"].execution.requirements,
        )

    def test_compilation_is_deterministic_and_contains_core_actions(self):
        first = compile_strategy_profile(self.profile, self.effective)
        second = compile_strategy_profile(self.profile, self.effective)
        self.assertEqual(first, second)
        self.assertIn("(research castle-age)", first)
        self.assertIn("(research loom)", first)
        self.assertIn("(train villager)", first)
        self.assertIn("(train cataphract)", first)
        self.assertIn("(build barracks)", first)
        self.assertIn("(build lumber-camp)", first)
        self.assertIn("(build mining-camp)", first)
        self.assertIn("(build mill)", first)
        self.assertIn("(build farm)", first)
        self.assertIn("(build market)", first)
        self.assertIn("(train spearman-line)", first)
        self.assertIn("(not (players-unit-type-count any-enemy militia-line >= 5))", first)
        self.assertIn("(train varangian-guard)", first)
        self.assertIn("(players-unit-type-count any-enemy militia-line >= 5)", first)
        self.assertIn("(attack-now)", first)


    def test_profile_has_feudal_engine_continuity(self):
        demands = {item.identity: item for item in self.profile.demands}
        barracks = demands["feudal-barracks"]
        self.assertIn("(current-age >= feudal-age)", barracks.execution.requirements)
        self.assertIn("(can-build barracks)", barracks.execution.requirements)
        self.assertIn("MOUNTED_PRESSURE_FEUDAL", {
            item.identity for item in self.profile.counter_packages
        })
        self.assertIn("RANGED_PRESSURE_FEUDAL", {
            item.identity for item in self.profile.counter_packages
        })
        self.assertEqual(
            demands["counter-mounted-spears"].target.minimum,
            4,
        )
        self.assertEqual(
            demands["counter-ranged-skirmishers"].target.minimum,
            4,
        )

    def test_economy_modes_encode_resource_priority_by_position(self):
        from LearnerAI.Compiler.clients.basilisk import EconomyMode

        expected = {
            EconomyMode.BASE: (50, 30, 20, 5),
            EconomyMode.COUNTER_FEUDAL: (42, 40, 18, 8),
            EconomyMode.FAST_CASTLE: (55, 15, 30, 3),
            EconomyMode.WATER_ECONOMY: (40, 40, 20, 5),
            EconomyMode.WATER_CONTROL: (38, 42, 20, 8),
            EconomyMode.CASTLE_CONVERSION: (45, 30, 25, 7),
            EconomyMode.IMPERIAL_CONVERSION: (40, 25, 35, 7),
        }
        policies = {
            item.mode: item.allocation
            for item in self.profile.economy_controller.policies
        }
        self.assertEqual(
            set(policies),
            set(expected),
        )
        for mode, values in expected.items():
            allocation = policies[mode]
            self.assertEqual(
                (allocation.food, allocation.wood, allocation.gold, allocation.builders),
                values,
            )

    def test_economy_research_priority_does_not_preempt_conversion(self):
        demands = {item.identity: item for item in self.profile.demands}
        self.assertIn(
            "(unit-type-count-total villager >= 30)",
            demands["research-hand-cart"].execution.requirements,
        )
        self.assertIn(
            "(unit-type-count-total villager >= 35)",
            demands["research-bow-saw"].execution.requirements,
        )
        bow_saw_id = int(demands["research-bow-saw"].target.entity_id)
        self.assertIn(
            f"(up-research-status c: {bow_saw_id} >= 3)",
            demands["research-two-man-saw"].execution.requirements,
        )
        self.assertIn(
            "(unit-type-count-total villager >= 50)",
            demands["research-two-man-saw"].execution.requirements,
        )
        self.assertIn(
            "(current-age >= imperial-age)",
            demands["research-two-man-saw"].execution.requirements,
        )
        self.assertIn(
            "(players-unit-type-count any-enemy militia-line >= 5)",
            demands["research-chemistry"].execution.requirements,
        )
        self.assertIn(
            "(unit-type-count-total villager >= 45)",
            demands["research-conscription"].execution.requirements,
        )

    def test_feudal_economy_prioritizes_wood_for_cheap_counters(self):
        from LearnerAI.Compiler.clients.basilisk import EconomyMode

        policy = next(
            item
            for item in self.profile.economy_controller.policies
            if int(item.mode) == int(EconomyMode.COUNTER_FEUDAL)
        )
        self.assertEqual(policy.allocation.food, 42)
        self.assertEqual(policy.allocation.wood, 40)
        self.assertEqual(policy.allocation.gold, 18)
        self.assertEqual(policy.allocation.builders, 8)

    def test_feudal_research_is_sequenced_around_the_active_package(self):
        demands = {item.identity: item for item in self.profile.demands}
        wheelbarrow_id = int(demands["research-wheelbarrow"].target.entity_id)
        self.assertIn(
            f"(up-research-status c: {wheelbarrow_id} >= 3)",
            demands["research-double-bit-axe"].execution.requirements,
        )
        self.assertIn(
            f"(up-research-status c: {wheelbarrow_id} >= 3)",
            demands["research-horse-collar"].execution.requirements,
        )
        self.assertIn(
            "(building-type-count-total 87 >= 1)",
            demands["research-fletching"].execution.requirements,
        )
        self.assertIn(
            "(players-unit-type-count any-enemy archer-line >= 3)",
            demands["research-fletching"].execution.requirements,
        )

    def test_castle_transition_waits_for_feudal_pressure_to_clear(self):
        demand = self.profile.demand("castle-age-transition")
        self.assertIn(
            "(not (players-unit-type-count any-enemy militia-line >= 5))",
            demand.execution.requirements,
        )
        self.assertIn(
            "(unit-type-count-total villager >= 24)",
            demand.execution.requirements,
        )

    def test_profile_has_conditional_castle_economic_expansion(self):
        demand = self.profile.demand("castle-second-town-center")
        self.assertIn("(map-type arena)", demand.execution.requirements)
        self.assertIn("(map-type arena)", demand.execution.requirements)
        self.assertIn("(unit-type-count-total villager >= 35)", demand.execution.requirements)
        self.assertIn(
            "(not (players-unit-type-count any-enemy militia-line >= 5))",
            demand.execution.requirements,
        )

    def test_profile_has_cataphract_logistica_branch(self):
        demands = {item.identity: item for item in self.profile.demands}
        logistica = demands["castle-logistica"]
        self.assertEqual(logistica.execution.action, "(research ri-logistica)")
        self.assertIn("(can-research-with-escrow ri-logistica)", logistica.execution.requirements)
        self.assertIn(
            "(or (map-type arena) (players-unit-type-count any-enemy militia-line >= 5))",
            demands["castle-cataphract-floor"].execution.requirements,
        )

    def test_profile_has_conditional_monks_and_siege_support(self):
        demands = {item.identity: item for item in self.profile.demands}
        self.assertIn(
            "(building-type-count-total monastery >= 1)",
            demands["castle-monk-floor"].execution.requirements,
        )
        self.assertIn(
            "(map-type arena)",
            demands["castle-monk-floor"].execution.requirements,
        )
        self.assertIn(
            "(or (players-unit-type-count any-enemy mangonel-line >= 2) (players-unit-type-count any-enemy archer-line >= 4))",
            demands["castle-siege-capability"].execution.requirements,
        )
        self.assertIn(
            "(or (players-unit-type-count any-enemy mangonel-line >= 2) (players-unit-type-count any-enemy archer-line >= 4))",
            demands["castle-siege-capability"].execution.requirements,
        )

    def test_castle_research_sequences_from_feudal_economy(self):
        demands = {item.identity: item for item in self.profile.demands}
        wheelbarrow_id = int(demands["research-wheelbarrow"].target.entity_id)
        double_bit_axe_id = int(demands["research-double-bit-axe"].target.entity_id)
        horse_collar_id = int(demands["research-horse-collar"].target.entity_id)
        gold_mining_id = int(demands["research-gold-mining"].target.entity_id)
        fletching_id = int(demands["research-fletching"].target.entity_id)

        self.assertIn(
            f"(up-research-status c: {wheelbarrow_id} >= 3)",
            demands["research-hand-cart"].execution.requirements,
        )
        self.assertIn(
            f"(up-research-status c: {double_bit_axe_id} >= 3)",
            demands["research-bow-saw"].execution.requirements,
        )
        self.assertIn(
            f"(up-research-status c: {gold_mining_id} >= 3)",
            demands["research-gold-shaft-mining"].execution.requirements,
        )
        self.assertIn(
            f"(up-research-status c: {horse_collar_id} >= 3)",
            demands["research-heavy-plow"].execution.requirements,
        )
        self.assertIn(
            f"(up-research-status c: {fletching_id} >= 3)",
            demands["research-bodkin-arrow"].execution.requirements,
        )

    def test_profile_has_castle_economy_and_imperial_conversion_guards(self):
        from Compiler.clients.basilisk import EconomyMode

        policy = next(
            item
            for item in self.profile.economy_controller.policies
            if int(item.mode) == int(EconomyMode.CASTLE_CONVERSION)
        )
        self.assertEqual(policy.allocation.food, 45)
        self.assertEqual(policy.allocation.wood, 30)
        self.assertEqual(policy.allocation.gold, 25)
        self.assertEqual(policy.allocation.builders, 7)

        imperial = self.profile.demand("imperial-conversion")
        self.assertIn(
            "(unit-type-count-total villager >= 40)",
            imperial.execution.requirements,
        )

    def test_castle_artifact_contains_conversion_actions(self):
        artifact = compile_strategy_profile(self.profile, self.effective)
        self.assertIn("(research ri-logistica)", artifact)
        self.assertIn("(build town-center)", artifact)
        self.assertIn("(train monk)", artifact)
        self.assertIn("(train mangonel-line)", artifact)
        self.assertIn("(research imperial-age)", artifact)

    def test_profile_has_broad_imperial_mounted_response(self):
        demands = {item.identity: item for item in self.profile.demands}
        mounted_guard = "(or (players-unit-type-count any-enemy knight >= 3) (players-unit-type-count any-enemy scout-cavalry-line >= 3))"
        for identity in (
            "imperial-halberdier",
            "imperial-heavy-camel",
            "imperial-halberdier-counter",
            "imperial-heavy-camel-counter",
        ):
            self.assertIn(mounted_guard, demands[identity].execution.requirements)

    def test_water_dock_releases_when_dock_exists(self):
        demand = self.profile.demand("water-dock-capability")
        self.assertIn("(map-type islands)", demand.execution.requirements)
        self.assertEqual(
            demand.invalidation[0].observation_ref,
            "strategy-dock-exists",
        )

    def test_profile_has_imperial_trash_war_packages(self):
        demands = {item.identity: item for item in self.profile.demands}
        self.assertIn(
            "(or (players-unit-type-count any-enemy knight >= 3) (players-unit-type-count any-enemy scout-cavalry-line >= 3))",
            demands["imperial-halberdier-counter"].execution.requirements,
        )
        self.assertIn(
            "(players-unit-type-count any-enemy archer-line >= 4)",
            demands["imperial-elite-skirmisher-counter"].execution.requirements,
        )
        self.assertIn(
            "(train 359)",
            demands["imperial-halberdier-counter"].execution.action,
        )
        self.assertIn(
            "(train 6)",
            demands["imperial-elite-skirmisher-counter"].execution.action,
        )
        self.assertIn(
            "(train 330)",
            demands["imperial-heavy-camel-counter"].execution.action,
        )

    def test_profile_has_imperial_gunpowder_conversion(self):
        demands = {item.identity: item for item in self.profile.demands}
        self.assertIn(
            "(players-unit-type-count any-enemy militia-line >= 5)",
            demands["imperial-hand-cannoneer-counter"].execution.requirements,
        )
        self.assertIn(
            "(up-research-status c: 47 >= 3)",
            demands["imperial-hand-cannoneer-counter"].execution.requirements,
        )
        self.assertIn(
            "(train 5)",
            demands["imperial-hand-cannoneer-counter"].execution.action,
        )
        self.assertIn(
            "(players-unit-type-count any-enemy militia-line >= 5)",
            demands["research-chemistry"].execution.requirements,
        )

    def test_profile_has_imperial_cataphract_conversion(self):
        demands = {item.identity: item for item in self.profile.demands}
        self.assertIn(
            "(up-research-status c: 61 >= 3)",
            demands["imperial-elite-cataphract-floor"].execution.requirements,
        )
        self.assertIn(
            "(up-research-status c: 361 >= 3)",
            demands["imperial-elite-cataphract-floor"].execution.requirements,
        )
        self.assertIn(
            "(or (map-type arena) (players-unit-type-count any-enemy militia-line >= 5))",
            demands["imperial-elite-cataphract-floor"].execution.requirements,
        )
        self.assertIn(
            "(research 361)",
            demands["imperial-elite-cataphract"].execution.action,
        )

    def test_profile_has_imperial_production_conversion(self):
        from Compiler.clients.basilisk import EconomyMode

        policy = next(
            item
            for item in self.profile.economy_controller.policies
            if item.mode is EconomyMode.IMPERIAL_CONVERSION
        )
        self.assertEqual(policy.allocation.food, 40)
        self.assertEqual(policy.allocation.wood, 25)
        self.assertEqual(policy.allocation.gold, 35)
        self.assertEqual(policy.allocation.builders, 7)

        imperial = self.profile.demand("imperial-conversion")
        self.assertIn(
            "(unit-type-count-total villager >= 40)",
            imperial.execution.requirements,
        )

    def test_imperial_artifact_contains_win_condition_actions(self):
        artifact = compile_strategy_profile(self.profile, self.effective)
        self.assertIn("(train 359)", artifact)
        self.assertIn("(train 6)", artifact)
        self.assertIn("(train 330)", artifact)
        self.assertIn("(train 5)", artifact)
        self.assertIn("(research 361)", artifact)
        self.assertIn("(research conscription)", artifact)

    def test_islands_open_fishing_starts_in_dark_and_reaches_four(self):
        demand = self.profile.demand("water-fishing-opening")
        self.assertEqual(demand.target.minimum, 4)
        self.assertIn("(current-age >= dark-age)", demand.execution.requirements)
        self.assertIn("(map-type islands)", demand.execution.requirements)
        self.assertIn("(building-type-count-total dock >= 1)", demand.execution.requirements)
        self.assertEqual(demand.execution.action, "(train fishing-ship)")
        self.assertEqual(demand.execution.witness, "(unit-type-count fishing-ship >= 4)")


    def test_profile_has_basic_resource_dropsites(self):
        demands = {item.identity: item for item in self.profile.demands}
        for identity in (
            "dark-lumber-camp",
            "dark-mining-camp",
            "dark-mill-capability",
            "wood-dropsite-extension",
            "mining-dropsite-extension",
        ):
            self.assertIn(identity, demands)

        self.assertIn(
            "(unit-type-count-total villager >= 7)",
            demands["dark-lumber-camp"].execution.requirements,
        )
        self.assertIn(
            "(dropsite-min-distance wood > 12)",
            demands["wood-dropsite-extension"].execution.requirements,
        )
        self.assertIn(
            "(or (dropsite-min-distance gold > 5) (dropsite-min-distance stone > 5))",
            demands["dark-mining-camp"].execution.requirements,
        )
        self.assertIn(
            "(or (dropsite-min-distance gold > 12) (dropsite-min-distance stone > 12))",
            demands["mining-dropsite-extension"].execution.requirements,
        )
        self.assertIn(
            "(unit-type-count-total villager >= 7)",
            demands["dark-mill-capability"].execution.requirements,
        )
        self.assertIn(
            "(dropsite-min-distance food > 5)",
            demands["dark-mill-capability"].execution.requirements,
        )

    def test_profile_has_farm_bank_and_market_recovery(self):
        demands = {item.identity: item for item in self.profile.demands}
        self.assertIn("farm-bank-stage-1", demands)
        self.assertIn("farm-bank-stage-2", demands)
        self.assertIn("farm-bank-stage-3", demands)

        self.assertIn(
            "(building-type-count-total mill >= 1)",
            demands["farm-bank-stage-1"].execution.requirements,
        )
        self.assertIn(
            "(unit-type-count-total villager >= 18)",
            demands["farm-bank-stage-1"].execution.requirements,
        )
        self.assertIn(
            "(food-amount < 500)",
            demands["farm-bank-stage-1"].execution.requirements,
        )
        self.assertIn(
            "(unit-type-count-total villager >= 30)",
            demands["farm-bank-stage-2"].execution.requirements,
        )
        self.assertIn(
            "(food-amount < 700)",
            demands["farm-bank-stage-2"].execution.requirements,
        )
        self.assertIn(
            "(unit-type-count-total villager >= 45)",
            demands["farm-bank-stage-3"].execution.requirements,
        )
        self.assertIn(
            "(food-amount < 900)",
            demands["farm-bank-stage-3"].execution.requirements,
        )

        market = demands["feudal-market-recovery"]
        self.assertIn("(current-age >= feudal-age)", market.execution.requirements)
        self.assertIn("(unit-type-count-total villager >= 24)", market.execution.requirements)
        self.assertIn(
            "(or (food-amount < 300) (or (wood-amount < 150) (gold-amount < 150)))",
            market.execution.requirements,
        )

    def test_profile_has_basic_feudal_spear_floor(self):
        demand = self.profile.demand("feudal-spear-floor")
        self.assertEqual(demand.target.minimum, 2)
        self.assertEqual(demand.execution.action, "(train spearman-line)")
        self.assertIn("(current-age >= feudal-age)", demand.execution.requirements)
        self.assertIn("(not (map-type islands))", demand.execution.requirements)

    def test_profile_has_basic_economic_placement_and_exploration_sns(self):
        modes = {
            item.identity: item
            for item in self.profile.strategic_number_modes
        }
        expected = {
            "lumber-camp-placement-distance": (260, 40),
            "mining-camp-placement-distance": (261, 40),
            "mill-placement-distance": (87, 28),
            "initial-exploration-requirement": (167, 2),
        }
        for identity, (native_id, value) in expected.items():
            self.assertEqual(modes[identity].native_strategic_number_id, native_id)
            self.assertEqual(modes[identity].value, value)

    def test_profile_has_complete_water_capability_chain(self):
        demands = {item.identity: item for item in self.profile.demands}

        dock = demands["water-dock-capability"]
        self.assertIn("(map-type islands)", dock.execution.requirements)
        self.assertIn("(can-build dock)", dock.execution.requirements)
        self.assertIn(
            "(building-type-count-total dock < 1)",
            dock.execution.requirements,
        )

        for identity in (
            "water-fishing-continuity",
            "water-transport-capability",
            "water-naval-defense",
            "water-naval-control",
        ):
            self.assertIn(identity, demands)

        artifact = compile_strategy_profile(self.profile, self.effective)
        self.assertIn("(build dock)", artifact)
        self.assertIn("(train fishing-ship)", artifact)
        self.assertIn("(train transport-ship)", artifact)
        self.assertIn("(train fire-galley)", artifact)
        self.assertIn("(train galley)", artifact)

    def test_profile_has_long_housing_ladder(self):
        identities = {item.identity for item in self.profile.demands}
        self.assertIn("house-stage-1", identities)
        self.assertIn("house-stage-12", identities)

    def test_compilation_contains_staged_housing(self):
        artifact = compile_strategy_profile(self.profile, self.effective)
        self.assertIn("(build house)", artifact)
        self.assertIn("(goal strategy-posture 3)", artifact)


if __name__ == "__main__":
    unittest.main()
