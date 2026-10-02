import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from LearnerAI.Compiler.clients.basilisk import (
    compile_strategy_profile,
    compile_strategy_runtime_profile,
)
from LearnerAI.Compiler.ast import Expression
from LearnerAI.Compiler.ir.civ_profile import resolve_effective_civ
from LearnerAI.Compiler.ir.game_data import Resource
from LearnerAI.Compiler.ir.native_duc import NativeDucPlan, NativeDucRule
from LearnerAI.Compiler.ir.strategy import StrategyPosture
from LearnerAI.Compiler.ir.strategy_runtime import RuntimeObservationSnapshot
from LearnerAI.Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_castle_strategy,
    lower_strategy_profile,
)


class StrategyCompilerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        self.profile = build_byzantine_castle_strategy(self.effective)

    def test_protected_research_declares_explicit_escrow_resources(self):
        demand = self.profile.demand("feudal-transition")
        self.assertEqual(
            demand.execution.escrow_release_resources,
            (Resource.FOOD, Resource.GOLD),
        )

    def test_strategy_lowering_produces_targeted_escrow_release_plan(self):
        compilation = lower_strategy_profile(self.profile, self.effective)

        self.assertIsNotNone(compilation.escrow_plan)
        plan = compilation.escrow_plan
        assert plan is not None
        self.assertEqual(
            tuple(operation.resource for operation in plan.operations),
            ("food", "gold"),
        )
        self.assertTrue(
            all(
                operation.target_demand.local_name == "feudal-transition"
                for operation in plan.operations
            )
        )
        self.assertTrue(
            all(operation.command == "release-escrow" for operation in plan.operations)
        )

    def test_strategy_compiler_emits_protected_research_release_before_research(self):
        output = compile_strategy_profile(
            self.profile,
            self.effective,
        )
        action_start = output.index("; Action issuance: feudal-transition")
        action_block = output[action_start:]
        self.assertLess(
            action_block.index("(release-escrow food)"),
            action_block.index("(research feudal-age)"),
        )
        self.assertLess(
            action_block.index("(release-escrow gold)"),
            action_block.index("(research feudal-age)"),
        )

    def test_strategy_compilation_exposes_profile_and_override_duc_channels(self):
        profile_plan = NativeDucPlan(
            rules=(
                NativeDucRule(
                    identity="byzantine-duc-profile",
                    order=0,
                    facts=(Expression("(true)", "true", ()),),
                    actions=(
                        Expression(
                            "(up-full-reset-search)",
                            "up-full-reset-search",
                            (),
                        ),
                    ),
                ),
            )
        )
        override_plan = NativeDucPlan(
            rules=(
                NativeDucRule(
                    identity="byzantine-duc-override",
                    order=0,
                    facts=(Expression("(true)", "true", ()),),
                    actions=(
                        Expression(
                            "(up-full-reset-search)",
                            "up-full-reset-search",
                            (),
                        ),
                    ),
                ),
            )
        )
        profile = replace(self.profile, duc_plan=profile_plan)

        compilation = lower_strategy_profile(profile, self.effective)
        self.assertIs(compilation.duc_plan, profile_plan)

        default_output = compile_strategy_profile(profile, self.effective)
        self.assertIn("; Native DUC execution plan", default_output)
        self.assertIn("; Native DUC rule: byzantine-duc-profile", default_output)

        override_output = compile_strategy_profile(
            self.profile,
            self.effective,
            duc_plan=override_plan,
        )
        self.assertIn("; Native DUC rule: byzantine-duc-override", override_output)
        self.assertNotIn("; Native DUC rule: byzantine-duc-profile", override_output)

        runtime_output = compile_strategy_runtime_profile(
            profile,
            self.effective,
            RuntimeObservationSnapshot(previous_posture=StrategyPosture.CASTLE_POWER),
            duc_plan=override_plan,
        )
        self.assertIn("; Native DUC rule: byzantine-duc-override", runtime_output)

    def test_byzantine_strategy_lowers_default_duc_target_pipeline(self):
        compilation = lower_strategy_profile(self.profile, self.effective)

        self.assertIsNotNone(compilation.duc_plan)
        plan = compilation.duc_plan
        assert plan is not None
        self.assertEqual(
            tuple(rule.identity for rule in plan.rules),
            (
                "byzantine-castle-target-knight",
                "byzantine-castle-target-infantry",
            ),
        )
        self.assertEqual(
            tuple(item.source for item in plan.rules[0].facts),
            (
                "(current-age >= castle-age)",
                "(up-compare-sn 227 >= 75)",
                "(players-unit-type-count any-enemy knight >= 3)",
            ),
        )
        self.assertEqual(
            tuple(item.source for item in plan.rules[1].facts),
            (
                "(current-age >= castle-age)",
                "(up-compare-sn 227 >= 75)",
                "(players-unit-type-count any-enemy militia-line >= 5)",
            ),
        )
        self.assertEqual(
            tuple(item.head for item in plan.rules[0].actions[:3]),
            (
                "up-full-reset-search",
                "up-find-remote",
                "up-set-target-object",
            ),
        )
        self.assertEqual(
            tuple(item.head for item in plan.rules[1].actions[:3]),
            (
                "up-full-reset-search",
                "up-find-remote",
                "up-set-target-object",
            ),
        )
        self.assertTrue(
            all(
                any(
                    output.rule_identity == rule.identity
                    and output.command == "up-get-object-data"
                    for output in plan.output_requests
                )
                for rule in plan.rules
            )
        )

        output = compile_strategy_profile(self.profile, self.effective)
        self.assertIn("; Native DUC rule: byzantine-castle-target-knight", output)
        self.assertIn("(up-find-remote c: knight-line c: 1)", output)
        self.assertIn("(up-set-target-object search-remote c: 0)", output)
        self.assertIn("; Native DUC rule: byzantine-castle-target-infantry", output)
        self.assertIn("(up-find-remote c: militia-line c: 1)", output)

    def test_byzantine_strategy_lowers_default_attack_lifecycle(self):
        compilation = lower_strategy_profile(self.profile, self.effective)

        self.assertIsNotNone(compilation.attack_plan)
        plan = compilation.attack_plan
        assert plan is not None
        self.assertEqual(
            tuple(rule.identity for rule in plan.rules),
            (
                "byzantine-castle-attack-now-cataphract",
                "byzantine-castle-attack-now-knight",
            ),
        )
        self.assertEqual(
            tuple(item.source for item in plan.rules[0].facts),
            (
                "(current-age == castle-age)",
                "(up-compare-sn 227 >= 75)",
                "(unit-type-count cataphract >= 2)",
            ),
        )
        self.assertEqual(
            tuple(item.source for item in plan.rules[1].facts),
            (
                "(current-age == castle-age)",
                "(up-compare-sn 227 >= 75)",
                "(unit-type-count knight >= 3)",
            ),
        )
        self.assertEqual(plan.rules[0].actions[0].source, "(attack-now)")
        self.assertEqual(plan.rules[1].actions[0].source, "(attack-now)")

        first = compile_strategy_profile(self.profile, self.effective)
        second = compile_strategy_profile(self.profile, self.effective)
        self.assertEqual(first, second)
        self.assertIn("; Native attack lifecycle plan", first)
        self.assertIn("; Native attack rule: byzantine-castle-attack-now-cataphract", first)
        self.assertIn("; Native attack rule: byzantine-castle-attack-now-knight", first)
        self.assertIn("(attack-now)", first)

    def test_runtime_strategy_uses_the_same_default_attack_plan_channel(self):
        snapshot = RuntimeObservationSnapshot(
            previous_posture=StrategyPosture.CASTLE_POWER,
        )
        output = compile_strategy_runtime_profile(
            self.profile,
            self.effective,
            snapshot,
        )
        self.assertIn("; Native attack lifecycle plan", output)
        self.assertIn("; Native attack rule: byzantine-castle-attack-now-cataphract", output)
        self.assertIn("; Native attack rule: byzantine-castle-attack-now-knight", output)
        self.assertIn("(current-age == castle-age)", output)
        self.assertIn("(attack-now)", output)

    def test_strategy_profile_compiles_through_existing_semantic_pipeline(self):
        output = compile_strategy_profile(
            self.profile,
            self.effective,
        )

        self.assertIn("(build castle)", output)
        self.assertIn("(train spearman-line)", output)
        self.assertIn("demand-castle-commitment", output)

    def test_strategy_lowering_does_not_create_second_lifecycle(self):
        compilation = lower_strategy_profile(self.profile, self.effective)

        self.assertEqual(
            len([d for d in compilation.demands if d.name == "castle-commitment"]),
            1,
        )
        self.assertIsNotNone(
            compilation.bindings["castle-commitment"].opportunity_cost
        )


if __name__ == "__main__":
    unittest.main()
