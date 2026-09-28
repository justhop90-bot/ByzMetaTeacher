import unittest

from Compiler.semantic.duc import analyze_duc
from Compiler.ast import Expression, SourceLocation
from Compiler.semantic.rule_execution import (
    EffectiveRule,
    RuleAction,
    RulePassBehavior,
)


def _rule(order, actions):
    location = SourceLocation(order, 1, "target-consumer-red.per")
    return EffectiveRule(
        rule_order=order,
        source_location=location,
        source_slice_ordinal=0,
        instance_id=f"target-consumer-red:{order}",
        facts=(Expression("(true)", "true", (), location),),
        actions=tuple(
            RuleAction(
                expression=Expression(
                    f"({head} {' '.join(args)})".rstrip(),
                    head,
                    tuple(args),
                    location,
                ),
                within_rule_order=index,
            )
            for index, (head, args) in enumerate(actions)
        ),
        pass_behavior=RulePassBehavior.RECURRENT,
        disable_self_action_index=None,
    )


class DucTargetConsumerRedPhaseTests(unittest.TestCase):
    def test_option_zero_targets_local_search_results_without_selected_target(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-target-objects", ("0", "action-default", "-1", "-1")),
            )),
        ))

        self.assertFalse(any(
            item.code == "DUC-005"
            and "up-target-objects" in item.message
            for item in report.diagnostics
        ))


if __name__ == "__main__":
    unittest.main()
