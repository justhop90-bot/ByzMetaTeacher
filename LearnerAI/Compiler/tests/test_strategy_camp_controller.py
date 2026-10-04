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


    def test_all_strategy_requirement_expressions_parse(self):
        from LearnerAI.Compiler.ast import SourceLocation
        from LearnerAI.Compiler.semantic.analyzer import parse_expression

        profile = build_byzantine_strategy(self.effective)
        for demand in profile.demands:
            for requirement in demand.execution_demands[0].requirements:
                try:
                    parse_expression(requirement, SourceLocation(1))
                except Exception as exc:
                    self.fail(
                        f"malformed requirement in {demand.identity}: "
                        f"{requirement!r}: {exc}"
                    )

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
            if resource == "stone":
                self.assertIn("(current-age >= castle-age)", active.expression)
                self.assertIn("(stone-amount < 650)", active.expression)

            for floor in range(1, max_count + 1):
                demand = profile.demand(f"economy-{resource}-camp-floor-{floor}")
                self.assertEqual(demand.capability_intent.kind.value, "BUILD")
                self.assertEqual(demand.execution_demands[0].action, f"(build {'lumber-camp' if resource == 'wood' else 'mining-camp'})")
                requirements = demand.execution_demands[0].requirements
                self.assertIn(active.identity, {item.observation_ref for item in demand.reason})
                self.assertIn(active.expression, requirements)
                self.assertIn("(building-type-count", demand.execution_demands[0].witness)
                if floor >= 3:
                    self.assertIn(remote.expression, requirements)

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
