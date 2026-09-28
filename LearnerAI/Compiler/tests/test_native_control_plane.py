import unittest

from Compiler.ast import Expression, SourceLocation
from Compiler.compiler import compile_source
from Compiler.ir import (
    GoalRole,
    GoalSlotRequest,
    SemanticId,
    StorageRequestId,
)
from Compiler.ir.native_control import NativeControlPlan, NativeControlRule, NativeControlState
from Compiler.runtime_binding import (
    BindingContext,
    StrategicNumberInventory,
    StrategicNumberRequest,
    TimerRequest,
)
from Compiler.semantic.native_control import validate_native_control_plan
from Compiler.semantic.pass_scheduler import PassScheduler
from Compiler.semantic.rule_execution import EffectiveRule, RuleAction, RulePassBehavior


class NativePersistentControlPlaneTests(unittest.TestCase):
    def test_native_control_plan_lowers_goal_s_name_and_timer_storage(self):
        owner = SemanticId("control.fixture", "state")
        goal_request = GoalSlotRequest(
            StorageRequestId(owner, "strategy-goal"),
            role=GoalRole.PERSISTENT_STATE,
        )
        sn_request = StrategicNumberRequest(
            StorageRequestId(owner, "resource-control"),
            why_not_goal="This state directly controls a native Strategic Number.",
            stability_key="control.fixture.resource-control",
        )
        timer_request = TimerRequest(
            StorageRequestId(owner, "cooldown"),
            initialization_policy="DISABLE_BEFORE_FIRST_USE",
            stability_key="control.fixture.cooldown",
        )
        plan = NativeControlPlan(
            states=(
                NativeControlState("strategy-goal", goal_request),
                NativeControlState("resource-control", sn_request),
                NativeControlState("cooldown", timer_request),
            ),
            rules=(
                NativeControlRule(
                    "initialize",
                    facts=(
                        Expression(
                            "(goal strategy-goal -1)",
                            "goal",
                            ("strategy-goal", "-1"),
                        ),
                    ),
                    actions=(
                        Expression("(set-goal strategy-goal 1)", "set-goal", ("strategy-goal", "1")),
                        Expression("(set-strategic-number resource-control 50)", "set-strategic-number", ("resource-control", "50")),
                        Expression("(enable-timer cooldown 30)", "enable-timer", ("cooldown", "30")),
                        Expression("(disable-self)", "disable-self", ()),
                    ),
                ),
                NativeControlRule(
                    "consume",
                    facts=(
                        Expression("(goal strategy-goal 1)", "goal", ("strategy-goal", "1")),
                        Expression("(strategic-number resource-control >= 50)", "strategic-number", ("resource-control", ">=", "50")),
                        Expression("(up-timer-status cooldown == timer-running)", "up-timer-status", ("cooldown", "==", "timer-running")),
                    ),
                    actions=(
                        Expression("(set-goal strategy-goal 2)", "set-goal", ("strategy-goal", "2")),
                        Expression("(disable-timer cooldown)", "disable-timer", ("cooldown",)),
                    ),
                ),
            ),
        )

        sn_inventory = StrategicNumberInventory(
            inventory_sha="control-plane-test",
            documented_ids=frozenset(),
            candidate_ids=frozenset({510, 509}),
        )
        output = compile_source(
            """
            demand bootstrap {
                require (can-build house)
                action (build house)
                witness (building-type-count house >= 1)
                release (building-type-count house >= 1)
            }
            """,
            binding_context=BindingContext(
                strategic_number_inventory=sn_inventory,
            ),
            control_plan=plan,
        )

        self.assertIn("(defconst strategy-goal 42)", output)
        self.assertIn("(defconst cooldown 1)", output)
        self.assertIn("(defrule", output)
        self.assertIn("(set-strategic-number resource-control 50)", output)
        self.assertIn("(up-timer-status cooldown == timer-running)", output)



    def test_all_control_plane_commands_can_cross_the_control_lowering_gate(self):
        owner = SemanticId("control.fixture", "all-commands")
        states = (
            NativeControlState(
                "g",
                GoalSlotRequest(
                    StorageRequestId(owner, "g"),
                    role=GoalRole.PERSISTENT_STATE,
                ),
            ),
            NativeControlState(
                "s",
                StrategicNumberRequest(
                    StorageRequestId(owner, "s"),
                    why_not_goal="This state directly controls native Strategic Number behavior.",
                    stability_key="control.fixture.s",
                ),
            ),
            NativeControlState(
                "timer",
                TimerRequest(
                    StorageRequestId(owner, "timer"),
                    initialization_policy="DISABLE_BEFORE_FIRST_USE",
                    stability_key="control.fixture.timer",
                ),
            ),
        )
        location = SourceLocation(1, 1, "<control-plane>")
        facts = (
            Expression("(goal g -1)", "goal", ("g", "-1"), location),
            Expression("(up-compare-goal g c:>= -1)", "up-compare-goal", ("g", "c:>=", "-1"), location),
            Expression("(strategic-number s c:== 0)", "strategic-number", ("s", "c:==", "0"), location),
            Expression("(up-compare-sn s c:== 0)", "up-compare-sn", ("s", "c:==", "0"), location),
            Expression("(timer-triggered timer)", "timer-triggered", ("timer",), location),
            Expression("(up-timer-status timer c:== timer-disabled)", "up-timer-status", ("timer", "c:==", "timer-disabled"), location),
        )
        actions = (
            Expression("(set-goal g 1)", "set-goal", ("g", "1"), location),
            Expression("(up-modify-goal g c:+ 1)", "up-modify-goal", ("g", "c:+", "1"), location),
            Expression("(set-strategic-number s 1)", "set-strategic-number", ("s", "1"), location),
            Expression("(up-modify-sn s c:+ 1)", "up-modify-sn", ("s", "c:+", "1"), location),
            Expression("(enable-timer timer 5)", "enable-timer", ("timer", "5"), location),
            Expression("(disable-timer timer)", "disable-timer", ("timer",), location),
            Expression("(up-set-timer c: timer c: 5)", "up-set-timer", ("c:", "timer", "c:", "5"), location),
            Expression("(disable-self)", "disable-self", (), location),
            Expression("(up-jump-rule 0)", "up-jump-rule", ("0",), location),
        )
        from Compiler.primitives.registry import default_de_registry

        report = validate_native_control_plan(
            NativeControlPlan(
                states=states,
                rules=(NativeControlRule("all", facts=facts, actions=actions, location=location),),
            ),
            default_de_registry(),
        )
        self.assertEqual(
            set(report.control_commands),
            {
                "set-goal",
                "goal",
                "up-compare-goal",
                "up-modify-goal",
                "set-strategic-number",
                "strategic-number",
                "up-compare-sn",
                "up-modify-sn",
                "enable-timer",
                "disable-timer",
                "timer-triggered",
                "up-set-timer",
                "up-timer-status",
                "disable-self",
                "up-jump-rule",
            },
        )

    def test_goal_mutation_and_comparison_share_recurrent_scheduler_state(self):
        location = SourceLocation(1, 1, "<test>")
        rules = (
            EffectiveRule(
                rule_order=1,
                source_location=location,
                source_slice_ordinal=0,
                instance_id="r1",
                facts=(Expression("(true)", "true", (), location),),
                actions=(
                    RuleAction(
                        Expression("(set-goal g 5)", "set-goal", ("g", "5"), location),
                        0,
                    ),
                    RuleAction(
                        Expression(
                            "(up-modify-goal g c:+ 2)",
                            "up-modify-goal",
                            ("g", "c:+", "2"),
                            location,
                        ),
                        1,
                    ),
                ),
                pass_behavior=RulePassBehavior.ONE_SHOT,
                disable_self_action_index=None,
            ),
            EffectiveRule(
                rule_order=2,
                source_location=location,
                source_slice_ordinal=0,
                instance_id="r2",
                facts=(
                    Expression(
                        "(up-compare-goal g c:== 7)",
                        "up-compare-goal",
                        ("g", "c:==", "7"),
                        location,
                    ),
                ),
                actions=(
                    RuleAction(
                        Expression("(set-goal result 1)", "set-goal", ("result", "1"), location),
                        0,
                    ),
                ),
                pass_behavior=RulePassBehavior.ONE_SHOT,
                disable_self_action_index=None,
            ),
        )

        scheduler = PassScheduler(rules, goal_values={"g": -1})
        scheduler.run_pass()

        self.assertEqual(scheduler.goals["g"], 7)
        self.assertEqual(scheduler.goals["result"], 1)

    def test_control_plane_requires_declared_symbolic_storage(self):
        from Compiler.primitives.registry import default_de_registry

        plan = NativeControlPlan(
            states=(),
            rules=(
                NativeControlRule(
                    "bad",
                    facts=(
                        Expression("(goal missing-goal 1)", "goal", ("missing-goal", "1")),
                    ),
                    actions=(),
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "undeclared GOAL state"):
            validate_native_control_plan(plan, default_de_registry())


if __name__ == "__main__":
    unittest.main()
