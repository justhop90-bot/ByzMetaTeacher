import unittest
from pathlib import Path
from LearnerAI.Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_strategy,
    compile_strategy_profile,
    lower_strategy_profile,
)
from LearnerAI.Compiler.ir.civ_profile import resolve_effective_civ
from LearnerAI.Compiler.ir.game_data import Resource


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
                "opening-selector-counter-feudal",
                "opening-selector-defensive-standard",
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
        expected_opening_facts = {
            "opening-selector-water-control": (
                "(goal opening-plan -1)",
                "(map-type islands)",
                "(or (players-unit-type-count any-enemy galley-line >= 2) "
                "(players-unit-type-count any-enemy fire-galley-line >= 2))",
            ),
            "opening-selector-water-economy": (
                "(goal opening-plan -1)",
                "(map-type islands)",
                "(not (or (players-unit-type-count any-enemy galley-line >= 2) "
                "(players-unit-type-count any-enemy fire-galley-line >= 2)))",
            ),
            "opening-selector-fast-castle": (
                "(goal opening-plan -1)",
                "(map-type arena)",
                "(not (or (players-unit-type-count any-enemy knight >= 3) "
                "(or (players-unit-type-count any-enemy archer-line >= 4) "
                "(players-unit-type-count any-enemy militia-line >= 5))))",
            ),
            "opening-selector-counter-feudal": (
                "(goal opening-plan -1)",
                "(not (map-type islands))",
                "(not (map-type arena))",
                "(or (players-unit-type-count any-enemy knight >= 3) "
                "(or (players-unit-type-count any-enemy archer-line >= 4) "
                "(players-unit-type-count any-enemy militia-line >= 5)))",
            ),
            "opening-selector-defensive-standard": (
                "(goal opening-plan -1)",
                "(not (map-type islands))",
                "(not (map-type arena))",
                "(not (or (players-unit-type-count any-enemy knight >= 3) "
                "(or (players-unit-type-count any-enemy archer-line >= 4) "
                "(players-unit-type-count any-enemy militia-line >= 5))))",
            ),
        }
        for rule in (fast_castle, counter_feudal):
            self.assertEqual(
                tuple(fact.source for fact in rule.facts),
                expected_opening_facts[rule.identity],
            )
        for rule_id, expected_facts in expected_opening_facts.items():
            rule = next(rule for rule in control.rules if rule.identity == rule_id)
            self.assertEqual(tuple(fact.source for fact in rule.facts), expected_facts)
            self.assertTrue(all(len(fact.source) <= 255 for fact in rule.facts))

        output = compile_strategy_profile(profile, self.effective)
        self.assertIn("(goal opening-plan -1)", output)
        self.assertIn("(set-goal opening-plan 5)", output)
        self.assertIn("(set-goal opening-plan 4)", output)
        self.assertIn("(set-goal opening-plan 3)", output)
        self.assertIn("(set-goal opening-plan 2)", output)
        self.assertIn("(set-goal opening-plan 1)", output)

    def test_opening_pressure_uses_the_broader_early_threat_signal(self):
        profile = build_byzantine_strategy(self.effective)
        pressure = profile.observation("strategy-opening-pressure").expression
        self.assertEqual(
            pressure,
            "(or (players-unit-type-count any-enemy knight >= 3) "
            "(or (players-unit-type-count any-enemy archer-line >= 4) "
            "(players-unit-type-count any-enemy militia-line >= 5)))",
        )
        self.assertEqual(
            pressure,
            profile.observation("strategy-enemy-pressure").expression,
        )

    def test_feudal_transition_waits_for_first_resource_fronts(self):
        profile = build_byzantine_strategy(self.effective)
        transition = profile.demand("feudal-transition")
        requirements = tuple(transition.execution.requirements)
        self.assertEqual(
            requirements,
            (
                "(current-age == dark-age)",
                "(building-type-count-total lumber-camp >= 1)",
                "(building-type-count-total mining-camp >= 1)",
                "(can-research-with-escrow feudal-age)",
            ),
        )

    def test_castle_age_transition_is_compiler_owned_and_protected(self):
        profile = build_byzantine_strategy(self.effective)
        transition = profile.demand("castle-age-transition")

        self.assertEqual(
            tuple(transition.execution.requirements),
            (
                "(current-age == feudal-age)",
                "(building-type-count-total blacksmith >= 1)",
                "(building-type-count-total market >= 1)",
                "(can-research-with-escrow castle-age)",
            ),
        )
        self.assertEqual(transition.execution.action, "(research castle-age)")
        self.assertEqual(
            transition.execution.escrow_release_resources,
            (Resource.FOOD, Resource.GOLD),
        )
        self.assertEqual(
            tuple(
                (floor.resource, floor.minimum)
                for floor in transition.opportunity_cost.protected_floors
            ),
            ((Resource.FOOD, 800), (Resource.GOLD, 200)),
        )

    def test_age_bank_controller_preserves_villager_continuity_until_maturity(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        rule = next(
            rule for rule in control.rules
            if rule.identity == "age-bank-villager-production"
        )
        sources = tuple(fact.source for fact in rule.facts)
        self.assertIn("(unit-type-count-total villager < 110)", sources)
        self.assertIn("(population-headroom > 0)", sources)
        self.assertIn("(can-train villager)", sources)
        self.assertIn(
            "(not (and (current-age == dark-age) "
            "(and (unit-type-count-total villager >= 21) "
            "(and (building-type-count-total lumber-camp >= 1) "
            "(and (building-type-count-total mining-camp >= 1) "
            "(can-research-with-escrow feudal-age)))))",
            sources,
        )
        self.assertIn(
            "(not (and (current-age == feudal-age) "
            "(and (unit-type-count-total villager >= 28) "
            "(and (building-type-count-total blacksmith >= 1) "
            "(and (building-type-count-total market >= 1) "
            "(can-research-with-escrow castle-age)))))",
            sources,
        )
        self.assertEqual(
            tuple(action.source for action in rule.actions),
            ("(train villager)",),
        )

    def test_camp_floor_two_requires_a_remote_resource_front(self):
        profile = build_byzantine_strategy(self.effective)

        for resource in ("wood", "gold", "stone"):
            demand = profile.demand(f"economy-{resource}-camp-floor-2")
            self.assertTrue(
                any(
                    "dropsite-min-distance" in requirement
                    for requirement in demand.execution.requirements
                ),
                resource,
            )

    def test_adaptive_outpost_starts_released_and_reopens_from_pressure(self):
        profile = build_byzantine_strategy(self.effective)
        demand = profile.demand("adaptive-outpost")

        self.assertEqual(demand.initial_state.name, "RELEASED")
        self.assertEqual(
            tuple(demand.execution.requirements),
            ("(current-age >= feudal-age)", "(can-build outpost)"),
        )

    def test_stone_camp_is_castle_commitment_owned(self):
        profile = build_byzantine_strategy(self.effective)

        for floor in range(1, 6):
            demand = profile.demand(f"economy-stone-camp-floor-{floor}")
            self.assertEqual(demand.initial_state.name, "RELEASED")
            self.assertIn(
                "(and (current-age >= feudal-age) (resource-found stone))",
                demand.execution.requirements,
            )
            self.assertIsNotNone(demand.opportunity_cost)
            self.assertEqual(demand.opportunity_cost.owner, "castle-trajectory")

    def test_feudal_research_yields_to_castle_feasibility(self):
        profile = build_byzantine_strategy(self.effective)

        for identity in ("research-double-bit-axe", "research-horse-collar"):
            requirements = tuple(profile.demand(identity).execution.requirements)
            self.assertIn(
                "(not (can-research-with-escrow castle-age))",
                requirements,
            )

        wheelbarrow = tuple(
            profile.demand("research-wheelbarrow").execution.requirements
        )
        self.assertIn(
            "(not (can-research-with-escrow castle-age))",
            wheelbarrow,
        )

    def test_checked_in_runtime_preserves_age_bank_arbitration(self):
        repo_root = Path(__file__).resolve().parents[3]
        runtime = (repo_root / "Byzantine.per").read_text(encoding="utf-8")

        villager_start = runtime.index("; Persistent civilian production")
        villager_end = runtime.index(
            "; Pending diagnostics: early-defensive-spears",
            villager_start,
        )
        villager_rule = runtime[villager_start:villager_end]
        self.assertIn("(unit-type-count-total villager >= 21)", villager_rule)
        self.assertIn(
            "(unit-type-count-total villager >= bt-castle-age-villager-maturity)",
            villager_rule,
        )
        self.assertIn("(building-type-count-total blacksmith >= 1)", villager_rule)
        self.assertIn("(building-type-count-total market >= 1)", villager_rule)
        self.assertNotIn(
            "(not (and\n        (current-age == dark-age)\n        (can-research-with-escrow feudal-age)\n    ))",
            villager_rule,
        )
        self.assertNotIn(
            "(not (and\n        (current-age == feudal-age)\n        (can-research-with-escrow castle-age)\n    ))",
            villager_rule,
        )

        outpost_start = runtime.index("; Pending diagnostics: adaptive-outpost")
        outpost_end = runtime.index("; Pending diagnostics: adaptive-watch-tower", outpost_start)
        outpost_section = runtime[outpost_start:outpost_end]
        init_section = runtime[
            runtime.index("; Demand initialization"):outpost_start
        ]
        self.assertIn("(set-goal demand-adaptive-outpost 0)", init_section)
        self.assertIn("(current-age >= feudal-age)", outpost_section)

        dba_start = runtime.index("; Action issuance: research-double-bit-axe")
        dba_end = runtime.index("; Pending diagnostics: research-horse-collar", dba_start)
        dba_rule = runtime[dba_start:dba_end]
        self.assertIn(
            "(not (can-research-with-escrow castle-age))",
            dba_rule,
        )

        horse_start = runtime.index("; Action issuance: research-horse-collar")
        horse_end = runtime.index("; Pending diagnostics: research-hand-cart", horse_start)
        horse_rule = runtime[horse_start:horse_end]
        self.assertIn(
            "(not (can-research-with-escrow castle-age))",
            horse_rule,
        )

    def test_opening_selection_materially_changes_native_economy_writers(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        expected = {
            "base": (55, 30, 15, 5),
            "counter_feudal": (42, 38, 20, 8),
            "fast_castle": (55, 15, 30, 3),
        }
        for mode_name, values in expected.items():
            rules = {
                rule.identity: rule
                for rule in control.rules
                if rule.identity.startswith(f"economy-controller-write-{mode_name}-")
            }
            expected_rule_count = 5 if mode_name == "base" else 4
            self.assertEqual(len(rules), expected_rule_count)
            written = tuple(
                next(
                    action.args[1]
                    for action in rule.actions
                    if action.head == "set-strategic-number"
                )
                for rule in (
                    rules[f"economy-controller-write-{mode_name}-sn-food-gatherer-percentage"],
                    rules[f"economy-controller-write-{mode_name}-sn-wood-gatherer-percentage"],
                    rules[f"economy-controller-write-{mode_name}-sn-gold-gatherer-percentage"],
                    rules[f"economy-controller-write-{mode_name}-sn-percent-civilian-builders"],
                )
            )
            self.assertEqual(tuple(map(int, written)), values)

        self.assertNotEqual(expected["base"][:3], expected["fast_castle"][:3])
        self.assertNotEqual(expected["base"][:3], expected["counter_feudal"][:3])

        fast_selection = next(
            rule for rule in control.rules
            if rule.identity == "economy-controller-select-fast-castle"
        )
        self.assertEqual(
            tuple(fact.source for fact in fast_selection.facts),
            (
                "(and (current-age >= feudal-age) (current-age < castle-age))",
                "(not (players-unit-type-count any-enemy knight >= 3))",
                "(not (players-unit-type-count any-enemy archer-line >= 4))",
                "(not (players-unit-type-count any-enemy militia-line >= 5))",
                "(goal opening-plan 3)",
            ),
        )
        self.assertTrue(all(len(fact.source) <= 255 for fact in fast_selection.facts))

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


if __name__ == "__main__":
    unittest.main()
