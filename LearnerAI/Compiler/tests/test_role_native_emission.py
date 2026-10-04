import unittest
from pathlib import Path

from LearnerAI.Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_strategy,
    compile_strategy_profile,
    resolve_effective_civ,
)
from LearnerAI.Compiler.compiler import compile_semantic_demands


def _role_block(artifact: str) -> str:
    start_marker = "; Native Byzantine role-separation plan"
    end_marker = "; Native DUC execution plan"
    start = artifact.index(start_marker)
    end = artifact.index(end_marker, start)
    return artifact[start:end]


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

        role_block = _role_block(first)

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
        role_block = _role_block(output)
        for forbidden in (
            "(attack-now)",
            "action-attack-move",
            "(up-target-objects",
            "(up-target-point",
            "(action-move",
            "(stop)",
        ):
            self.assertNotIn(forbidden, role_block)

    def test_checked_in_role_block_matches_canonical_emission(self):
        repo_root = Path(__file__).resolve().parents[3]
        checked_in = (repo_root / "Byzantine.per").read_text(encoding="utf-8")
        canonical = compile_strategy_profile(self.profile, self.effective)
        self.assertEqual(
            _role_block(checked_in),
            _role_block(canonical),
            "checked-in Byzantine.per role block has diverged from canonical compiler output",
        )


if __name__ == "__main__":
    unittest.main()
