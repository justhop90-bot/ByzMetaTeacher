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
        self.assertIn("(train varangian-guard)", first)
        self.assertIn("(players-unit-type-count any-enemy militia-line >= 5)", first)
        self.assertIn("(attack-now)", first)

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
