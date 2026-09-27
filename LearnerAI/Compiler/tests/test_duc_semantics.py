import unittest

from Compiler.ir.duc import DucListKind, DucLoopWidening, DucTargetStatus
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



    def _branched_execution(self, rules):
        return RuleExecutionReport(
            rules=rules,
            reachability=RuleReachabilityReport(
                reachable_rule_orders=tuple(range(1, len(rules) + 1)),
                unreachable_rule_orders=(),
                incoming_rule_orders=(
                    (1, ()),
                    (2, (1,)),
                    (3, (1,)),
                    (4, (2, 3)),
                    *(
                        (order, (order - 1,))
                        for order in range(5, len(rules) + 1)
                    ),
                ),
                outgoing_rule_orders=(
                    (1, (2, 3)),
                    (2, (4,)),
                    (3, (4,)),
                    *(
                        (order, (order + 1,))
                        for order in range(4, len(rules))
                    ),
                    (len(rules), ()),
                ),
            ),
        )

    def test_branch_join_preserves_identical_remote_generation(self):
        rules = (
            _rule(1, (("up-jump-rule", ("1",)),)),
            _rule(2, (("up-find-remote", ("c:", "town-center", "c:", "1")),)),
            _rule(3, (("up-find-remote", ("c:", "town-center", "c:", "1")),)),
            _rule(4, (("up-set-target-object", ("search-remote", "c:", "0")),)),
            _rule(5, (("up-target-objects", ("1", "action-default", "-1", "-1")),)),
        )

        report = analyze_duc(self._branched_execution(rules))

        join_state = next(state for order, state in report.states if order == 4)
        self.assertFalse(join_state.remote_list.path_ambiguous)
        self.assertEqual(join_state.remote_list.current_generation.generation, 1)
        self.assertEqual(report.final_state.target.validity, DucTargetStatus.VALID)
        self.assertNotIn("REMOTE_LIST", report.branch_merges[0].merged_fields)

    def test_branch_join_marks_retained_filter_divergence(self):
        rules = (
            _rule(1, (("up-jump-rule", ("1",)),)),
            _rule(2, (
                ("up-filter-distance", ("c:", "0", "c:", "100")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
            )),
            _rule(3, (
                ("up-filter-range", ("0", "100", "0", "100")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
            )),
            _rule(4, (("up-find-remote", ("c:", "town-center", "c:", "1")),)),
        )

        report = analyze_duc(self._branched_execution(rules))

        merge = next(item for item in report.branch_merges if item.rule_order == 4)
        self.assertIn("FILTERS", merge.merged_fields)
        self.assertTrue(report.final_state.remote_list.path_ambiguous)
        self.assertTrue(report.searches[-1].consumed_filter.path_ambiguous)
        self.assertTrue(
            any(item.code == "DUC-012" and item.rule_order == 4
                for item in report.diagnostics)
        )

    def test_branch_join_merges_preexisting_target_to_unknown(self):
        rules = (
            _rule(1, (("up-jump-rule", ("1",)),)),
            _rule(2, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-set-target-object", ("search-local", "c:", "0")),
            )),
            _rule(3, (("up-find-local", ("c:", "villager", "c:", "1")),)),
            _rule(4, (("up-target-objects", ("1", "action-default", "-1", "-1")),)),
        )

        report = analyze_duc(self._branched_execution(rules))

        self.assertEqual(report.final_state.target.validity, DucTargetStatus.UNKNOWN)
        self.assertTrue(
            any(item.code == "DUC-007" and item.rule_order == 4
                for item in report.diagnostics)
        )

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

    def test_backward_jump_uses_finite_loop_widening(self):
        rules = (
            _rule(1, (("up-find-remote", ("c:", "town-center", "c:", "1")),)),
            _rule(2, (("up-find-remote", ("c:", "town-center", "c:", "1")),)),
            _rule(3, (("up-find-remote", ("c:", "town-center", "c:", "1")), ("up-jump-rule", ("-2",)))),
            _rule(4, (("up-set-target-object", ("search-remote", "c:", "0")),)),
        )
        execution = RuleExecutionReport(
            rules=rules,
            reachability=RuleReachabilityReport(
                reachable_rule_orders=(1, 2, 3, 4),
                unreachable_rule_orders=(),
                incoming_rule_orders=(
                    (1, ()),
                    (2, (1, 3)),
                    (3, (2,)),
                    (4, (3,)),
                ),
                outgoing_rule_orders=(
                    (1, (2,)),
                    (2, (3,)),
                    (3, (2, 4)),
                    (4, ()),
                ),
            ),
        )

        report = analyze_duc(execution)

        self.assertFalse(any(item.code == "DUC-013" for item in report.diagnostics))
        loop_state = next(state for order, state in report.states if order == 2)
        self.assertTrue(loop_state.remote_list.path_ambiguous)
        self.assertIsNone(loop_state.remote_list.current_generation)
        self.assertEqual(len(report.states), 4)
        self.assertEqual(report.final_state.target.validity, DucTargetStatus.UNKNOWN)
        self.assertEqual(len(report.loop_widenings), 1)
        widening = report.loop_widenings[0]
        self.assertIsInstance(widening, DucLoopWidening)
        self.assertEqual(widening.loop_head_rule_order, 2)
        self.assertEqual(widening.back_edge_source_rule_order, 3)
        self.assertEqual(widening.iteration_limit, 3)
        self.assertEqual(widening.iterations, 3)
        self.assertIn("REMOTE_LIST", widening.widened_fields)

    def test_loop_widening_is_field_local_for_local_search_state(self):
        rules = (
            _rule(1, (("up-find-remote", ("c:", "town-center", "c:", "1")),)),
            _rule(2, (("up-find-local", ("c:", "villager", "c:", "1")),)),
            _rule(3, (("up-jump-rule", ("-2",)),)),
            _rule(4, (("up-target-objects", ("1", "action-default", "-1", "-1")),)),
        )
        execution = RuleExecutionReport(
            rules=rules,
            reachability=RuleReachabilityReport(
                reachable_rule_orders=(1, 2, 3, 4),
                unreachable_rule_orders=(),
                incoming_rule_orders=((1, ()), (2, (1, 3)), (3, (2,)), (4, (3,))),
                outgoing_rule_orders=((1, (2,)), (2, (3,)), (3, (2, 4)), (4, ())),
            ),
        )

        report = analyze_duc(execution)

        loop_state = next(state for order, state in report.states if order == 2)
        self.assertTrue(loop_state.local_list.path_ambiguous)
        self.assertFalse(loop_state.remote_list.path_ambiguous)
        self.assertEqual(
            report.loop_widenings[0].widened_fields,
            ("LOCAL_LIST",),
        )

    def test_loop_widening_abstracts_retained_filter_lineage(self):
        rules = (
            _rule(1, (("up-find-remote", ("c:", "town-center", "c:", "1")),)),
            _rule(2, (
                ("up-filter-distance", ("c:", "0", "c:", "100")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
            )),
            _rule(3, (("up-jump-rule", ("-2",)),)),
            _rule(4, (("up-find-remote", ("c:", "town-center", "c:", "1")),)),
        )
        execution = RuleExecutionReport(
            rules=rules,
            reachability=RuleReachabilityReport(
                reachable_rule_orders=(1, 2, 3, 4),
                unreachable_rule_orders=(),
                incoming_rule_orders=((1, ()), (2, (1, 3)), (3, (2,)), (4, (3,))),
                outgoing_rule_orders=((1, (2,)), (2, (3,)), (3, (2, 4)), (4, ())),
            ),
        )

        report = analyze_duc(execution)

        self.assertTrue(report.final_state.filters.path_ambiguous)
        self.assertTrue(report.final_state.remote_list.path_ambiguous)
        self.assertTrue(
            any(item.code == "DUC-012" and item.rule_order == 4 for item in report.diagnostics)
        )
        widening = report.loop_widenings[0]
        self.assertEqual(widening.widened_fields, ("REMOTE_LIST", "FILTERS"))

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
