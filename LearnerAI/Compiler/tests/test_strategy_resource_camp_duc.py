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
        camp_rules = [rule for rule in plan.rules if rule.identity.startswith("byzantine-camp-placement-")]
        self.assertEqual(len(camp_rules), 16)

        for resource, building, maximum in expected:
            for floor in range(1, maximum + 1):
                identity = f"byzantine-camp-placement-{resource}-{floor}"
                rule = next(rule for rule in camp_rules if rule.identity == identity)
                sources = {expression.source for expression in rule.facts}
                actions = {expression.source for expression in rule.actions}

                self.assertIn(
                    f"(up-find-resource c: {resource} c: {'1' if floor == 1 else '40'})",
                    actions,
                )
                self.assertIn(
                    f"(up-set-target-object search-remote c: {floor - 1})",
                    actions,
                )
                self.assertIn(
                    f"(up-get-point position-object byzantine-camp-{resource}-point-{floor})",
                    actions,
                )
                self.assertIn(
                    f"(up-set-target-point byzantine-camp-{resource}-point-{floor})",
                    actions,
                )
                self.assertIn(
                    f"(up-build place-point 0 c: {building})",
                    actions,
                )
                self.assertIn(
                    f"(goal demand-economy-{resource if resource != 'wood' else 'lumber'}-camp-floor-{floor} 1)",
                    sources,
                )
                self.assertIn(f"(can-build {building})", sources)
                self.assertIn(
                    f"(building-type-count-total {building} < {floor})",
                    sources,
                )
                if resource == "stone":
                    self.assertIn(
                        "(and (current-age >= feudal-age) (resource-found stone))",
                        sources,
                    )
                else:
                    self.assertIn(f"(resource-found {resource})", sources)

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
