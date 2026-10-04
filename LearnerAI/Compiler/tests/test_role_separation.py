import unittest

from LearnerAI.Compiler.ir.civ_profile import ByzantineProfile, resolve_effective_civ
from LearnerAI.Compiler.ir.strategy import build_byzantine_strategy
from LearnerAI.Compiler.ir.role_separation import (
    RoleControllerState,
    RoleKind,
)


class RoleSeparationTests(unittest.TestCase):
    def setUp(self):
        effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        self.profile = build_byzantine_strategy(effective)

    def test_byzantine_profile_exposes_role_plan(self):
        plan = self.profile.role_separation_plan
        self.assertIsNotNone(plan)
        self.assertEqual(
            tuple(role.role for role in plan.roles),
            (
                RoleKind.SCREEN,
                RoleKind.MAIN,
                RoleKind.SIEGE,
                RoleKind.RAID,
                RoleKind.RESERVE,
            ),
        )
        self.assertEqual(
            tuple(role.group_id for role in plan.roles),
            (5, 6, 7, 8, 9),
        )

    def test_role_state_contract(self):
        plan = self.profile.role_separation_plan
        self.assertEqual(plan.state_values[RoleControllerState.IDLE], 0)
        self.assertEqual(plan.state_values[RoleControllerState.FORMING], 1)
        self.assertEqual(plan.state_values[RoleControllerState.COMMITTED], 2)
        self.assertEqual(plan.state_values[RoleControllerState.RAID_SPLIT], 3)
        self.assertEqual(plan.state_values[RoleControllerState.RECOVERING], 4)
        self.assertEqual(len(plan.storage_requests), 10)

    def test_role_rules_never_issue_attack_or_move(self):
        plan = self.profile.role_separation_plan
        forbidden = {
            "attack-now",
            "attack-groups",
            "action-attack-move",
            "up-target-objects",
            "up-target-point",
            "action-move",
            "stop",
        }
        commands = {
            expression.head
            for rule in plan.rules
            for expression in (*rule.facts, *rule.actions)
        }
        self.assertTrue(commands)
        self.assertTrue(forbidden.isdisjoint(commands))
        self.assertNotIn(
            "set-goal",
            {
                expression.head
                for rule in plan.rules
                for expression in rule.actions
                if expression.args
                and "byzantine-army-attack-ready" in str(expression.args[0])
            },
        )

    def test_native_role_plan_validates(self):
        from LearnerAI.Compiler.primitives import default_de_registry
        from LearnerAI.Compiler.ir.role_separation import (
            validate_native_role_separation_plan,
        )

        validate_native_role_separation_plan(
            self.profile.role_separation_plan,
            default_de_registry(),
        )

    def test_fortified_siege_contract_blocks_raid(self):
        plan = self.profile.role_separation_plan
        self.assertIn(
            "role-raid-fortified-ineligible",
            tuple(witness.identity for witness in plan.witnesses),
        )
        self.assertIn(
            "role-fortified-siege",
            tuple(witness.identity for witness in plan.witnesses),
        )
        self.assertIn(
            "up-get-group-size",
            plan.commands(),
        )


if __name__ == "__main__":
    unittest.main()
