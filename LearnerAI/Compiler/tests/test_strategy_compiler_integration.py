import tempfile
import unittest
from pathlib import Path

from LearnerAI.Compiler.clients.basilisk import compile_strategy_profile
from LearnerAI.Compiler.ir.civ_profile import resolve_effective_civ
from LearnerAI.Compiler.ir.game_data import Resource
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
