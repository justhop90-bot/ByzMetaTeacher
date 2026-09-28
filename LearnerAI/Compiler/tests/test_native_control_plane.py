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
    RuntimeBinder,
    StrategicNumberInventory,
    StrategicNumberRequest,
    TimerRequest,
)


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
        true = Expression("(true)", "true", ())
        plan = NativeControlPlan(
            states=(
                NativeControlState("strategy-goal", goal_request),
                NativeControlState("resource-control", sn_request),
                NativeControlState("cooldown", timer_request),
            ),
            rules=(
                NativeControlRule(
                    "initialize",
                    facts=(true,),
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
            native_control_plan=plan,
        )

        self.assertIn("(defconst strategy-goal 42)", output)
        self.assertIn("(defconst cooldown 1)", output)
        self.assertIn("(defrule", output)
        self.assertIn("(set-strategic-number resource-control 50)", output)
        self.assertIn("(up-timer-status cooldown == timer-running)", output)

    def test_control_plane_requires_declared_symbolic_storage(self):
        from Compiler.primitives.registry import default_de_registry
        from Compiler.semantic.native_control import validate_native_control_plan

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
        with self.assertRaisesRegex(ValueError, "undeclared Goal state"):
            validate_native_control_plan(plan, default_de_registry())


if __name__ == "__main__":
    unittest.main()
