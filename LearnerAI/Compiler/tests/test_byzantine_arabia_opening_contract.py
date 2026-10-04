import unittest

from LearnerAI.Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_strategy,
    compile_strategy_profile,
    lower_strategy_profile,
)
from LearnerAI.Compiler.ir.civ_profile import resolve_effective_civ
from LearnerAI.Compiler.ir.game_data import Resource


class ByzantineArabiaOpeningContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())

    def test_loom_is_a_real_standard_feudal_research_lifecycle(self):
        profile = build_byzantine_strategy(self.effective)
        demand = profile.demand("research-loom")
        self.assertEqual(demand.capability_intent.entity_id, 22)
        requirements = demand.execution_demands[0].requirements
        self.assertNotIn("(goal opening-plan 1)", " ".join(requirements))
        self.assertNotIn("(goal opening-plan 2)", " ".join(requirements))
        self.assertTrue(any("(current-age == dark-age)" in requirement for requirement in requirements))
        self.assertTrue(any("(unit-type-count-total villager >= 13)" in requirement for requirement in requirements))
        self.assertTrue(any("(building-type-count-total lumber-camp >= 1)" in requirement for requirement in requirements))
        self.assertTrue(any("(building-type-count-total mining-camp >= 1)" in requirement for requirement in requirements))

        feudal = profile.demand("feudal-transition")
        self.assertNotIn(
            "(research-completed 22)",
            feudal.execution_demands[0].requirements,
        )
        self.assertEqual(
            feudal.execution_demands[0].action_witness_gates,
            ("(research-completed 22)",),
        )

        output = compile_strategy_profile(profile, self.effective)
        issuance_start = output.index("; Action issuance: feudal-transition")
        issuance_end = output.index("=>", issuance_start)
        issuance_block = output[issuance_start:issuance_end]
        self.assertIn("(research-completed 22)", issuance_block)
        self.assertIn("(research ri-loom)", output)

    def test_arabia_pressure_contract_detects_real_early_pressure(self):
        profile = build_byzantine_strategy(self.effective)
        pressure = profile.observation("strategy-arabia-early-pressure")
        expression = pressure.expression
        self.assertIn("militia-line >= 3", expression)
        self.assertIn("scout-cavalry-line >= 3", expression)
        self.assertIn("archer-line >= 3", expression)
        self.assertIn("knight >= 1", expression)
        army_presence = profile.observation("strategy-arabia-early-army-presence").expression
        self.assertIn("(players-building-type-count any-enemy barracks >= 1)", army_presence)
        self.assertIn("(players-military-population any-enemy >= 3)", army_presence)


    def test_pressure_clear_returns_economy_to_base_arbitration(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None
        rules = {rule.identity: rule for rule in control.rules}
        base = rules["economy-controller-select-base"]
        self.assertIn("(goal opening-plan 1)", " ".join(f.source for f in base.facts))
        counter = rules["economy-controller-select-counter-pressure"]
        self.assertIn("(current-age >= feudal-age)", " ".join(f.source for f in counter.facts))

    def test_castle_bank_is_persistent_and_releases_at_castle(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        state_names = {state.identifier for state in control.states}
        self.assertIn("byzantine-castle-bank-state", state_names)

        rules = {
            rule.identity: rule
            for rule in control.rules
            if rule.identity.startswith("economy-controller-castle-bank-")
        }
        self.assertIn("economy-controller-castle-bank-protect-hard", rules)
        self.assertIn("economy-controller-castle-bank-protect-buffer", rules)
        self.assertIn("economy-controller-castle-bank-break-hard-reserve", rules)
        self.assertIn("economy-controller-castle-bank-release-on-castle", rules)

        release = rules["economy-controller-castle-bank-release-on-castle"]
        self.assertIn("(current-age >= castle-age)", release.facts[0].source)

    def test_feudal_economic_research_cannot_spend_after_castle_bank_is_reserved(self):
        profile = build_byzantine_strategy(self.effective)
        for identity in (
            "research-double-bit-axe",
            "research-horse-collar",
            "research-wheelbarrow",
            "research-gold-mining",
        ):
            demand = profile.demand(identity)
            floors = {
                floor.resource: floor.minimum
                for floor in demand.opportunity_cost.protected_floors
            }
            self.assertGreaterEqual(floors[Resource.FOOD], 800)
            self.assertGreaterEqual(floors[Resource.GOLD], 200)


if __name__ == "__main__":
    unittest.main()