import unittest

from LearnerAI.Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_strategy,
    compile_strategy_profile,
)
from LearnerAI.Compiler.ir.civ_profile import resolve_effective_civ


class ByzantineResourceCampDucTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())

    def test_byzantine_camp_floors_are_lowered_to_native_duc_placement(self):
        profile = build_byzantine_strategy(self.effective)
        plan = profile.duc_plan
        self.assertIsNotNone(plan)
        assert plan is not None

        expected = (
            ("wood", "lumber-camp", 6),
            ("gold", "mining-camp", 5),
            ("stone", "mining-camp", 5),
        )
        for resource, building, maximum in expected:
            for floor in range(1, maximum + 1):
                search_identity = f"byzantine-camp-placement-{resource}-{floor}-search"
                place_identity = f"byzantine-camp-placement-{resource}-{floor}-place"
                search_rule = next(rule for rule in plan.rules if rule.identity == search_identity)
                place_rule = next(rule for rule in plan.rules if rule.identity == place_identity)

                search_actions = {expression.source for expression in search_rule.actions}
                place_facts = {expression.source for expression in place_rule.facts}
                place_actions = {expression.source for expression in place_rule.actions}

                expected_limit = 1 if floor == 1 else 40
                self.assertIn(
                    f"(up-find-resource c: {resource} c: {expected_limit})",
                    search_actions,
                )
                self.assertIn(
                    f"(up-get-search-state {resource}-camp-search-state-{floor})",
                    search_actions,
                )
                self.assertIn(
                    f"(up-compare-goal {resource}-camp-search-state-{floor} > {floor - 1})",
                    place_facts,
                )
                self.assertIn(
                    f"(up-set-target-object search-remote c: {floor - 1})",
                    place_facts,
                )
                self.assertIn(
                    f"(up-set-target-object search-remote c: {floor - 1})",
                    place_actions,
                )
                self.assertIn(
                    f"(up-get-point position-object {resource}-camp-point-{floor})",
                    place_actions,
                )
                self.assertIn(
                    f"(up-set-target-point {resource}-camp-point-{floor})",
                    place_actions,
                )
                self.assertIn(
                    f"(up-build place-point 0 c: {building})",
                    place_actions,
                )
                demand_name = f"economy-{resource}-camp-floor-{floor}"
                demand = profile.demand(demand_name)
                self.assertTrue(demand.native_placement)
                self.assertEqual(
                    demand.execution_demands[0].witness,
                    f"(building-type-count {building} >= {floor})",
                )

                if resource == "stone":
                    self.assertIn(
                        "(and (current-age >= feudal-age) (resource-found stone))",
                        search_rule.facts[6].source,
                    )
                else:
                    self.assertIn(
                        f"(resource-found {resource})",
                        search_rule.facts[6].source,
                    )

        fallback = next(
            rule for rule in plan.rules
            if rule.identity == "byzantine-camp-placement-wood-1-fallback"
        )
        self.assertIn("(current-age == dark-age)", {fact.source for fact in fallback.facts})
        self.assertIn("(build lumber-camp)", {action.source for action in fallback.actions})

    def test_native_camp_placement_replaces_generic_action_issuance(self):
        output = compile_strategy_profile(
            build_byzantine_strategy(self.effective),
            self.effective,
        )
        for resource, building, maximum in (
            ("wood", "lumber-camp", 6),
            ("gold", "mining-camp", 5),
            ("stone", "mining-camp", 5),
        ):
            demand_name = f"economy-{resource}-camp-floor-1"
            start = output.index(f"; Construction observation: {demand_name}")
            end = output.find("\n; ", start + 10)
            section = output[start:] if end < 0 else output[start:end]
            self.assertNotIn(
                f"(build {building})",
                section,
                f"{demand_name} must not use the generic demand action issuer",
            )
            self.assertIn(
                f"Native DUC rule: byzantine-camp-placement-{resource}-1",
                output,
            )
        self.assertIn("(build lumber-camp)", output)

if __name__ == "__main__":
    unittest.main()
