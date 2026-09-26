import tempfile
import unittest
from pathlib import Path

from LearnerAI.Compiler.compiler import compile_strategy_profile
from LearnerAI.Compiler.ir.civ_profile import ByzantineProfile, resolve_effective_civ
from LearnerAI.Compiler.ir.strategy import (
    build_byzantine_castle_strategy,
    lower_strategy_profile,
)


class StrategyCompilerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        self.profile = build_byzantine_castle_strategy(self.effective)

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
