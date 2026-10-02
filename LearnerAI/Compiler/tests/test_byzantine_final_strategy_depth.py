import unittest

from Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_strategy,
    compile_strategy_profile,
)
from Compiler.ir.civ_profile import resolve_effective_civ


class ByzantineFinalStrategyDepthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        cls.profile = build_byzantine_strategy(cls.effective)
        cls.output = compile_strategy_profile(cls.profile, cls.effective)
        cls.demands = {item.identity: item for item in cls.profile.demands}

    def test_late_land_composition_transitions_are_real_production_demands(self):
        for identity in (
            "castle-camel-transition-floor",
            "imperial-halberdier-floor",
            "imperial-heavy-camel-floor",
        ):
            self.assertIn(identity, self.demands)
        self.assertIn("(train 329)", self.output)
        self.assertIn("(train 359)", self.output)
        self.assertIn("(train 330)", self.output)

    def test_fortification_has_exposure_conditioned_tower_layers(self):
        for identity in (
            "adaptive-watch-tower",
            "adaptive-stone-wall",
            "adaptive-guard-tower",
            "imperial-keep-floor",
            "imperial-bombard-tower-floor",
        ):
            self.assertIn(identity, self.demands)
        for action in (
            "(build 79)",
            "(build 117)",
            "(build 234)",
            "(build 235)",
            "(build 236)",
        ):
            self.assertIn(action, self.output)
        self.assertIn("(players-unit-type-count any-enemy knight >= 3)", self.output)

    def test_monastery_strategy_is_selective_and_relic_policy_is_emitted(self):
        for identity in (
            "research-sanctity",
            "research-fervor",
            "research-atonement",
            "research-block-printing",
            "research-theocracy",
        ):
            self.assertIn(identity, self.demands)
        self.assertIn("byzantine-relic-acquisition", {rule.identity for rule in self.profile.duc_plan.rules})
        self.assertIn("byzantine-relic-denial-contest", {rule.identity for rule in self.profile.duc_plan.rules})
        relic_output = "\\n".join(
            str(expr.source)
            for rule in self.profile.duc_plan.rules
            for expr in (*rule.facts, *rule.actions)
        )
        self.assertIn("(up-find-remote c: relic-class* c: 1)", relic_output)
        self.assertIn("(up-find-local c: 125 c: 1)", relic_output)
        self.assertIn("(up-target-objects 0 action-move -1 -1)", relic_output)

    def test_second_wave_water_is_real_policy_with_research_dependencies(self):
        for identity in (
            "water-hulk-floor",
            "water-war-hulk-floor",
            "water-carrack-floor",
            "water-demolition-ship-floor",
            "water-heavy-demolition-ship-floor",
            "water-trade-cog-floor",
            "research-demolition-ship",
            "research-heavy-demolition-ship",
        ):
            self.assertIn(identity, self.demands)
        for action in (
            "(train 2626)",
            "(train 2627)",
            "(train 2628)",
            "(train 527)",
            "(train 528)",
            "(train 17)",
            "(research 905)",
            "(research 244)",
        ):
            self.assertIn(action, self.output)


if __name__ == "__main__":
    unittest.main()
