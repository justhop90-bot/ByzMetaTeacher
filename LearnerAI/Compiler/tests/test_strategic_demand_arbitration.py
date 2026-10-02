import unittest
from dataclasses import replace

from LearnerAI.Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_stock_strategy,
    lower_strategy_profile,
)
from LearnerAI.Compiler.ir.civ_profile import resolve_effective_civ
from LearnerAI.Compiler.ir.strategy import PrimaryStrategicIntent


class StrategicDemandArbitrationTests(unittest.TestCase):
    def setUp(self):
        effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        self.profile = build_byzantine_stock_strategy(effective)

    def test_primary_intent_plan_has_explicit_precedence(self):
        plan = self.profile.strategic_arbitration
        self.assertIsNotNone(plan)
        assert plan is not None

        ordered = tuple(
            candidate.intent
            for candidate in sorted(
                plan.candidates,
                key=lambda item: (-item.priority, item.intent.value),
            )
        )
        self.assertEqual(
            ordered,
            (
                PrimaryStrategicIntent.WATER,
                PrimaryStrategicIntent.CASTLE,
                PrimaryStrategicIntent.TWO_TC,
            ),
        )

    def test_primary_intent_uses_one_persistent_goal_state(self):
        compilation = lower_strategy_profile(
            self.profile,
            resolve_effective_civ(ByzantineProfile.for_update_185872()),
        )
        control = compilation.control_plan
        self.assertIsNotNone(control)
        assert control is not None

        state_names = {state.identifier for state in control.states}
        self.assertIn("strategic-primary-intent", state_names)

        rules = tuple(
            rule.identity
            for rule in control.rules
            if rule.identity.startswith("strategic-primary-intent-")
        )
        self.assertTrue(rules)

    def test_major_demands_are_not_initialized_active(self):
        effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        output = __import__(
            "LearnerAI.Compiler.clients.basilisk",
            fromlist=["compile_strategy_profile"],
        ).compile_strategy_profile(self.profile, effective)

        init_start = output.index("; Demand initialization")
        init_block = output[init_start: output.index("; Invalidation:", init_start)]

        self.assertIn(
            "(set-goal demand-castle-commitment",
            init_block,
        )
        castle_line = next(
            line
            for line in init_block.splitlines()
            if "(set-goal demand-castle-commitment" in line
        )
        self.assertNotEqual(castle_line.split()[-1].rstrip(")"), "1")

        tc_line = next(
            line
            for line in init_block.splitlines()
            if "(set-goal demand-castle-second-town-center" in line
        )
        self.assertNotEqual(tc_line.split()[-1].rstrip(")"), "1")

    def test_primary_intent_gates_castle_and_two_tc(self):
        castle = self.profile.demand("castle-commitment")
        tc = self.profile.demand("castle-second-town-center")

        self.assertEqual(
            castle.required_primary_intent,
            PrimaryStrategicIntent.CASTLE,
        )
        self.assertEqual(
            tc.required_primary_intent,
            PrimaryStrategicIntent.TWO_TC,
        )

        water_demands = {
            demand.identity
            for demand in self.profile.demands
            if demand.identity.startswith("water-")
        }
        for identity in water_demands:
            self.assertEqual(
                self.profile.demand(identity).required_primary_intent,
                PrimaryStrategicIntent.WATER,
            )

    def test_castle_and_two_tc_are_suppressed_during_enemy_pressure(self):
        effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        compilation = lower_strategy_profile(self.profile, effective)

        castle = next(d for d in compilation.demands if d.name == "castle-commitment")
        tc = next(d for d in compilation.demands if d.name == "castle-second-town-center")

        castle_requirements = tuple(item.expression.source for item in castle.requirements)
        tc_requirements = tuple(item.expression.source for item in tc.requirements)

        self.assertTrue(any(item.startswith("(not (or") for item in castle_requirements))
        self.assertTrue(any(item.startswith("(not (or") for item in tc_requirements))

    def test_primary_intent_is_lowered_as_native_control_not_semantic_requirement(self):
        effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        compilation = lower_strategy_profile(self.profile, effective)

        castle = next(d for d in compilation.demands if d.name == "castle-commitment")
        requirements = tuple(item.expression.source for item in castle.requirements)

        self.assertFalse(
            any("strategic-primary-intent" in item for item in requirements)
        )
        output = __import__(
            "LearnerAI.Compiler.clients.basilisk",
            fromlist=["compile_strategy_profile"],
        ).compile_strategy_profile(self.profile, effective)
        self.assertIn(
            "(goal strategic-primary-intent 2)",
            output,
        )
        self.assertIn(
            "(set-goal demand-castle-commitment 1)",
            output,
        )

    def test_counter_demands_start_released_and_follow_selected_package(self):
        effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        output = __import__(
            "LearnerAI.Compiler.clients.basilisk",
            fromlist=["compile_strategy_profile"],
        ).compile_strategy_profile(self.profile, effective)

        init_start = output.index("; Demand initialization")
        init_block = output[init_start: output.index("; Invalidation:", init_start)]
        spear_line = next(
            line
            for line in init_block.splitlines()
            if "(set-goal demand-counter-mounted-spears" in line
        )
        self.assertNotEqual(spear_line.split()[-1].rstrip(")"), "1")
        self.assertIn(
            "(goal counter-package-mounted_pressure_feudal 1)",
            output,
        )
        self.assertIn(
            "(set-goal demand-counter-mounted-spears 1)",
            output,
        )

    def test_recoverable_primary_demand_carries_world_loss_policy(self):
        binding = self.profile.demand("castle-commitment")
        self.assertTrue(binding.recovery_on_world_loss)
        self.assertTrue(binding.recovery.reopen_on_recovery)


if __name__ == "__main__":
    unittest.main()
