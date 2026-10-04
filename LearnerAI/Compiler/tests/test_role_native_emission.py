import unittest

from LearnerAI.Compiler.compiler import compile_semantic_demands
from LearnerAI.Compiler.ir.civ_profile import ByzantineProfile, resolve_effective_civ
from LearnerAI.Compiler.ir.role_separation import default_byzantine_role_separation_plan
from LearnerAI.Compiler.ir.strategy import build_byzantine_strategy


class ByzantineRoleNativeEmissionTests(unittest.TestCase):
    def setUp(self):
        effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        profile = build_byzantine_strategy(effective)
        self.plan = profile.role_separation_plan

    def test_role_plan_emits_deterministically(self):
        first = compile_semantic_demands((), role_plan=self.plan)
        second = compile_semantic_demands((), role_plan=self.plan)
        self.assertEqual(first, second)
        self.assertIn("(defconst byzantine-army-role-id-screen", first)
        self.assertIn("(defconst byzantine-army-role-id-main", first)
        self.assertIn("(defconst byzantine-army-role-id-siege", first)
        self.assertIn("(defconst byzantine-army-role-id-raid", first)
        self.assertIn("(defconst byzantine-army-role-id-reserve", first)
        self.assertIn("(defconst byzantine-army-role-screen-size", first)
        self.assertIn("(defconst byzantine-army-role-main-size", first)
        self.assertIn("(up-get-group-size", first)
        self.assertIn("; Native role rule: role-forming-screen", first)
        self.assertIn("(defconst byzantine-army-role-recovery-request", first)
        self.assertIn("(up-get-group-size", first)

    def test_role_emission_contains_no_attack_or_move_action(self):
        output = compile_semantic_demands((), role_plan=self.plan)
        role_block = output[output.index("; Native Byzantine role-separation plan"):]
        forbidden = (
            "(attack-now)",
            "action-attack-move",
            "(up-target-objects",
            "(up-target-point",
            "(action-move",
            "(stop)",
        )
        self.assertTrue(all(token not in role_block for token in forbidden))

    def test_role_plan_is_available_on_byzantine_stock_strategy_only(self):
        effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        profile = build_byzantine_strategy(effective)
        self.assertIsNotNone(profile.role_separation_plan)


if __name__ == "__main__":
    unittest.main()
