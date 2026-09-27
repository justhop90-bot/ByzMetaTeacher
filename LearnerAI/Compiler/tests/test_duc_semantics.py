import unittest

from Compiler.ir.duc import DucListKind, DucTargetStatus
from Compiler.semantic.duc import analyze_duc
from Compiler.ast import Expression, SourceLocation
from Compiler.semantic.rule_execution import (
    EffectiveRule,
    RuleAction,
    RuleExecutionReport,
    RulePassBehavior,
    RuleReachabilityReport,
)


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

    def test_partial_search_reset_does_not_invalidate_remote_target(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-set-target-object", ("search-remote", "c:", "0")),
            )),
            _rule(2, (
                ("up-reset-search", ("1", "1", "0", "0")),
                ("up-target-objects", ("1", "action-default", "-1", "-1")),
            )),
        ))

        self.assertEqual(report.final_state.target.validity, DucTargetStatus.VALID)
        reset = report.resets[-1]
        self.assertEqual(reset.invalidates_lists, (DucListKind.LOCAL,))
        self.assertFalse(reset.invalidates_remote_index)


    def test_branch_join_marks_divergent_local_generation_and_target_unknown(self):
        rules = (
            _rule(1, (("up-jump-rule", ("1",)),)),
            _rule(2, (("up-find-local", ("c:", "villager", "c:", "1")),)),
            _rule(3, (("up-find-local", ("c:", "monk", "c:", "1")),)),
            _rule(4, (("up-set-target-object", ("search-local", "c:", "0")),)),
            _rule(5, (("up-target-objects", ("1", "action-default", "-1", "-1")),)),
        )
        execution = RuleExecutionReport(
            rules=rules,
            reachability=RuleReachabilityReport(
                reachable_rule_orders=(1, 2, 3, 4, 5),
                unreachable_rule_orders=(),
                incoming_rule_orders=(
                    (1, ()),
                    (2, (1,)),
                    (3, (1,)),
                    (4, (2, 3)),
                    (5, (4,)),
                ),
                outgoing_rule_orders=(
                    (1, (2, 3)),
                    (2, (4,)),
                    (3, (4,)),
                    (4, (5,)),
                    (5, ()),
                ),
            ),
        )

        report = analyze_duc(execution)

        merge = report.branch_merges[0]
        self.assertEqual(merge.rule_order, 4)
        self.assertEqual(merge.predecessor_rule_orders, (2, 3))
        self.assertIn("LOCAL_LIST", merge.merged_fields)
        join_state = next(
            state
            for rule_order, state in report.states
            if rule_order == 4
        )
        self.assertTrue(join_state.local_list.path_ambiguous)
        self.assertTrue(join_state.local_list.initialized)
        self.assertIsNone(join_state.local_list.current_generation)
        self.assertEqual(report.final_state.target.validity, DucTargetStatus.UNKNOWN)
        self.assertTrue(
            any(item.code == "DUC-007" and item.rule_order in {4, 5}
                for item in report.diagnostics)
        )

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
