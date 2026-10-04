import unittest

from LearnerAI.Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_strategy,
    compile_strategy_profile,
    resolve_effective_civ,
)
from LearnerAI.Compiler.compiler import compile_semantic_demands


class ByzantineRoleNativeEmissionTests(unittest.TestCase):
    def setUp(self):
        self.effective = resolve_effective_civ(
            ByzantineProfile.for_update_185872()
        )
        self.profile = build_byzantine_strategy(
            self.effective,
            include_water_continuity=True,
        )
        self.plan = self.profile.role_separation_plan

    def test_role_plan_emits_deterministically(self):
        first = compile_semantic_demands((), role_plan=self.plan)
        second = compile_semantic_demands((), role_plan=self.plan)
        self.assertEqual(first, second)
        self.assertIn(
            "(defconst byzantine-army-role-id-screen",
            first,
        )
        self.assertIn(
            "; Native role rule: role-forming-screen",
            first,
        )
        self.assertIn(
            "(defconst byzantine-army-role-recovery-request",
            first,
        )
        self.assertIn("(up-get-group-size", first)

    def test_canonical_byzantine_emission_preserves_four_objective_actuators(self):
        first = compile_strategy_profile(self.profile, self.effective)
        second = compile_strategy_profile(self.profile, self.effective)
        self.assertEqual(first, second)

        role_start = first.index("; Native Byzantine role-separation plan")
        role_end = first.find("; Native DUC execution plan", role_start)
        role_block = first[role_start:] if role_end < 0 else first[role_start:role_end]

        for forbidden in (
            "attack-now",
            "attack-groups",
            "action-attack-move",
            "up-target-objects",
            "up-target-point",
            "action-move",
            "(stop",
        ):
            self.assertNotIn(forbidden, role_block)

        self.assertEqual(
            first.count("(up-target-objects 1 action-attack-move -1 -1)"),
            4,
        )

    def test_role_floors_are_disjoint_and_fortified_siege_uses_larger_floor(self):
        plan = self.plan
        self.assertEqual(
            tuple(role.minimum for role in plan.roles),
            (2, 4, 1, 2, 0),
        )
        witness_text = "\n".join(
            expression.source
            for witness in plan.witnesses
            for expression in witness.facts
        )
        self.assertIn(
            "byzantine-siege-scale-fortified",
            witness_text,
        )

    def test_role_emission_contains_no_attack_or_move_action(self):
        output = compile_semantic_demands((), role_plan=self.plan)
        role_block = output[output.index("; Native Byzantine role-separation plan"):]
        for forbidden in (
            "(attack-now)",
            "action-attack-move",
            "(up-target-objects",
            "(up-target-point",
            "(action-move",
            "(stop)",
        ):
            self.assertNotIn(forbidden, role_block)


if __name__ == "__main__":
    unittest.main()
