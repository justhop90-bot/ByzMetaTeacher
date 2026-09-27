import unittest

from Compiler.ir.duc import DucListKind, DucTargetStatus
from Compiler.semantic.duc import analyze_duc
from Compiler.ast import Expression, SourceLocation
from Compiler.semantic.rule_execution import EffectiveRule, RuleAction, RulePassBehavior


def _rule(order, actions, *, pass_behavior=RulePassBehavior.RECURRENT):
    location = SourceLocation(order, 1, "fixture.per")
    return EffectiveRule(
        rule_order=order,
        source_location=location,
        source_slice_ordinal=0,
        instance_id=f"fixture:{order}",
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
        pass_behavior=pass_behavior,
        disable_self_action_index=None,
    )


class DucSemanticTests(unittest.TestCase):
    def test_search_target_provenance_survives_same_rule_chain(self):
        report = analyze_duc((
            _rule(1, (
                ("up-full-reset-search", ()),
                ("up-reset-filters", ()),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-get-search-state", ("100",)),
                ("up-set-target-object", ("search-remote", "c:", "0")),
                ("up-target-objects", ("0", "action-default", "-1", "-1")),
            )),
        ))

        self.assertEqual(
            report.final_state.remote_list.current_generation.list_kind,
            DucListKind.REMOTE,
        )
        self.assertEqual(
            report.final_state.remote_list.current_generation.generation,
            1,
        )
        self.assertEqual(report.final_state.target.validity, DucTargetStatus.VALID)
        self.assertEqual(report.targets[-1].source_list_generation, 1)
        self.assertEqual(report.searches[0].consumed_filter.generation, 0)


if __name__ == "__main__":
    unittest.main()
