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

    def test_feudal_economy_prioritizes_wood_for_cheap_counters(self):
        from LearnerAI.Compiler.clients.basilisk import EconomyMode

        policy = next(
            item
            for item in self.profile.economy_controller.policies
            if item.mode is EconomyMode.COUNTER_FEUDAL
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
            f"(research-completed {wheelbarrow_id})",
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
