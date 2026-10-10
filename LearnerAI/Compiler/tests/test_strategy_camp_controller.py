import unittest

from LearnerAI.Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_strategy,
    compile_strategy_profile,
    lower_strategy_profile,
)
from LearnerAI.Compiler.ir.civ_profile import resolve_effective_civ


class ByzantineCampControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())

    def test_resource_found_has_a_semantic_adapter(self):
        from LearnerAI.Compiler.primitives.native_binder import NativeSupportState
        from LearnerAI.Compiler.primitives.registry import default_de_registry

        self.assertIs(
            default_de_registry().support_state("resource-found"),
            NativeSupportState.EXECUTABLE_SAFE,
        )

    def test_three_resource_front_observations_and_floors_exist(self):
        profile = build_byzantine_strategy(self.effective)

        for resource, max_count in (("wood", 6), ("gold", 5), ("stone", 5)):
            active = profile.observation(f"camp-front-{resource}-active")
            remote = profile.observation(f"camp-front-{resource}-remote")
            self.assertIn("resource-found", active.expression)
            self.assertIn("dropsite-min-distance", remote.expression)

            for floor in range(1, max_count + 1):
                demand = profile.demand(f"economy-{resource}-camp-floor-{floor}")
                self.assertEqual(demand.capability_intent.kind.value, "BUILD")
                self.assertEqual(demand.execution_demands[0].action, f"(build {'lumber-camp' if resource == 'wood' else 'mining-camp'})")
                requirements = demand.execution_demands[0].requirements
                floor_active = (
                    profile.observation("camp-front-gold-secondary-active")
                    if resource == "gold" and floor >= 2
                    else active
                )
                self.assertIn(
                    floor_active.identity,
                    {item.observation_ref for item in demand.reason},
                )
                self.assertIn(floor_active.expression, requirements)
                if resource == "gold" and floor >= 2:
                    self.assertIn("(current-age >= feudal-age)", floor_active.expression)
                self.assertIn("(building-type-count", demand.execution_demands[0].witness)
                if floor >= 2:
                    self.assertNotIn(
                        remote.expression,
                        requirements,
                        "resource-front admission must not depend on nearest-dropsite distance",
                    )

    def test_camp_builds_use_the_existing_construction_lifecycle(self):
        compilation = lower_strategy_profile(
            build_byzantine_strategy(self.effective),
            self.effective,
        )

        for resource, building in (
            ("wood", "lumber-camp"),
            ("gold", "mining-camp"),
            ("stone", "mining-camp"),
        ):
            demand = next(
                item
                for item in compilation.demands
                if item.name == f"economy-{resource}-camp-floor-1"
            )
            self.assertIsNotNone(demand.construction_lifecycle)
            self.assertEqual(demand.construction_lifecycle.building, building)
            self.assertEqual(demand.action.expression.source, f"(build {building})")

        output = compile_strategy_profile(
            build_byzantine_strategy(self.effective),
            self.effective,
        )
        self.assertIn("; Construction observation: economy-wood-camp-floor-1", output)
        self.assertIn("; Construction observation: economy-gold-camp-floor-1", output)
        self.assertIn("; Construction observation: economy-stone-camp-floor-1", output)

    def test_secondary_camp_floors_have_binder_owned_resource_front_dispatch(self):
        compilation = lower_strategy_profile(
            build_byzantine_strategy(self.effective),
            self.effective,
        )
        plan = compilation.duc_plan
        assert plan is not None

        expected_floors = {
            "wood": range(2, 7),
            "gold": range(2, 6),
            "stone": range(2, 6),
        }
        identities = {rule.identity for rule in plan.rules}
        managed = set(plan.managed_demand_identities)
        for resource, floors in expected_floors.items():
            building = "lumber-camp" if resource == "wood" else "mining-camp"
            building_id = 562 if resource == "wood" else 584
            for floor in floors:
                demand = f"economy-{resource}-camp-floor-{floor}"
                self.assertIn(demand, managed)
                search = f"byzantine-resource-camp-search-{resource}-{floor}"
                place = f"byzantine-resource-camp-place-{resource}-{floor}"
                self.assertTrue({search, place}.issubset(identities))
                place_rule = next(rule for rule in plan.rules if rule.identity == place)
                facts = tuple(item.source for item in place_rule.facts)
                actions = tuple(item.source for item in place_rule.actions)
                self.assertIn(
                    f"(building-type-count {building} >= {floor - 1})",
                    facts,
                )
                self.assertIn(
                    f"(up-compare-goal resource-camp-remote-count > {floor - 2})",
                    facts,
                )
                self.assertIn(
                    f"(up-set-target-object search-remote c: {floor - 2})",
                    actions,
                )
                self.assertIn(
                    f"(up-build place-point 0 c: {building_id})",
                    actions,
                )
                if floor == 2:
                    self.assertNotIn(
                        "(up-compare-goal resource-camp-remote-count > 1)",
                        facts,
                    )
                    self.assertNotIn(
                        "(up-set-target-object search-remote c: 1)",
                        actions,
                    )
                self.assertLess(
                    actions.index("(up-get-point position-object resource-camp-point)"),
                    actions.index("(up-set-target-point resource-camp-point)"),
                )
                self.assertLess(
                    actions.index("(up-set-target-point resource-camp-point)"),
                    actions.index(f"(up-build place-point 0 c: {building})"),
                )

                search_rule = next(rule for rule in plan.rules if rule.identity == search)
                search_actions = tuple(item.source for item in search_rule.actions)
                self.assertIn("(up-filter-status c: 3 c: 0)", search_actions)
                self.assertIn(
                    "(up-get-search-state resource-camp-search-state)",
                    search_actions,
                )
                output = next(
                    request for request in plan.output_requests
                    if request.rule_identity == search
                    and request.command == "up-get-search-state"
                )
                self.assertEqual(output.request.width, 4)
                input_request = next(
                    request for request in plan.input_requests
                    if request.rule_identity == place
                    and request.section == "FACT"
                    and request.source == output.request.request_id
                )
                self.assertEqual(input_request.source_offset, 3)

    def test_native_camp_placement_controller_reasserts_geometry_and_widens_on_remote_front(self):
        compilation = lower_strategy_profile(
            build_byzantine_strategy(self.effective),
            self.effective,
        )
        control = compilation.control_plan
        assert control is not None

        state_ids = {state.identifier for state in control.states}
        self.assertIn("sn-lumber-camp-max-distance", state_ids)
        self.assertIn("sn-mining-camp-max-distance", state_ids)
        self.assertIn("sn-allow-adjacent-dropsites", state_ids)
        self.assertIn("sn-dropsite-separation-distance", state_ids)

        output = compile_strategy_profile(
            build_byzantine_strategy(self.effective),
            self.effective,
        )
        for value in (16, 20, 28, 36):
            self.assertIn(f"(set-strategic-number sn-lumber-camp-max-distance {value})", output)
            self.assertIn(f"(set-strategic-number sn-mining-camp-max-distance {value})", output)
        self.assertIn("(set-strategic-number sn-allow-adjacent-dropsites 0)", output)
        self.assertIn("(set-strategic-number sn-dropsite-separation-distance 6)", output)
        self.assertIn("(up-modify-sn sn-lumber-camp-max-distance c:+ 4)", output)
        self.assertIn("(up-modify-sn sn-mining-camp-max-distance c:+ 4)", output)


if __name__ == "__main__":
    unittest.main()
