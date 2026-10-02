"""Phase 7 Pack A (ROADMAP): strategy-owned goal-state assertions.

Slice: a StrategicDemandSpec declares goal-backed FSM states; lowering
builds a NativeControlPlan (states + guard rules) through the existing
persistent-control-plane channel. No new DSL, no scheduler, no demand
changes: set-goal never becomes a demand action.

Hard invariants pinned here:
- assertions are owned by their declaring demand; shared state names
  across demands conflict unless the owner matches (deduped then);
- guards stay native Facts; the control-plane gate rejects unknown
  commands, undeclared states, and bad arities (no test bypasses it);
- same-pass write visibility stays engine-ordered (no firing proof);
- no assertions and no posture transitions means no control plan (existing behavior preserved).
"""
import unittest
from dataclasses import replace

from Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_castle_strategy,
    compile_strategy_profile,
)
from Compiler.ir.civ_profile import resolve_effective_civ
from Compiler.ir.strategy import (
    GoalStateAssertion,
    StrategyPosture,
    lower_strategy_profile,
)


def _profile():
    effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
    profile = build_byzantine_castle_strategy(effective)
    # Goal-FSM tests isolate the existing control-plane seam. Native SN mode
    # synthesis has its own dedicated tests and acceptance fixture.
    return effective, replace(profile, strategic_number_modes=(), attack_plan=None, duc_plan=None)


def _with_assertions(profile, *assertions_by_spec):
    demands = []
    for spec in profile.demands:
        extra = tuple(
            assertion
            for demand_id, assertion in assertions_by_spec
            if demand_id == spec.identity
        )
        demands.append(
            replace(spec, goal_assertions=spec.goal_assertions + extra)
        )
    from dataclasses import replace as dc_replace

    return dc_replace(profile, demands=tuple(demands))


class StrategyGoalStateTests(unittest.TestCase):
    def test_lowering_builds_state_and_rule_deterministically(self):
        effective, profile = _profile()
        profile = replace(profile, transitions=())
        spec = profile.demands[0]
        profile = _with_assertions(
            profile,
            (
                spec.identity,
                GoalStateAssertion(
                    spec.identity, "war-posture", "(goal war-posture 0)", 1
                ),
            ),
        )
        first = lower_strategy_profile(profile, effective)
        second = lower_strategy_profile(profile, effective)
        self.assertIsNotNone(first.control_plan)
        self.assertEqual(
            [state.identifier for state in first.control_plan.states],
            ["war-posture"],
        )
        self.assertEqual(
            [rule.identity for rule in first.control_plan.rules],
            ["war-posture-assert-000"],
        )
        self.assertEqual(first.control_plan, second.control_plan)

    def test_posture_transitions_lower_to_persistent_goal_fsm(self):
        effective, profile = _profile()

        compilation = lower_strategy_profile(profile, effective)

        self.assertIsNotNone(compilation.control_plan)
        control_plan = compilation.control_plan
        assert control_plan is not None
        self.assertEqual(
            control_plan.state("strategy-posture").identifier,
            "strategy-posture",
        )
        self.assertEqual(
            len(control_plan.rules),
            len(profile.transitions) + 1,
        )
        self.assertEqual(
            tuple(rule.identity for rule in control_plan.rules),
            (
                "strategy-posture-initialize-000",
                "strategy-posture-transition-001",
                "strategy-posture-transition-002",
                "strategy-posture-transition-003",
                "strategy-posture-transition-004",
                "strategy-posture-transition-005",
            ),
        )
        self.assertEqual(
            tuple(action.source for action in control_plan.rules[0].actions),
            ("(set-goal strategy-posture 0)", "(disable-self)"),
        )
        self.assertIn("(goal strategy-posture 1)", control_plan.rules[1].facts[0].source)
        self.assertIn("(goal strategy-posture 3)", control_plan.rules[1].facts[0].source)
        self.assertIn("(set-goal strategy-posture 4)", control_plan.rules[1].actions[0].source)
        self.assertIn("(goal strategy-posture 3)", control_plan.rules[2].facts[0].source)
        self.assertEqual(
            control_plan.rules[2].actions[0].source,
            "(set-goal strategy-posture 1)",
        )
        self.assertIn("(goal strategy-posture 0)", control_plan.rules[4].facts[0].source)
        self.assertIn("(current-age == dark-age)", control_plan.rules[4].facts[0].source)
        self.assertEqual(
            control_plan.rules[4].actions[0].source,
            "(set-goal strategy-posture 3)",
        )

    def test_no_assertions_means_no_control_plan(self):
        effective, profile = _profile()
        profile = replace(profile, transitions=())
        compilation = lower_strategy_profile(profile, effective)
        self.assertIsNone(compilation.control_plan)

    def test_posture_fsm_emits_through_existing_control_plane(self):
        effective, profile = _profile()

        first = compile_strategy_profile(profile, effective)
        second = compile_strategy_profile(profile, effective)

        self.assertRegex(first, r"\(defconst strategy-posture \d+\)")
        self.assertIn("(set-goal strategy-posture 3)", first)
        self.assertIn("; Native control rule: strategy-posture-transition-001", first)
        self.assertEqual(first, second)

    def test_posture_transition_equal_priority_conflict_is_rejected(self):
        effective, profile = _profile()
        profile = replace(
            profile,
            transitions=(
                profile.transitions[0],
                replace(
                    profile.transitions[1],
                    label="conflicting-opening",
                    to_posture=StrategyPosture.RUSH,
                    priority=profile.transitions[0].priority,
                ),
            ),
        )

        with self.assertRaisesRegex(ValueError, "equal-priority initial posture"):
            lower_strategy_profile(profile, effective)

    def test_end_to_end_emits_defconst_guard_and_set(self):
        effective, profile = _profile()
        spec = profile.demands[0]
        profile = _with_assertions(
            profile,
            (
                spec.identity,
                GoalStateAssertion(
                    spec.identity, "war-posture", "(goal war-posture 0)", 1
                ),
            ),
        )
        first = compile_strategy_profile(profile, effective)
        self.assertRegex(first, r"\(defconst war-posture \d+\)")
        self.assertIn("(goal war-posture 0)", first)
        self.assertIn("(set-goal war-posture 1)", first)
        self.assertIn("; Native control rule: war-posture-assert-000", first)
        self.assertEqual(
            first, compile_strategy_profile(profile, effective)
        )

    def test_mismatched_owner_rejected(self):
        _, profile = _profile()
        spec = profile.demands[0]
        profile = _with_assertions(
            profile,
            (
                spec.identity,
                GoalStateAssertion(
                    "someone-else", "war-posture", "(goal war-posture 0)", 1
                ),
            ),
        )
        effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        with self.assertRaisesRegex(ValueError, "not by strategic demand"):
            lower_strategy_profile(profile, effective)

    def test_shared_state_across_owners_rejected(self):
        _, profile = _profile()
        first, second = profile.demands[0], profile.demands[1]
        profile = _with_assertions(
            profile,
            (
                first.identity,
                GoalStateAssertion(
                    first.identity, "war-posture", "(goal war-posture 0)", 1
                ),
            ),
            (
                second.identity,
                GoalStateAssertion(
                    second.identity, "war-posture", "(goal war-posture 1)", 2
                ),
            ),
        )
        effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        with self.assertRaisesRegex(ValueError, "multiple demand owners"):
            lower_strategy_profile(profile, effective)

    def test_shared_state_same_owner_dedupes(self):
        effective, profile = _profile()
        profile = replace(profile, transitions=())
        spec = profile.demands[0]
        profile = _with_assertions(
            profile,
            (
                spec.identity,
                GoalStateAssertion(
                    spec.identity, "war-posture", "(goal war-posture 0)", 1
                ),
            ),
            (
                spec.identity,
                GoalStateAssertion(
                    spec.identity, "war-posture", "(goal war-posture 1)", 2
                ),
            ),
        )
        compilation = lower_strategy_profile(profile, effective)
        self.assertEqual(len(compilation.control_plan.states), 1)
        self.assertEqual(len(compilation.control_plan.rules), 2)

    def test_unknown_guard_command_rejected_at_compile(self):
        _, profile = _profile()
        spec = profile.demands[0]
        profile = _with_assertions(
            profile,
            (
                spec.identity,
                GoalStateAssertion(
                    spec.identity, "war-posture", "(frobnicate war-posture)", 1
                ),
            ),
        )
        effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        with self.assertRaises(ValueError):
            compile_strategy_profile(profile, effective)

    def test_assertion_shape_validated(self):
        with self.assertRaisesRegex(ValueError, "valid .per identifier"):
            GoalStateAssertion("demand", "Has Space", "(goal x 0)", 1)
        with self.assertRaisesRegex(ValueError, "guard fact must not be empty"):
            GoalStateAssertion("demand", "war-posture", "   ", 1)
        with self.assertRaisesRegex(ValueError, "must be an integer"):
            GoalStateAssertion("demand", "war-posture", "(goal x 0)", True)
        with self.assertRaisesRegex(ValueError, "demand identity must not be empty"):
            GoalStateAssertion("  ", "war-posture", "(goal x 0)", 1)


if __name__ == "__main__":
    unittest.main()
