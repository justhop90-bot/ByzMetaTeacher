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
                self.assertFalse(
                    any(
                        expression.head in {"not", "or", "and"}
                        for rule in (search_rule, place_rule)
                        for expression in rule.facts
                    ),
                    f"{resource} floor {floor} DUC guards must be native facts",
                )

                search_actions = {expression.source for expression in search_rule.actions}
                place_facts = {expression.source for expression in place_rule.facts}
                place_actions = {expression.source for expression in place_rule.actions}

                expected_limit = 1 if (floor == 1 or (resource == "wood" and floor == 2)) else 40
                self.assertIn(
                    f"(up-find-resource c: {resource} c: {expected_limit})",
                    search_actions,
                )
                self.assertIn(
                    f"(up-get-search-state {resource}-camp-search-state-{floor})",
                    search_actions,
                )
                self.assertNotIn(
                    "(up-modify-sn sn-focus-player-number",
                    search_actions,
                )
                expected_index = 0 if floor <= 2 else floor - 2
                self.assertIn(
                    f"(up-compare-goal {resource}-camp-search-state-{floor} > {expected_index})",
                    place_facts,
                )
                self.assertIn(
                    f"(up-set-target-object search-remote c: {expected_index})",
                    place_facts,
                )
                self.assertIn(
                    f"(up-set-target-object search-remote c: {expected_index})",
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
                self.assertNotIn(
                    f"(up-build place-point 0 c: {building})",
                    place_actions,
                )
                demand_name = (
                    f"economy-lumber-camp-floor-{floor}"
                    if resource == "wood" and floor <= 2
                    else f"economy-wood-camp-floor-{floor}"
                    if resource == "wood"
                    else f"economy-{resource}-camp-floor-{floor}"
                )
                demand = profile.demand(demand_name)
                self.assertTrue(demand.native_placement)
                if resource == "wood" and floor == 1:
                    self.assertEqual(
                        demand.native_fallback_requirements,
                        (
                            "(current-age == dark-age)",
                            "(unit-type-count-total villager >= 15)",
                        ),
                    )
                else:
                    self.assertEqual(demand.native_fallback_requirements, ())
                self.assertEqual(
                    demand.execution_demands[0].witness,
                    f"(building-type-count {building} >= {floor})",
                )
                self.assertIn(
                    f"(set-goal demand-{demand_name} issued-{demand_name})",
                    {action.source for action in place_rule.control_actions},
                )
                self.assertIn(
                    "(set-goal action-claim-build-pass-singleton 1)",
                    {action.source for action in place_rule.control_actions},
                )

                search_facts = {expression.source for expression in search_rule.facts}
                if resource == "stone":
                    self.assertIn(
                        "(current-age >= feudal-age)",
                        search_facts,
                    )
                    self.assertIn(
                        "(resource-found stone)",
                        search_facts,
                    )
                else:
                    self.assertIn(
                        f"(resource-found {resource})",
                        search_facts,
                    )

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
            for floor in range(1, maximum + 1):
                demand_name = (
                    f"economy-lumber-camp-floor-{floor}"
                    if resource == "wood" and floor <= 2
                    else f"economy-wood-camp-floor-{floor}"
                    if resource == "wood"
                    else f"economy-{resource}-camp-floor-{floor}"
                )
                self.assertNotIn(
                    f"; Action issuance: {demand_name} | ACTIVE -> ISSUED",
                    output,
                )
                self.assertIn(
                    f"; Native placement owner: {demand_name}",
                    output,
                )
                self.assertIn(
                    f"Native DUC rule: byzantine-camp-placement-{resource}-{floor}-place",
                    output,
                )
        self.assertIn(
            "; Native placement fallback: economy-lumber-camp-floor-1",
            output,
        )
        self.assertIn("(defconst status-resource 3)", output)
        self.assertIn("(defconst list-active 0)", output)
        self.assertIn("(defconst status-ready 2)", output)
        self.assertIn(
            "(set-goal action-claim-build-pass-singleton 1)",
            output,
        )
        self.assertIn(
            "(current-age == dark-age)",
            output,
        )

if __name__ == "__main__":
    unittest.main()
