from dataclasses import replace
import unittest
from LearnerAI.Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_strategy,
    compile_strategy_profile,
    lower_strategy_profile,
)
from LearnerAI.Compiler.ir.civ_profile import resolve_effective_civ


class ByzantineStrategyControlSliceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())

    def test_varangian_is_a_conditioned_castle_infantry_package(self):
        profile = build_byzantine_strategy(self.effective)

        self.assertIn("strategy-enemy-infantry-pressure", {x.identity for x in profile.observations})
        self.assertIn("strategy-enemy-infantry-pressure-cleared", {x.identity for x in profile.observations})

        demand = profile.demand("castle-varangian-guard-floor")
        self.assertEqual(demand.capability_intent.entity_type, "unit-line")
        self.assertEqual(demand.capability_intent.entity_id, "varangian-guard-line")
        self.assertEqual(demand.target.minimum, 2)
        self.assertIn("strategy-enemy-infantry-pressure", {
            x.observation_ref for x in demand.reason
        })
        self.assertIn("strategy-enemy-infantry-pressure-cleared", {
            x.observation_ref for x in demand.invalidation
        })

        package = next(
            item for item in profile.military_compositions
            if item.identity == "castle-infantry-package"
        )
        self.assertIn("castle-varangian-guard-floor", package.production_demands)

        standard = next(
            item for item in profile.military_compositions
            if item.identity == "castle-standard-package"
        )
        self.assertNotIn("castle-varangian-guard-floor", standard.production_demands)

    def test_map_profile_and_opening_selector_are_typed(self):
        profile = build_byzantine_strategy(self.effective)

        self.assertEqual(
            tuple(item.identity for item in profile.map_profile),
            ("ARABIA", "ARENA", "STANDARD_LAND", "HYBRID", "ISLANDS"),
        )
        self.assertEqual(
            {
                item.identity: item.default_opening
                for item in profile.map_profile
                if item.identity in {"ARABIA", "STANDARD_LAND"}
            },
            {"ARABIA": "DEFENSIVE_STANDARD", "STANDARD_LAND": "FAST_CASTLE"},
        )
        self.assertEqual(profile.opening_selector.plan_id, "byzantine-opening-v1")

    def test_opening_selection_is_durable_and_precedence_ordered(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        self.assertIn("opening-plan", {state.identifier for state in control.states})
        rule_ids = tuple(
            rule.identity for rule in control.rules
            if rule.identity.startswith("opening-selector-")
        )
        self.assertEqual(
            rule_ids,
            (
                "opening-selector-water-control",
                "opening-selector-water-economy",
                "opening-selector-fast-castle",
                "opening-selector-defensive-standard-arabia",
                "opening-selector-fast-castle-standard-land",
                "opening-selector-counter-feudal",
            ),
        )

        fast_castle = next(
            rule for rule in control.rules
            if rule.identity == "opening-selector-fast-castle"
        )
        counter_feudal = next(
            rule for rule in control.rules
            if rule.identity == "opening-selector-counter-feudal"
        )
        self.assertIn("(map-type arena)", fast_castle.facts[0].source)
        self.assertIn("(players-unit-type-count any-enemy knight >= 3)", fast_castle.facts[0].source)
        self.assertIn("(players-unit-type-count any-enemy archer-line >= 4)", fast_castle.facts[0].source)
        self.assertIn("(players-unit-type-count any-enemy militia-line >= 5)", fast_castle.facts[0].source)
        self.assertIn("(players-unit-type-count any-enemy militia-line >= 5)", counter_feudal.facts[0].source)
        arabia_standard = next(
            rule for rule in control.rules
            if rule.identity == "opening-selector-defensive-standard-arabia"
        )
        self.assertIn("(map-type arabia)", arabia_standard.facts[0].source)
        self.assertIn("(players-unit-type-count any-enemy knight >= 3)", arabia_standard.facts[0].source)
        self.assertIn("(players-unit-type-count any-enemy archer-line >= 4)", arabia_standard.facts[0].source)
        self.assertIn("(players-unit-type-count any-enemy militia-line >= 5)", arabia_standard.facts[0].source)

        output = compile_strategy_profile(profile, self.effective)
        self.assertIn("(goal opening-plan -1)", output)
        self.assertIn("opening-selector-defensive-standard-arabia", output)
        self.assertNotIn("(map-type hybrid)", output)
        self.assertIn("(set-goal opening-plan 5)", output)
        self.assertIn("(set-goal opening-plan 4)", output)
        self.assertIn("(set-goal opening-plan 3)", output)
        self.assertIn("(set-goal opening-plan 2)", output)
        self.assertIn("(set-goal opening-plan 1)", output)

    def test_map_profile_default_opening_controls_selector_emission(self):
        profile = build_byzantine_strategy(self.effective)
        custom_profiles = tuple(
            replace(item, default_opening="FAST_CASTLE")
            if item.identity.value == "ARABIA"
            else item
            for item in profile.map_profile
        )
        custom_profile = replace(profile, map_profile=custom_profiles)
        compilation = lower_strategy_profile(custom_profile, self.effective)
        control = compilation.control_plan
        assert control is not None
        rule_ids = {rule.identity for rule in control.rules if rule.identity.startswith("opening-selector-")}
        self.assertNotIn("opening-selector-defensive-standard-arabia", rule_ids)

    def test_economy_controller_uses_only_documented_civilian_allocation_sns(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        self.assertEqual(
            profile.economy_controller.controller_id,
            "byzantine-economy-v1",
        )
        from LearnerAI.Compiler.clients.basilisk import EconomyMode
        self.assertEqual(
            {item.mode for item in profile.economy_controller.policies},
            set(EconomyMode),
        )
        written_sources = {
            action.source
            for rule in control.rules
            if rule.identity.startswith("economy-controller-")
            for action in rule.actions
            if action.head == "set-strategic-number"
        }
        self.assertTrue(
            all(
                any(name in source for source in written_sources)
                for name in (
                    "sn-food-gatherer-percentage",
                    "sn-wood-gatherer-percentage",
                    "sn-gold-gatherer-percentage",
                    "sn-percent-civilian-builders",
                )
            )
        )

        output = compile_strategy_profile(profile, self.effective)
        self.assertIn("(defconst sn-food-gatherer-percentage 117)", output)
        self.assertIn("(defconst sn-wood-gatherer-percentage 120)", output)
        self.assertIn("(defconst sn-gold-gatherer-percentage 118)", output)
        self.assertIn("(defconst sn-percent-civilian-builders 1)", output)

        fast_castle_policy = next(
            item for item in profile.economy_controller.policies
            if item.mode == EconomyMode.FAST_CASTLE
        )
        self.assertEqual(
            (fast_castle_policy.allocation.food,
             fast_castle_policy.allocation.wood,
             fast_castle_policy.allocation.gold),
            (50, 25, 25),
        )

        expected_floors = {
            "research-double-bit-axe": {"food": 900, "gold": 250},
            "research-horse-collar": {"food": 900, "gold": 250},
            "research-wheelbarrow": {"food": 1000, "gold": 250},
            "research-gold-mining": {"food": 900, "gold": 250},
        }
        for demand in profile.demands:
            if demand.identity in expected_floors:
                requirements = demand.execution_demands[0].requirements
                self.assertIn("(current-age >= feudal-age)", requirements)
                self.assertNotIn("(current-age >= castle-age)", requirements)
                self.assertIn(
                    f"(food-amount >= {expected_floors[demand.identity]['food']})",
                    requirements,
                )
                self.assertIn(
                    f"(gold-amount >= {expected_floors[demand.identity]['gold']})",
                    requirements,
                )
                self.assertIsNotNone(demand.opportunity_cost)
                floors = {
                    floor.resource.value: floor.minimum
                    for floor in demand.opportunity_cost.protected_floors
                }
                self.assertEqual(
                    floors,
                    {"FOOD": expected_floors[demand.identity]["food"], "GOLD": 250},
                )

        from LearnerAI.Compiler.clients.basilisk import EconomyMode
        self.assertIn(
            EconomyMode.FAST_IMPERIAL,
            {item.mode for item in profile.economy_controller.policies},
        )


    def test_feudal_reservation_is_age_transition_owned(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        state_names = {state.identifier for state in control.states}
        self.assertIn("feudal-transition-bank-state", state_names)
        self.assertIn("feudal-transition-loom-recovery", state_names)

        age_transition_rules = {
            rule.identity
            for rule in control.rules
            if rule.identity.startswith("feudal-transition-bank-")
        }
        self.assertIn("feudal-transition-bank-initialize", age_transition_rules)
        self.assertIn("feudal-transition-bank-enter", age_transition_rules)
        self.assertIn("feudal-transition-bank-ready", age_transition_rules)
        self.assertIn("feudal-transition-bank-release-on-feudal", age_transition_rules)

        control_output = compile_strategy_profile(profile, self.effective)
        self.assertNotIn("economy-controller-feudal-bank-", control_output)

    def test_economy_controller_only_reads_feudal_reservation_for_civilian_allocation(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        readers = [
            rule for rule in control.rules
            if rule.identity.startswith("economy-controller-feudal-reservation-")
        ]
        self.assertGreaterEqual(len(readers), 3)
        for rule in readers:
            self.assertTrue(any(
                "(goal feudal-transition-bank-state 1)" in fact.source
                for fact in rule.facts
            ))
            self.assertTrue(all(
                "set-goal feudal-transition-bank-state" not in action.source
                for action in rule.actions
            ))

        import LearnerAI.Compiler.ir.economic_control as economic_control
        self.assertFalse(hasattr(economic_control, "FeudalBankState"))
        self.assertNotIn("feudal_bank_", control_output := compile_strategy_profile(profile, self.effective))
        self.assertIn("economy-controller-feudal-reservation-", control_output)

    def test_feudal_reservation_uses_resource_deficit_writers_not_a_static_age_allocation(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        rules = {
            rule.identity: rule
            for rule in control.rules
            if rule.identity.startswith("economy-controller-feudal-reservation-")
        }
        self.assertIn(
            "(food-amount < 500)",
            " ".join(f.source for f in rules["economy-controller-feudal-reservation-prioritize-food"].facts),
        )
        self.assertIn(
            "(gold-amount < 200)",
            " ".join(f.source for f in rules["economy-controller-feudal-reservation-prioritize-gold"].facts),
        )
        output = compile_strategy_profile(profile, self.effective)
        self.assertIn("economy-controller-feudal-reservation-prioritize-food", output)
        self.assertIn("economy-controller-feudal-reservation-prioritize-gold", output)

    def test_feudal_transition_declares_a_protected_500_food_200_gold_floor(self):
        profile = build_byzantine_strategy(self.effective)
        demand = profile.demand("feudal-transition")
        requirements = demand.execution_demands[0].requirements

        self.assertIn("(food-amount >= 500)", requirements)
        self.assertIn("(gold-amount >= 200)", requirements)
        self.assertIsNotNone(demand.opportunity_cost)
        floors = {
            floor.resource.value: floor.minimum
            for floor in demand.opportunity_cost.protected_floors
        }
        self.assertEqual(floors, {"FOOD": 500, "GOLD": 200})


if __name__ == "__main__":
    unittest.main()
