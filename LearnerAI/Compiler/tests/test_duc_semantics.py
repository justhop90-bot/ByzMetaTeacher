import unittest
from dataclasses import replace

from Compiler.ir.duc import (
    DucCardinalityRange,
    DucGoalOutputSpan,
    DucGroupStatus,
    DucSearchCursorDisposition,
    DucSearchFactResult,
    DucSearchAvailabilityResult,
    DucSearchResultDisposition,
    DucStateKind,
    DucListKind,
    DucListMutationKind,
    DucSearchIndexResetReason,
    DucLoopWidening,
    DucTargetConsumerMode,
    DucTargetDataRelation,
    DucTargetFactResult,
    DucTargetKind,
    DucTargetProof,
    DucTargetStatus,
    DucTargetTransition,
)
from Compiler.primitives import NativeContractCatalog, default_native_contract_catalog
from Compiler.semantic.duc import _empty_state, analyze_duc
from Compiler.semantic.recurrent_execution import (
    RecurrentExecutionStatus,
    analyze_recurrent_execution,
)
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
    def test_filter_generation_change_downgrades_local_target_proof_to_unknown(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-set-target-object", ("search-local", "c:", "0")),
                ("up-filter-distance", ("c:", "-1", "c:", "4")),
            )),
        ))

        self.assertIsNotNone(report.final_state.target)
        self.assertEqual(report.final_state.target.validity, DucTargetStatus.UNKNOWN)
        self.assertEqual(report.final_state.target.proof, DucTargetProof.UNKNOWN)


    def test_filter_generation_change_downgrades_remote_target_proof_to_unknown(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-set-target-object", ("search-remote", "c:", "0")),
                ("up-filter-distance", ("c:", "-1", "c:", "4")),
            )),
        ))

        self.assertIsNotNone(report.final_state.target)
        self.assertEqual(report.final_state.target.validity, DucTargetStatus.UNKNOWN)
        self.assertEqual(report.final_state.target.proof, DucTargetProof.UNKNOWN)


    def test_native_id_target_survives_filter_generation_change(self):
        report = analyze_duc((
            _rule(1, (
                ("up-set-target-by-id", ("c:", "93")),
                ("up-filter-distance", ("c:", "-1", "c:", "4")),
            )),
        ))

        self.assertIsNotNone(report.final_state.target)
        self.assertEqual(report.final_state.target.validity, DucTargetStatus.UNKNOWN)
        self.assertEqual(report.final_state.target.proof, DucTargetProof.NATIVE_ID_PROOF)


    def test_target_reestablishment_after_filter_change_restores_current_pass_proof(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-set-target-object", ("search-local", "c:", "0")),
                ("up-filter-distance", ("c:", "-1", "c:", "4")),
                ("up-set-target-object", ("search-local", "c:", "0")),
            )),
        ))

        self.assertIsNotNone(report.final_state.target)
        self.assertEqual(report.final_state.target.validity, DucTargetStatus.VALID)
        self.assertEqual(report.final_state.target.proof, DucTargetProof.CURRENT_PASS_PROOF)


    def test_get_cost_delta_creates_four_goal_output_span(self):
        report = analyze_duc((
            _rule(
                1,
                (("up-get-cost-delta", ("41",)),),
            ),
        ))

        self.assertEqual(len(report.final_state.goal_output_spans), 1)
        span = report.final_state.goal_output_spans[0]
        self.assertEqual(span.start_goal_id, 41)
        self.assertEqual(span.width, 4)
        self.assertEqual(span.provenance.command, "up-get-cost-delta")


    def test_get_cost_delta_accepts_last_native_start(self):
        report = analyze_duc((
            _rule(
                1,
                (("up-get-cost-delta", ("15996",)),),
            ),
        ))

        self.assertEqual(
            report.final_state.goal_output_spans[0].start_goal_id,
            15996,
        )
        self.assertEqual(report.final_state.goal_output_spans[0].width, 4)


    def test_get_cost_delta_rejects_start_that_would_overrun_extended_goal_span(self):
        report = analyze_duc((
            _rule(
                1,
                (("up-get-cost-delta", ("15997",)),),
            ),
        ))

        self.assertFalse(report.final_state.goal_output_spans)
        self.assertTrue(any(
            item.code == "DUC-017"
            and "15996" in item.message
            for item in report.diagnostics
        ))


    def test_recurrent_local_search_reports_evidence_backed_cost(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-find-local", ("c:", "villager", "c:", "1")),
            )),
        ))

        cost = tuple(item for item in report.diagnostics if item.code == "DUC-015")
        self.assertEqual(len(cost), 1)
        self.assertIn("local", cost[0].message)
        self.assertIn("240", cost[0].message)
        self.assertIn("MEDIUM", cost[0].message)
        self.assertEqual(cost[0].severity, "warning")


    def test_recurrent_remote_search_reports_evidence_backed_cost(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
            )),
        ))

        cost = tuple(item for item in report.diagnostics if item.code == "DUC-015")
        self.assertEqual(len(cost), 1)
        self.assertIn("remote", cost[0].message)
        self.assertIn("40", cost[0].message)
        self.assertIn("FAST", cost[0].message)
        self.assertEqual(cost[0].severity, "warning")


    def test_same_rule_search_reset_suppresses_recurrent_cost_diagnostic(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-reset-search", ("1", "1", "0", "0")),
                ("up-find-local", ("c:", "villager", "c:", "1")),
            )),
        ))

        self.assertFalse(any(item.code == "DUC-015" for item in report.diagnostics))


    def test_one_shot_search_does_not_emit_recurrent_cost_diagnostic(self):
        report = analyze_duc((
            _rule(
                1,
                (
                    ("up-find-local", ("c:", "villager", "c:", "1")),
                    ("up-find-local", ("c:", "villager", "c:", "1")),
                    ("disable-self", ()),
                ),
                pass_behavior=RulePassBehavior.ONE_SHOT,
            ),
        ))

        self.assertFalse(any(item.code == "DUC-015" for item in report.diagnostics))


    def test_can_search_uninitialized_local_is_runtime_dependent(self):
        location = SourceLocation(1, 1, "fixture.per")
        fact = Expression(
            "(up-can-search search-local)",
            "up-can-search",
            ("search-local",),
            location,
        )
        report = analyze_duc((
            replace(_rule(1, ()), facts=(fact,)),
        ))

        observation = report.search_availability[-1]
        self.assertEqual(observation.source_list, DucListKind.LOCAL)
        self.assertEqual(
            observation.result,
            DucSearchAvailabilityResult.RUNTIME_DEPENDENT,
        )
        self.assertEqual(
            observation.cursor_disposition,
            DucSearchCursorDisposition.INITIAL,
        )

    def test_can_search_proven_end_is_guaranteed_false(self):
        location = SourceLocation(2, 1, "fixture.per")
        fact = Expression(
            "(up-can-search search-local)",
            "up-can-search",
            ("search-local",),
            location,
        )
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
            )),
            replace(_rule(2, ()), facts=(fact,)),
        ))

        observation = report.search_availability[-1]
        self.assertEqual(
            observation.result,
            DucSearchAvailabilityResult.GUARANTEED_FALSE,
        )
        self.assertEqual(
            observation.cursor_disposition,
            DucSearchCursorDisposition.AT_END,
        )

    def test_can_search_remote_reads_only_remote_search_state(self):
        location = SourceLocation(2, 1, "fixture.per")
        fact = Expression(
            "(up-can-search search-remote)",
            "up-can-search",
            ("search-remote",),
            location,
        )
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
            )),
            replace(_rule(2, ()), facts=(fact,)),
        ))

        observation = report.search_availability[-1]
        self.assertEqual(observation.source_list, DucListKind.REMOTE)
        self.assertEqual(
            observation.result,
            DucSearchAvailabilityResult.RUNTIME_DEPENDENT,
        )
        self.assertEqual(
            observation.cursor_disposition,
            DucSearchCursorDisposition.RUNTIME_ADVANCED,
        )

    def test_set_target_object_action_rejects_first_remote_out_of_range_index(self):
        report = analyze_duc(
            (
                _rule(
                    1,
                    (
                        ("up-find-remote", ("c:", "town-center", "c:", "1")),
                        ("up-set-target-object", ("search-remote", "c:", "40")),
                    ),
                ),
            ),
        )

        self.assertIsNone(report.final_state.target)
        self.assertTrue(
            any(
                item.code == "DUC-014"
                and "remote list capacity 40" in item.message
                for item in report.diagnostics
            )
        )

    def test_set_target_object_fact_on_proven_empty_search_list_is_guaranteed_false(self):
        initial = _empty_state()
        local = replace(
            initial.local_list,
            search_index=replace(
                initial.local_list.search_index,
                cursor_disposition=DucSearchCursorDisposition.AT_END,
            ),
        )
        initial = replace(initial, local_list=local)
        location = SourceLocation(1, 1, "fixture.per")
        target_fact = Expression(
            "(up-set-target-object search-local c: 0)",
            "up-set-target-object",
            ("search-local", "c:", "0"),
            location,
        )

        report = analyze_duc(
            (
                replace(
                    _rule(1, ()),
                    facts=(target_fact,),
                ),
            ),
            initial_state=initial,
        )

        self.assertEqual(
            report.target_fact_observations[-1].result,
            DucTargetFactResult.GUARANTEED_FALSE,
        )
        self.assertIsNone(report.target_fact_observations[-1].target)

    def test_set_target_object_action_rejects_proven_empty_search_list(self):
        from Compiler.semantic.duc import _empty_state

        initial = _empty_state()
        local = replace(
            initial.local_list,
            search_index=replace(
                initial.local_list.search_index,
                cursor_disposition=DucSearchCursorDisposition.AT_END,
            ),
        )
        initial = replace(initial, local_list=local)

        report = analyze_duc(
            (
                _rule(
                    1,
                    (
                        ("up-find-local", ("c:", "villager", "c:", "1")),
                        ("up-set-target-object", ("search-local", "c:", "0")),
                    ),
                ),
            ),
            initial_state=initial,
        )

        self.assertEqual(
            report.searches[-1].output_generation.cardinality,
            DucCardinalityRange(0, 0),
        )
        self.assertIsNone(report.final_state.target)
        self.assertTrue(
            any(
                item.code == "DUC-014"
                and "proven zero cardinality" in item.message
                for item in report.diagnostics
            )
        )

    def test_failed_target_action_on_uninitialized_search_list_does_not_establish_target(self):
        report = analyze_duc((
            _rule(1, (
                ("up-set-target-object", ("search-local", "c:", "0")),
            )),
        ))

        self.assertIsNone(report.final_state.target)
        self.assertTrue(any(
            item.code == "DUC-005"
            and "no initialized search list" in item.message
            for item in report.diagnostics
        ))

    def test_set_target_object_fact_records_runtime_dependent_result_without_fabricating_target(self):
        location = SourceLocation(1, 1, "fixture.per")
        find_fact = Expression(
            "(up-find-local c: villager c: 1)",
            "up-find-local",
            ("c:", "villager", "c:", "1"),
            location,
        )
        target_fact = Expression(
            "(up-set-target-object search-local c: 0)",
            "up-set-target-object",
            ("search-local", "c:", "0"),
            location,
        )
        report = analyze_duc((
            replace(_rule(1, ()), facts=(find_fact, target_fact)),
        ))

        self.assertEqual(
            report.target_fact_observations[-1].result,
            DucTargetFactResult.RUNTIME_DEPENDENT,
        )
        self.assertIsNone(report.target_fact_observations[-1].target)
        self.assertIsNone(report.final_state.target)

    def test_set_target_object_fact_out_of_range_is_guaranteed_false(self):
        location = SourceLocation(1, 1, "fixture.per")
        find_fact = Expression(
            "(up-find-local c: villager c: 1)",
            "up-find-local",
            ("c:", "villager", "c:", "1"),
            location,
        )
        target_fact = Expression(
            "(up-set-target-object search-local c: 240)",
            "up-set-target-object",
            ("search-local", "c:", "240"),
            location,
        )
        report = analyze_duc((
            replace(_rule(1, ()), facts=(find_fact, target_fact)),
        ))

        self.assertEqual(
            report.target_fact_observations[-1].result,
            DucTargetFactResult.GUARANTEED_FALSE,
        )
        self.assertIsNone(report.final_state.target)

    def test_failed_target_action_preserves_existing_target_when_native_effect_is_open(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-set-target-object", ("search-local", "c:", "0")),
                ("up-set-target-object", ("search-local", "c:", "240")),
            )),
        ))

        self.assertIsNotNone(report.final_state.target)
        self.assertEqual(report.final_state.target.validity, DucTargetStatus.VALID)
        self.assertTrue(any(
            item.code == "DUC-007"
            and "failed target establishment Action" in item.message
            for item in report.diagnostics
        ))

    def test_control_flow_report_preserves_target_fact_observations(self):
        location = SourceLocation(1, 1, "fixture.per")
        target_fact = Expression(
            "(up-set-target-object search-local c: 0)",
            "up-set-target-object",
            ("search-local", "c:", "0"),
            location,
        )
        rules = (
            replace(
                _rule(1, (("up-do-nothing", ()),)),
                facts=(target_fact,),
            ),
            _rule(2, (("up-do-nothing", ()),)),
        )
        execution = RuleExecutionReport(
            rules=rules,
            reachability=RuleReachabilityReport(
                reachable_rule_orders=(1, 2),
                unreachable_rule_orders=(),
                incoming_rule_orders=((1, ()), (2, (1,))),
                outgoing_rule_orders=((1, (2,)), (2, ())),
            ),
        )

        report = analyze_duc(execution)

        self.assertEqual(len(report.target_fact_observations), 1)
        self.assertEqual(
            report.target_fact_observations[0].result,
            DucTargetFactResult.GUARANTEED_FALSE,
        )
        self.assertEqual(
            report.target_fact_observations[0].provenance.rule_order,
            1,
        )

    def test_control_flow_report_preserves_target_consumer_effects(self):
        rules = (
            _rule(
                1,
                (
                    ("up-find-local", ("c:", "villager", "c:", "1")),
                    ("up-target-objects", ("0", "action-default", "-1", "-1")),
                ),
            ),
            _rule(2, (("up-do-nothing", ()),)),
        )
        execution = RuleExecutionReport(
            rules=rules,
            reachability=RuleReachabilityReport(
                reachable_rule_orders=(1, 2),
                unreachable_rule_orders=(),
                incoming_rule_orders=((1, ()), (2, (1,))),
                outgoing_rule_orders=((1, (2,)), (2, ())),
            ),
        )

        report = analyze_duc(execution)

        self.assertEqual(len(report.target_consumers), 1)
        self.assertEqual(
            report.target_consumers[0].mode,
            DucTargetConsumerMode.LOCAL_SEARCH_RESULTS,
        )
        self.assertEqual(report.target_consumers[0].provenance.rule_order, 1)

    def test_duc_state_effects_ignore_rule_that_recurrent_analysis_proves_never_runnable(self):
        rules = (
            _rule(1, (("set-goal", ("duc-gate", "0")),)),
            replace(
                _rule(2, (("up-find-local", ("c:", "villager", "c:", "1")),)),
                facts=(Expression("(goal duc-gate = 1)", "goal", ("duc-gate", "=", "1"), SourceLocation(2, 1, "fixture.per")),),
            ),
        )
        execution = RuleExecutionReport(
            rules=rules,
            reachability=RuleReachabilityReport(
                reachable_rule_orders=(1, 2),
                unreachable_rule_orders=(),
                incoming_rule_orders=((1, ()), (2, (1,))),
                outgoing_rule_orders=((1, (2,)), (2, ())),
            ),
        )

        recurrent = analyze_recurrent_execution(execution)
        self.assertEqual(
            recurrent.status_for_rule(2),
            RecurrentExecutionStatus.NEVER_RUNNABLE,
        )
        report = analyze_duc(execution, recurrent_execution=recurrent)

        self.assertEqual(report.searches, ())
        self.assertIsNone(report.final_state.local_list.current_generation)


    def test_never_runnable_duc_rule_does_not_export_its_jump_edge(self):
        rules = (
            _rule(1, (("set-goal", ("duc-gate", "0")),)),
            replace(
                _rule(2, (("up-jump-rule", ("2",)),)),
                facts=(Expression("(goal duc-gate = 1)", "goal", ("duc-gate", "=", "1"), SourceLocation(2, 1, "fixture.per")),),
            ),
            _rule(3, (("up-find-local", ("c:", "villager", "c:", "1")),)),
            _rule(4, (("up-do-nothing", ()),)),
        )
        execution = RuleExecutionReport(
            rules=rules,
            reachability=RuleReachabilityReport(
                reachable_rule_orders=(1, 2, 3, 4),
                unreachable_rule_orders=(),
                incoming_rule_orders=((1, ()), (2, (1,)), (3, (2,)), (4, (2, 3))),
                outgoing_rule_orders=((1, (2,)), (2, (4,)), (3, (4,)), (4, ())),
            ),
        )

        recurrent = analyze_recurrent_execution(execution)
        self.assertEqual(
            recurrent.status_for_rule(2),
            RecurrentExecutionStatus.NEVER_RUNNABLE,
        )
        report = analyze_duc(execution, recurrent_execution=recurrent)

        self.assertEqual(len(report.searches), 1)
        self.assertEqual(report.searches[0].provenance.rule_order, 3)


    def test_runtime_dependent_rule_keeps_duc_effects_live(self):
        rules = (
            _rule(1, (("up-find-local", ("c:", "villager", "c:", "1")),)),
            replace(
                _rule(2, (("up-find-local", ("c:", "archer-line", "c:", "1")),)),
                facts=(Expression("(game-time >= 600)", "game-time", (">=", "600"), SourceLocation(2, 1, "fixture.per")),),
            ),
        )
        execution = RuleExecutionReport(
            rules=rules,
            reachability=RuleReachabilityReport(
                reachable_rule_orders=(1, 2),
                unreachable_rule_orders=(),
                incoming_rule_orders=((1, ()), (2, (1,))),
                outgoing_rule_orders=((1, (2,)), (2, ())),
            ),
        )

        recurrent = analyze_recurrent_execution(execution)
        self.assertEqual(
            recurrent.status_for_rule(2),
            RecurrentExecutionStatus.MAY_RUN,
        )
        report = analyze_duc(execution, recurrent_execution=recurrent)

        self.assertEqual(len(report.searches), 2)
        self.assertEqual(report.searches[-1].provenance.rule_order, 2)


    def test_repeated_searches_append_to_one_retained_list_generation_lineage(self):
        report = analyze_duc((
            _rule(1, (
                ("up-full-reset-search", ()),
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-find-local", ("c:", "archer-line", "c:", "1")),
                ("up-find-local", ("c:", "skirmisher-line", "c:", "1")),
            )),
        ))

        self.assertEqual(len(report.searches), 3)
        first, second, third = report.searches
        self.assertEqual(first.output_generation.cardinality, DucCardinalityRange(0, 240))
        self.assertEqual(first.output_generation.last_search_cardinality, DucCardinalityRange(0, 240))
        self.assertEqual(second.output_generation.produced_by.input_state_generations[0], 1)
        self.assertEqual(third.output_generation.produced_by.input_state_generations[0], 2)
        self.assertEqual(third.output_generation.capacity, 240)
        self.assertEqual(second.output_generation.last_search_cardinality, DucCardinalityRange(0, 240))
        self.assertEqual(third.output_generation.last_search_cardinality, DucCardinalityRange(0, 240))
        self.assertEqual(third.output_generation.cardinality.maximum, 240)
        self.assertNotEqual(first.output_generation.content_fingerprint, third.output_generation.content_fingerprint)

    def test_search_state_binds_concrete_four_goal_output_span(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-get-search-state", ("41",)),
            )),
        ))

        observation = report.observations[-1]
        self.assertIsNotNone(observation.output_span)
        self.assertEqual(observation.output_span.start_goal_id, 41)
        self.assertEqual(observation.output_span.width, 4)
        self.assertEqual(observation.output_span.generation, 1)
        self.assertIsNone(observation.output_span.overwritten_generation)
        self.assertEqual(
            observation.output_span.provenance.command,
            "up-get-search-state",
        )
        self.assertEqual(
            report.final_state.goal_output_spans,
            (observation.output_span,),
        )


    def test_search_state_overwrite_records_previous_four_goal_span_provenance(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-get-search-state", ("41",)),
                ("up-get-search-state", ("41",)),
            )),
        ))

        first, second = report.observations[-2:]
        self.assertEqual(first.output_span.width, 4)
        self.assertEqual(second.output_span.width, 4)
        self.assertEqual(second.output_span.generation, 2)
        self.assertEqual(second.output_span.overwritten_generation, 1)
        self.assertEqual(
            second.output_span.overwritten_provenance.command,
            "up-get-search-state",
        )
        self.assertEqual(
            report.final_state.goal_output_spans,
            (second.output_span,),
        )


    def test_search_state_accepts_highest_safe_four_goal_start(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-get-search-state", ("15996",)),
            )),
        ))

        span = report.observations[-1].output_span
        self.assertIsNotNone(span)
        self.assertEqual(span.start_goal_id, 15996)
        self.assertEqual(span.width, 4)
        self.assertEqual(report.final_state.goal_output_spans, (span,))


    def test_search_state_rejects_start_that_cannot_fit_four_goals(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-get-search-state", ("15997",)),
            )),
        ))

        self.assertTrue(
            any(
                item.code == "DUC-017"
                and "15996" in item.message
                for item in report.diagnostics
            )
        )
        self.assertEqual(report.observations, ())
        self.assertEqual(report.final_state.goal_output_spans, ())


    def test_goal_output_branch_join_widens_conflicting_search_and_group_writers(self):
        rules = (
            _rule(1, (("up-jump-rule", ("1",)),)),
            _rule(2, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-get-search-state", ("41",)),
            )),
            _rule(3, (("up-get-group-size", ("c:", "0", "41")),)),
            _rule(4, (("up-do-nothing", ()),)),
        )
        report = analyze_duc(self._branched_execution(rules))

        span = report.final_state.goal_output_spans[0]
        self.assertEqual(span.start_goal_id, 41)
        self.assertEqual(span.width, 4)
        self.assertTrue(span.path_ambiguous)
        self.assertIsNone(span.provenance)
        self.assertIsNone(span.overwritten_provenance)
        self.assertIsNone(span.overwritten_generation)
    def test_search_state_branch_join_preserves_width_four_output_span(self):
        rules = (
            _rule(1, (("up-jump-rule", ("1",)),)),
            _rule(2, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-get-search-state", ("41",)),
            )),
            _rule(3, (("up-do-nothing", ()),)),
            _rule(4, (("up-do-nothing", ()),)),
        )
        report = analyze_duc(self._branched_execution(rules))

        span = report.final_state.goal_output_spans[0]
        self.assertEqual(span.width, 4)
        self.assertTrue(span.path_ambiguous)
        self.assertIsNone(span.provenance)


    def test_search_state_symbolic_output_goal_remains_unresolved(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-get-search-state", ("search-state-output",)),
            )),
        ))

        observation = report.observations[-1]
        self.assertIsNone(observation.output_span)
        self.assertEqual(report.final_state.goal_output_spans, ())


    def test_search_state_tracks_total_and_last_search_cardinality(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-get-search-state", ("41",)),
            )),
        ))

        observation = report.observations[-1]
        self.assertEqual(observation.local_total_cardinality, DucCardinalityRange(0, 240))
        self.assertEqual(observation.local_last_search_cardinality, DucCardinalityRange(0, 240))
        self.assertEqual(observation.remote_total_cardinality, DucCardinalityRange(0, 40))
        self.assertEqual(observation.remote_last_search_cardinality, DucCardinalityRange(0, 40))

    def test_full_reset_zeroes_retained_search_cardinality(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-full-reset-search", ()),
                ("up-get-search-state", ("41",)),
            )),
        ))

        observation = report.observations[-1]
        self.assertEqual(observation.local_total_cardinality, DucCardinalityRange(0, 0))
        self.assertEqual(observation.remote_total_cardinality, DucCardinalityRange(0, 0))
        self.assertEqual(observation.local_last_search_cardinality, DucCardinalityRange(0, 0))
        self.assertEqual(observation.remote_last_search_cardinality, DucCardinalityRange(0, 0))

    def test_goal_output_span_rejects_incoherent_overwrite_provenance(self):
        with self.assertRaisesRegex(
            ValueError,
            "without an overwritten generation",
        ):
            DucGoalOutputSpan(
                start_goal_id=41,
                width=1,
                generation=1,
                overwritten_generation=None,
                overwritten_provenance=object(),
                provenance=None,
                cardinality=DucCardinalityRange(0, 0),
            )

    def test_group_size_writes_a_concrete_width_one_goal_output_span(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-create-group", ("0", "2", "c:", "3")),
                ("up-get-group-size", ("c:", "3", "41")),
            )),
        ))

        observation = report.group_observations[-1]
        span = observation.output_span
        self.assertEqual(span.start_goal_id, 41)
        self.assertEqual(span.width, 1)
        self.assertEqual(span.generation, 1)
        self.assertIsNone(span.overwritten_generation)
        self.assertEqual(span.provenance.command, "up-get-group-size")
        self.assertEqual(span.provenance.input_group_generations, ((3, 1),))
        self.assertEqual(span.cardinality, report.final_state.groups[3].cardinality)
        self.assertEqual(report.final_state.goal_output_spans[0], span)

    def test_repeated_group_size_writes_same_goal_overwrite_with_new_provenance(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-create-group", ("0", "2", "c:", "3")),
                ("up-get-group-size", ("c:", "3", "41")),
                ("up-create-group", ("0", "1", "c:", "4")),
                ("up-get-group-size", ("c:", "4", "41")),
            )),
        ))

        first, second = report.group_observations[-2:]
        self.assertEqual(first.output_span.generation, 1)
        self.assertEqual(second.output_span.generation, 2)
        self.assertEqual(second.output_span.overwritten_generation, 1)
        self.assertEqual(
            second.output_span.overwritten_provenance.command,
            "up-get-group-size",
        )
        self.assertEqual(second.output_span.provenance.command, "up-get-group-size")
        self.assertEqual(second.output_span.provenance.input_group_generations, ((4, 1),))
        self.assertEqual(report.final_state.goal_output_spans, (second.output_span,))

    def test_group_size_goal_output_persists_across_pass_and_overwrites_previous_writer(self):
        first_report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-create-group", ("0", "2", "c:", "3")),
                ("up-get-group-size", ("c:", "3", "41")),
            )),
        ))
        first_span = first_report.final_state.goal_output_spans[0]

        second_report = analyze_duc(
            (
                _rule(1, (
                    ("up-get-group-size", ("c:", "3", "41")),
                )),
            ),
            initial_state=first_report.next_pass_state,
        )
        second_span = second_report.final_state.goal_output_spans[0]

        self.assertEqual(
            first_report.next_pass_state.goal_output_spans,
            (first_span,),
        )
        self.assertEqual(second_span.generation, 2)
        self.assertEqual(second_span.overwritten_generation, 1)
        self.assertEqual(second_span.overwritten_provenance, first_span.provenance)
        self.assertEqual(second_span.pass_id, 1)

    def test_group_size_goal_output_join_is_zero_to_max_when_one_path_does_not_write(self):
        rules = (
            _rule(1, (("up-jump-rule", ("1",)),)),
            _rule(2, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-create-group", ("0", "2", "c:", "3")),
                ("up-get-group-size", ("c:", "3", "41")),
            )),
            _rule(3, (("up-do-nothing", ()),)),
            _rule(4, (("up-group-size", ("c:", "3", ">=", "0")),)),
        )
        report = analyze_duc(self._branched_execution(rules))

        span = report.final_state.goal_output_spans[0]
        self.assertTrue(span.path_ambiguous)
        self.assertIsNone(span.provenance)
        self.assertEqual(span.cardinality.minimum, 0)
        self.assertGreaterEqual(span.cardinality.maximum, 0)

    def test_group_size_output_goal_out_of_native_range_is_diagnostic(self):
        report = analyze_duc((
            _rule(1, (
                ("up-get-group-size", ("c:", "3", "16001")),
            )),
        ))

        self.assertTrue(
            any(
                item.code == "DUC-017"
                and "1..16000" in item.message
                for item in report.diagnostics
            )
        )
        self.assertEqual(report.group_observations, ())

    def test_group_size_output_overwrite_divergence_becomes_path_ambiguous(self):
        rules = (
            _rule(1, (("up-jump-rule", ("1",)),)),
            _rule(2, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-create-group", ("0", "2", "c:", "3")),
                ("up-get-group-size", ("c:", "3", "41")),
            )),
            _rule(3, (
                ("up-find-local", ("c:", "archer-line", "c:", "1")),
                ("up-create-group", ("0", "1", "c:", "4")),
                ("up-get-group-size", ("c:", "4", "41")),
            )),
            _rule(4, (("up-group-size", ("c:", "3", ">=", "0")),)),
        )
        report = analyze_duc(self._branched_execution(rules))

        self.assertEqual(len(report.final_state.goal_output_spans), 1)
        span = report.final_state.goal_output_spans[0]
        self.assertEqual(span.start_goal_id, 41)
        self.assertTrue(span.path_ambiguous)
        self.assertIsNone(span.provenance)
        self.assertIsNone(span.overwritten_generation)

    def test_group_contracts_are_first_class_and_persistent(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-create-group", ("0", "2", "c:", "3")),
            )),
            _rule(2, (
                ("up-get-group-size", ("c:", "3", "41")),
                ("up-group-size", ("c:", "3", ">=", "0")),
            )),
        ))

        group = report.final_state.groups[3]
        self.assertEqual(group.group_id, 3)
        self.assertEqual(group.capacity, 40)
        self.assertEqual(group.source_list, DucListKind.LOCAL)
        self.assertEqual(group.source_list_generation, 1)
        self.assertEqual(group.requested_max_objects, 2)
        self.assertEqual(group.validity, DucGroupStatus.UNKNOWN)
        self.assertEqual(group.provenance.command, "up-create-group")
        self.assertEqual(group.provenance.input_state_generations, (1,))
        self.assertEqual(group.pass_id, 0)
        self.assertEqual(report.next_pass_state.groups[3].generation, group.generation)

    def test_reset_group_replaces_membership_and_advances_group_generation(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-create-group", ("0", "2", "c:", "3")),
                ("up-reset-group", ("c:", "3")),
            )),
        ))

        group = report.final_state.groups[3]
        self.assertEqual(group.validity, DucGroupStatus.EMPTY)
        self.assertEqual(group.cardinality, DucCardinalityRange(0, 0))
        self.assertEqual(group.generation, 2)
        self.assertEqual(group.provenance.command, "up-reset-group")

    def test_set_group_reloads_destination_list_and_invalidates_old_target(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-create-group", ("0", "2", "c:", "3")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-set-target-object", ("search-remote", "c:", "0")),
                ("up-set-group", ("search-remote", "c:", "3")),
            )),
        ))

        group = report.final_state.groups[3]
        self.assertNotEqual(group.validity, DucGroupStatus.EMPTY)
        remote = report.final_state.remote_list.current_generation
        self.assertIsNotNone(remote)
        self.assertEqual(remote.produced_by.command, "up-set-group")
        self.assertEqual(remote.cardinality, group.cardinality)
        self.assertEqual(remote.produced_by.input_group_generations, ((3, group.generation),))
        self.assertIsNotNone(report.final_state.target)
        self.assertEqual(report.final_state.target.validity, DucTargetStatus.STALE)

    def test_group_flag_state_is_persistent_until_overwritten(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-create-group", ("0", "2", "c:", "3")),
                ("up-modify-group-flag", ("1", "c:", "3")),
                ("up-modify-group-flag", ("0", "c:", "3")),
            )),
            _rule(2, (
                ("up-group-size", ("c:", "3", ">=", "0")),
            )),
        ))

        group = report.final_state.groups[3]
        self.assertEqual(group.flag_state.value, "CLEARED")
        self.assertEqual(report.next_pass_state.groups[3].flag_state.value, "CLEARED")

    def test_group_branch_divergence_widens_to_unknown(self):
        rules = (
            _rule(1, (("up-jump-rule", ("1",)),)),
            _rule(2, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-create-group", ("0", "2", "c:", "3")),
            )),
            _rule(3, (("up-reset-group", ("c:", "3")),)),
            _rule(4, (("up-group-size", ("c:", "3", ">=", "0")),)),
        )
        report = analyze_duc(self._branched_execution(rules))

        merged_group = report.final_state.groups[3]
        self.assertIn("GROUPS", next(item for item in report.branch_merges if item.rule_order == 4).merged_fields)
        self.assertEqual(merged_group.validity, DucGroupStatus.UNKNOWN)
        self.assertTrue(merged_group.path_ambiguous)
        self.assertEqual(merged_group.flag_state.value, "UNKNOWN")
        self.assertIsNone(merged_group.provenance)
    def test_search_reset_does_not_destroy_persistent_group(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-create-group", ("0", "2", "c:", "3")),
                ("up-full-reset-search", ()),
                ("up-set-group", ("search-remote", "c:", "3")),
                ("up-group-size", ("c:", "3", "==", "0")),
            )),
        ))

        group = report.final_state.groups[3]
        self.assertNotEqual(group.validity, DucGroupStatus.EMPTY)
        self.assertEqual(
            report.final_state.remote_list.current_generation.produced_by.command,
            "up-set-group",
        )
        self.assertEqual(
            report.final_state.remote_list.current_generation.produced_by.input_group_generations,
            ((3, group.generation),),
        )

    def test_group_overwrite_advances_generation_and_replaces_provenance(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-create-group", ("0", "2", "c:", "3")),
                ("up-create-group", ("0", "1", "c:", "3")),
            )),
        ))

        group = report.final_state.groups[3]
        self.assertEqual(group.generation, 2)
        self.assertEqual(group.provenance.command, "up-create-group")
        self.assertEqual(group.requested_max_objects, 1)

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
        self.assertIsNotNone(loop_state.remote_list.current_generation)
        self.assertEqual(loop_state.remote_list.current_generation.generation, 2)
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

    def test_loop_widening_emits_single_field_diagnostic(self):
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

        widening_diagnostics = tuple(
            item for item in report.diagnostics if item.code == "DUC-016"
        )
        self.assertEqual(len(widening_diagnostics), 1)
        diagnostic = widening_diagnostics[0]
        self.assertEqual(diagnostic.rule_order, 3)
        self.assertIn("loop head 2", diagnostic.message)
        self.assertIn("back-edge source 3", diagnostic.message)
        self.assertIn("iteration bound 3", diagnostic.message)
        self.assertIn("widened fields: LOCAL_LIST", diagnostic.message)

    def test_loop_widening_emits_multi_field_diagnostic(self):
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

        diagnostic = next(
            item for item in report.diagnostics if item.code == "DUC-016"
        )
        self.assertEqual(diagnostic.rule_order, 3)
        self.assertIn("loop head 2", diagnostic.message)
        self.assertIn("back-edge source 3", diagnostic.message)
        self.assertIn("iteration bound 3", diagnostic.message)
        self.assertIn("widened fields: REMOTE_LIST, FILTERS", diagnostic.message)

    def test_search_state_provenance_uses_shared_output_evidence(self):
        base = default_native_contract_catalog()
        shared = NativeContractCatalog(
            duc_output_evidence_ids=("airef:duc:get-search-state",),
        )
        report = analyze_duc(
            (
                _rule(1, (
                    ("up-find-remote", ("c:", "town-center", "c:", "1")),
                    ("up-get-search-state", ("100",)),
                )),
            ),
            contracts=shared,
        )

        self.assertEqual(
            report.observations[-1].provenance.evidence_ids,
            ("airef:duc:get-search-state",),
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

    def test_target_proof_records_explicit_current_pass_identity(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-set-target-object", ("search-remote", "c:", "0")),
            )),
        ))

        target = report.final_state.target
        self.assertIsNotNone(target)
        self.assertEqual(getattr(report.final_state, "pass_id", None), 0)
        self.assertEqual(getattr(target, "pass_id", None), 0)
        self.assertEqual(
            getattr(getattr(target, "proof", None), "value", None),
            "CURRENT_PASS_PROOF",
        )

    def test_cross_pass_target_reuse_becomes_syntactic_retention(self):
        first = analyze_duc((
            _rule(1, (
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-set-target-object", ("search-remote", "c:", "0")),
            )),
        ))

        second = analyze_duc((
            _rule(1, (
                ("up-target-objects", ("1", "action-default", "-1", "-1")),
            )),
        ), initial_state=first.next_pass_state)

        target = second.final_state.target
        self.assertIsNotNone(target)
        self.assertEqual(second.final_state.pass_id, 1)
        self.assertEqual(target.pass_id, 0)
        self.assertEqual(target.validity, DucTargetStatus.UNKNOWN)
        self.assertEqual(target.proof, DucTargetProof.SYNTACTIC_RETENTION)
        self.assertTrue(any(
            item.code == "DUC-007"
            and "retained across a pass" in item.message
            for item in second.diagnostics
        ))


    def test_cross_pass_target_reestablishment_preserves_source_proof(self):
        first = analyze_duc((
            _rule(1, (
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-set-target-object", ("search-remote", "c:", "0")),
            )),
        ))

        second = analyze_duc((
            _rule(1, (
                ("up-set-target-object", ("search-remote", "c:", "0")),
                ("up-target-objects", ("1", "action-default", "-1", "-1")),
            )),
        ), initial_state=first.next_pass_state)

        target = second.final_state.target
        self.assertIsNotNone(target)
        self.assertEqual(target.pass_id, 1)
        self.assertEqual(target.validity, DucTargetStatus.VALID)
        self.assertEqual(target.proof, DucTargetProof.PRESERVED_PROOF)
        self.assertFalse(any(item.code == "DUC-007" for item in second.diagnostics))


    def test_cross_pass_stale_target_is_not_weakened_to_unknown(self):
        first = analyze_duc((
            _rule(1, (
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-set-target-object", ("search-remote", "c:", "0")),
                ("up-reset-search", ("0", "0", "0", "1")),
            )),
        ))

        self.assertEqual(first.final_state.target.validity, DucTargetStatus.STALE)
        self.assertEqual(first.final_state.target.proof, DucTargetProof.UNKNOWN)

        second = analyze_duc((
            _rule(1, (
                ("up-target-objects", ("1", "action-default", "-1", "-1")),
            )),
        ), initial_state=first.next_pass_state)

        target = second.final_state.target
        self.assertIsNotNone(target)
        self.assertEqual(target.validity, DucTargetStatus.STALE)
        self.assertNotIn("retained across a pass", "\n".join(item.message for item in second.diagnostics))
        self.assertTrue(any(item.code == "DUC-006" for item in second.diagnostics))


    def test_list_mutation_forces_unknown_target_proof(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-set-target-object", ("search-remote", "c:", "0")),
                ("up-remove-objects", ("search-remote", "-1", "c:", "1")),
            )),
        ))

        self.assertEqual(report.final_state.target.validity, DucTargetStatus.UNKNOWN)
        self.assertEqual(report.final_state.target.proof, DucTargetProof.UNKNOWN)

    def test_analyze_duc_consumes_shared_native_catalog_contracts(self):
        base = default_native_contract_catalog()
        altered = replace(
            base.duc_mutation("up-clean-search"),
            sentinel_object_data="999",
        )
        shared = NativeContractCatalog(
            duc_mutations=(
                altered,
                *(item for item in base.duc_mutations if item.command != "up-clean-search"),
            ),
        )

        report = analyze_duc(
            (
                _rule(1, (
                    ("up-find-local", ("c:", "villager", "c:", "4")),
                    ("up-set-target-object", ("search-local", "c:", "0")),
                    ("up-clean-search", ("search-local", "-1", "1")),
                )),
            ),
            contracts=shared,
        )

        self.assertEqual(report.mutations[-1].kind, DucListMutationKind.SORT)

    def test_clean_search_sort_preserves_target_proof(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "4")),
                ("up-set-target-object", ("search-local", "c:", "0")),
                ("up-clean-search", ("search-local", "object-data-hitpoints", "1")),
            )),
        ))

        target = report.final_state.target
        self.assertIsNotNone(target)
        self.assertEqual(target.validity, DucTargetStatus.UNKNOWN)
        self.assertEqual(target.proof, DucTargetProof.UNKNOWN)
        mutation = report.mutations[-1]
        self.assertEqual(mutation.kind, DucListMutationKind.SORT)
        self.assertEqual(mutation.target_transition, DucTargetTransition.UNKNOWN)

    def test_clean_search_duplicate_removal_makes_nonfirst_target_unknown(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "4")),
                ("up-set-target-object", ("search-local", "c:", "1")),
                ("up-clean-search", ("search-local", "-1", "1")),
            )),
        ))

        target = report.final_state.target
        self.assertIsNotNone(target)
        self.assertEqual(target.validity, DucTargetStatus.UNKNOWN)
        self.assertEqual(target.proof, DucTargetProof.UNKNOWN)
        mutation = report.mutations[-1]
        self.assertEqual(mutation.kind, DucListMutationKind.DEDUPE)
        self.assertEqual(mutation.target_transition, DucTargetTransition.UNKNOWN)

    def test_clean_search_duplicate_removal_makes_first_target_unknown(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "4")),
                ("up-set-target-object", ("search-local", "c:", "0")),
                ("up-clean-search", ("search-local", "-1", "1")),
            )),
        ))

        target = report.final_state.target
        self.assertIsNotNone(target)
        self.assertEqual(target.validity, DucTargetStatus.UNKNOWN)
        self.assertEqual(target.proof, DucTargetProof.UNKNOWN)

    def test_remove_objects_exact_index_match_makes_target_stale(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "4")),
                ("up-set-target-object", ("search-local", "c:", "1")),
                ("up-remove-objects", ("search-local", "-1", "==", "1")),
            )),
        ))

        target = report.final_state.target
        self.assertIsNotNone(target)
        self.assertEqual(target.validity, DucTargetStatus.STALE)
        self.assertEqual(target.proof, DucTargetProof.UNKNOWN)
        mutation = report.mutations[-1]
        self.assertEqual(mutation.kind, DucListMutationKind.REMOVE_MATCHES)
        self.assertEqual(mutation.target_transition, DucTargetTransition.STALE)

    def test_remove_objects_greater_than_target_preserves_index_proof(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "4")),
                ("up-set-target-object", ("search-local", "c:", "1")),
                ("up-remove-objects", ("search-local", "-1", ">", "1")),
            )),
        ))

        target = report.final_state.target
        self.assertIsNotNone(target)
        self.assertEqual(target.validity, DucTargetStatus.VALID)
        self.assertEqual(target.proof, DucTargetProof.CURRENT_PASS_PROOF)
        self.assertTrue(target.object_refs[0].index_stable)
        self.assertEqual(
            report.mutations[-1].target_transition,
            DucTargetTransition.UNCHANGED,
        )

    def test_remove_objects_less_than_target_invalidates_index_proof(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "4")),
                ("up-set-target-object", ("search-local", "c:", "1")),
                ("up-remove-objects", ("search-local", "-1", "<", "1")),
            )),
        ))

        target = report.final_state.target
        self.assertIsNotNone(target)
        self.assertEqual(target.validity, DucTargetStatus.VALID)
        self.assertEqual(target.proof, DucTargetProof.CURRENT_PASS_PROOF)
        self.assertFalse(target.object_refs[0].index_stable)
        self.assertEqual(
            report.mutations[-1].target_transition,
            DucTargetTransition.UNCHANGED,
        )

    def test_remove_objects_provably_nonmatching_index_preserves_target(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "4")),
                ("up-set-target-object", ("search-local", "c:", "1")),
                ("up-remove-objects", ("search-local", "-1", "==", "0")),
            )),
        ))

        target = report.final_state.target
        self.assertIsNotNone(target)
        self.assertEqual(target.validity, DucTargetStatus.VALID)
        self.assertEqual(target.proof, DucTargetProof.CURRENT_PASS_PROOF)

    def test_remove_objects_non_index_property_makes_target_unknown(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "4")),
                ("up-set-target-object", ("search-local", "c:", "1")),
                ("up-remove-objects", ("search-local", "object-data-hitpoints", ">", "1")),
            )),
        ))

        target = report.final_state.target
        self.assertIsNotNone(target)
        self.assertEqual(target.validity, DucTargetStatus.UNKNOWN)
        self.assertEqual(target.proof, DucTargetProof.UNKNOWN)

    def test_remove_objects_index_match_after_sort_is_unknown(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "4")),
                ("up-set-target-object", ("search-local", "c:", "1")),
                ("up-clean-search", ("search-local", "object-data-hitpoints", "1")),
                ("up-remove-objects", ("search-local", "-1", "==", "1")),
            )),
        ))

        target = report.final_state.target
        self.assertIsNotNone(target)
        self.assertEqual(target.validity, DucTargetStatus.UNKNOWN)
        self.assertEqual(target.proof, DucTargetProof.UNKNOWN)
        self.assertFalse(target.object_refs[0].index_stable)
        self.assertEqual(
            report.mutations[-1].target_transition,
            DucTargetTransition.UNKNOWN,
        )



    def test_search_index_starts_at_zero_and_becomes_unknown_after_search(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
            )),
        ))

        initial = report.initial_state.local_list.search_index
        final = report.final_state.local_list.search_index
        self.assertEqual(initial.offset, 0)
        self.assertTrue(initial.known)
        self.assertEqual(initial.generation, 0)
        self.assertIsNone(final.offset)
        self.assertFalse(final.known)
        self.assertEqual(final.generation, 0)
        self.assertEqual(final.query_signature, ("c:", "villager", "c:", "1"))
        search = report.searches[0]
        self.assertEqual(search.index_before, 0)
        self.assertIsNone(search.index_after)
        self.assertIsNone(search.index_reset_reason)


    def test_find_local_fact_updates_search_state_and_keeps_fact_truth_runtime_dependent(self):
        report = analyze_duc((
            replace(
                _rule(1, (
                    ("up-get-search-state", ("41",)),
                )),
                facts=(
                    Expression(
                        "(up-find-local c: villager c: 1)",
                        "up-find-local",
                        ("c:", "villager", "c:", "1"),
                        SourceLocation(1, 1, "fixture.per"),
                    ),
                ),
            ),
        ))

        self.assertEqual(len(report.searches), 1)
        search = report.searches[0]
        self.assertEqual(search.source_kind, "FACT")
        self.assertEqual(search.fact_result, DucSearchFactResult.RUNTIME_DEPENDENT)
        self.assertEqual(search.cursor_after_disposition, DucSearchCursorDisposition.RUNTIME_ADVANCED)
        self.assertEqual(report.observations[0].local_search_cursor_disposition, DucSearchCursorDisposition.RUNTIME_ADVANCED)
        self.assertIsNotNone(report.final_state.local_list.current_generation)


    def test_find_remote_fact_updates_remote_cursor_and_can_be_reset_afterwards(self):
        report = analyze_duc((
            replace(
                _rule(1, (
                    ("up-reset-search", ("0", "0", "1", "0")),
                )),
                facts=(
                    Expression(
                        "(up-find-remote c: town-center c: 1)",
                        "up-find-remote",
                        ("c:", "town-center", "c:", "1"),
                        SourceLocation(1, 1, "fixture.per"),
                    ),
                ),
            ),
        ))

        search = report.searches[0]
        self.assertEqual(search.source_kind, "FACT")
        self.assertEqual(search.fact_result, DucSearchFactResult.RUNTIME_DEPENDENT)
        self.assertEqual(search.cursor_after_disposition, DucSearchCursorDisposition.RUNTIME_ADVANCED)
        self.assertEqual(
            report.final_state.remote_list.search_index.cursor_disposition,
            DucSearchCursorDisposition.RESET_START,
        )
        self.assertEqual(report.final_state.remote_list.search_index.offset, 0)


    def test_find_fact_at_known_end_is_guaranteed_false(self):
        first = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
            )),
        ))
        seed_index = replace(
            first.final_state.local_list.search_index,
            cursor_disposition=DucSearchCursorDisposition.AT_END,
            offset=None,
            known=False,
        )
        seed = replace(
            first.final_state,
            local_list=replace(
                first.final_state.local_list,
                search_index=seed_index,
            ),
        )

        report = analyze_duc((
            replace(
                _rule(1, (
                    ("up-get-search-state", ("41",)),
                )),
                facts=(
                    Expression(
                        "(up-find-local c: villager c: 1)",
                        "up-find-local",
                        ("c:", "villager", "c:", "1"),
                        SourceLocation(1, 1, "fixture.per"),
                    ),
                ),
            ),
        ), initial_state=seed)

        search = report.searches[0]
        self.assertEqual(search.source_kind, "FACT")
        self.assertEqual(search.result_disposition, DucSearchResultDisposition.GUARANTEED_EMPTY)
        self.assertEqual(search.fact_result, DucSearchFactResult.GUARANTEED_FALSE)
        self.assertEqual(search.cursor_before_disposition, DucSearchCursorDisposition.AT_END)
        self.assertEqual(search.cursor_after_disposition, DucSearchCursorDisposition.AT_END)
        self.assertEqual(report.observations[0].local_search_cursor_disposition, DucSearchCursorDisposition.AT_END)


    def test_branch_ambiguous_cursor_remains_ambiguous_after_later_search(self):
        rules = (
            _rule(1, (("up-jump-rule", ("1",)),)),
            _rule(2, (("up-find-local", ("c:", "villager", "c:", "1")),)),
            _rule(3, (("up-do-nothing", ()),)),
            _rule(4, (("up-find-local", ("c:", "villager", "c:", "1")),)),
        )
        report = analyze_duc(self._branched_execution(rules))

        search = report.searches[-1]
        self.assertEqual(
            search.cursor_before_disposition,
            DucSearchCursorDisposition.PATH_AMBIGUOUS,
        )
        self.assertEqual(
            search.cursor_after_disposition,
            DucSearchCursorDisposition.PATH_AMBIGUOUS,
        )
        self.assertEqual(
            report.final_state.local_list.search_index.cursor_disposition,
            DucSearchCursorDisposition.PATH_AMBIGUOUS,
        )
        self.assertTrue(report.final_state.local_list.path_ambiguous)


    def test_repeated_same_query_uses_prior_runtime_cursor_state(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-find-local", ("c:", "villager", "c:", "1")),
            )),
        ))

        first, second = report.searches
        self.assertEqual(first.cursor_after_disposition, DucSearchCursorDisposition.RUNTIME_ADVANCED)
        self.assertEqual(second.cursor_before_disposition, DucSearchCursorDisposition.RUNTIME_ADVANCED)
        self.assertIsNone(second.index_before)
        self.assertEqual(second.index_reset_reason, None)


    def test_search_records_runtime_cursor_transition(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
            )),
        ))

        search = report.searches[0]
        self.assertEqual(
            getattr(search, "cursor_after_disposition", None),
            "RUNTIME_ADVANCED",
        )
        self.assertEqual(
            getattr(report.final_state.local_list.search_index, "cursor_disposition", None),
            "RUNTIME_ADVANCED",
        )


    def test_get_search_state_observes_search_cursor_without_mutating_it(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-get-search-state", ("41",)),
            )),
        ))

        observation = report.observations[0]
        self.assertEqual(
            getattr(observation, "local_search_cursor_disposition", None),
            "RUNTIME_ADVANCED",
        )
        self.assertEqual(
            getattr(report.final_state.local_list.search_index, "cursor_disposition", None),
            "RUNTIME_ADVANCED",
        )


    def test_explicit_search_reset_restores_cursor_to_start(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-reset-search", ("1", "0", "0", "0")),
            )),
        ))

        self.assertEqual(
            getattr(report.final_state.local_list.search_index, "cursor_disposition", None),
            "RESET_START",
        )
        self.assertEqual(
            report.final_state.local_list.search_index.offset,
            0,
        )

    def test_search_at_proven_end_is_guaranteed_empty_and_does_not_rewind(self):
        first = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
            )),
        ))
        seed_index = replace(
            first.final_state.local_list.search_index,
            cursor_disposition=DucSearchCursorDisposition.AT_END,
            offset=None,
            known=False,
        )
        seed = replace(
            first.final_state,
            local_list=replace(
                first.final_state.local_list,
                search_index=seed_index,
            ),
        )

        report = analyze_duc(
            (
                _rule(1, (
                    ("up-find-local", ("c:", "villager", "c:", "1")),
                    ("up-get-search-state", ("41",)),
                )),
            ),
            initial_state=seed,
        )

        search = report.searches[0]
        self.assertEqual(search.result_disposition.value, "GUARANTEED_EMPTY")
        self.assertEqual(search.cursor_before_disposition.value, "AT_END")
        self.assertEqual(search.cursor_after_disposition.value, "AT_END")
        self.assertEqual(
            report.final_state.local_list.current_generation.last_search_cardinality,
            DucCardinalityRange(0, 0),
        )
        observation = report.observations[0]
        self.assertEqual(
            observation.local_search_cursor_disposition.value,
            "AT_END",
        )
        self.assertEqual(
            observation.local_last_search_cardinality,
            DucCardinalityRange(0, 0),
        )


    def test_search_on_full_destination_list_is_guaranteed_empty_and_cursor_blocked(self):
        first = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
            )),
        ))
        full_generation = replace(
            first.final_state.local_list.current_generation,
            cardinality=DucCardinalityRange(240, 240),
            last_search_cardinality=DucCardinalityRange(240, 240),
        )
        seed = replace(
            first.final_state,
            local_list=replace(
                first.final_state.local_list,
                current_generation=full_generation,
            ),
        )

        report = analyze_duc(
            (
                _rule(1, (
                    ("up-find-local", ("c:", "villager", "c:", "1")),
                )),
            ),
            initial_state=seed,
        )

        search = report.searches[0]
        self.assertEqual(search.result_disposition.value, "GUARANTEED_EMPTY")
        self.assertEqual(search.cursor_after_disposition.value, "BLOCKED_BY_CAPACITY")
        self.assertEqual(
            report.final_state.local_list.search_index.cursor_disposition.value,
            "BLOCKED_BY_CAPACITY",
        )
        self.assertEqual(
            report.final_state.local_list.current_generation.last_search_cardinality,
            DucCardinalityRange(0, 0),
        )


    def test_remote_cursor_advancement_and_focus_reset_are_independent(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("set-strategic-number", ("sn-focus-player-number", "2")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
            )),
        ))

        first, second = report.searches
        self.assertEqual(first.cursor_after_disposition.value, "RUNTIME_ADVANCED")
        self.assertEqual(
            second.index_reset_reason,
            DucSearchIndexResetReason.FOCUS_PLAYER_CHANGED,
        )
        self.assertEqual(
            second.cursor_before_disposition,
            DucSearchCursorDisposition.RESET_START,
        )
        self.assertEqual(second.focus_player_signature, "2")
        self.assertEqual(second.index_before, 0)
        self.assertEqual(
            second.cursor_after_disposition.value,
            "RUNTIME_ADVANCED",
        )


    def test_changed_local_query_signature_resets_local_search_index(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-find-local", ("c:", "archer-line", "c:", "1")),
            )),
        ))

        first, second = report.searches
        self.assertIsNone(first.index_after)
        self.assertEqual(second.index_before, 0)
        self.assertEqual(second.index_reset_reason.value, "QUERY_CHANGED")
        self.assertEqual(report.final_state.local_list.search_index.generation, 1)
        self.assertEqual(
            report.final_state.local_list.search_index.query_signature,
            ("c:", "archer-line", "c:", "1"),
        )


    def test_unchanged_local_query_does_not_spuriously_reset_index(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-find-local", ("c:", "villager", "c:", "1")),
            )),
        ))

        first, second = report.searches
        self.assertIsNone(first.index_reset_reason)
        self.assertIsNone(second.index_reset_reason)
        self.assertIsNone(second.index_after)


    def test_up_reset_search_can_reset_local_and_remote_indices_independently(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-reset-search", ("1", "0", "0", "0")),
            )),
            _rule(2, (
                ("up-reset-search", ("0", "0", "1", "0")),
            )),
        ))

        self.assertEqual(report.final_state.local_list.search_index.offset, 0)
        self.assertEqual(report.final_state.local_list.search_index.generation, 1)
        self.assertEqual(report.final_state.remote_list.search_index.offset, 0)
        self.assertEqual(report.final_state.remote_list.search_index.generation, 1)
        self.assertFalse(report.resets[0].invalidates_lists)
        self.assertEqual(report.resets[0].invalidates_local_index, True)
        self.assertEqual(report.resets[0].invalidates_remote_index, False)
        self.assertEqual(report.resets[1].invalidates_local_index, False)
        self.assertEqual(report.resets[1].invalidates_remote_index, True)


    def test_up_reset_filters_resets_both_indices_without_clearing_lists(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-reset-filters", ()),
            )),
        ))

        self.assertIsNotNone(report.final_state.local_list.current_generation)
        self.assertIsNotNone(report.final_state.remote_list.current_generation)
        self.assertEqual(report.final_state.local_list.search_index.offset, 0)
        self.assertEqual(report.final_state.remote_list.search_index.offset, 0)
        self.assertTrue(report.resets[-1].invalidates_local_index)
        self.assertTrue(report.resets[-1].invalidates_remote_index)


    def test_filter_distance_resets_both_search_indices_without_clearing_lists(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-filter-distance", ("c:", "0", "c:", "30")),
            )),
        ))

        self.assertIsNotNone(report.final_state.local_list.current_generation)
        self.assertIsNotNone(report.final_state.remote_list.current_generation)
        self.assertEqual(report.final_state.local_list.search_index.offset, 0)
        self.assertEqual(report.final_state.remote_list.search_index.offset, 0)


    def test_changed_remote_query_signature_resets_remote_search_index(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-find-remote", ("c:", "villager-class", "c:", "4")),
            )),
        ))

        first, second = report.searches
        self.assertIsNone(first.index_reset_reason)
        self.assertEqual(second.index_before, 0)
        self.assertEqual(second.index_reset_reason.value, "QUERY_CHANGED")


    def test_focus_player_search_index_starts_at_native_default(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
            )),
        ))

        index = report.final_state.remote_list.search_index
        self.assertEqual(index.focus_player_signature, "0")
        self.assertIsNone(index.focus_player_provenance)




    def test_search_index_state_survives_recurrent_loop_widening(self):
        rules = (
            _rule(1, (("up-find-local", ("c:", "villager", "c:", "1")),)),
            _rule(2, (("up-jump-rule", ("-1",)),)),
            _rule(3, (("up-do-nothing", ()),)),
        )
        execution = RuleExecutionReport(
            rules=rules,
            reachability=RuleReachabilityReport(
                reachable_rule_orders=(1, 2, 3),
                unreachable_rule_orders=(),
                incoming_rule_orders=((1, ()), (2, (1, 2)), (3, (2,))),
                outgoing_rule_orders=((1, (2,)), (2, (1, 3)), (3, ())),
            ),
        )

        report = analyze_duc(execution)
        loop_state = next(state for order, state in report.states if order == 1)
        index = loop_state.local_list.search_index
        self.assertFalse(index.known)
        self.assertEqual(index.query_signature, ("c:", "villager", "c:", "1"))
        self.assertTrue(index.path_ambiguous)




    def test_set_target_by_id_binds_native_object_identity(self):
        report = analyze_duc((
            _rule(1, (
                ("up-set-target-by-id", ("c:", "12345")),
            )),
        ))

        target = report.final_state.target
        self.assertIsNotNone(target)
        self.assertEqual(target.kind, DucTargetKind.OBJECT)
        self.assertEqual(target.object_refs[0].native_object_id, "12345")
        self.assertIsNone(target.object_refs[0].list_kind)
        self.assertIsNone(target.object_refs[0].list_generation)
        self.assertIsNone(target.object_refs[0].list_index)
        self.assertEqual(target.validity, DucTargetStatus.UNKNOWN)
        self.assertEqual(target.proof.value, "NATIVE_ID_PROOF")


    def test_direct_target_survives_search_resets_and_filter_resets(self):
        report = analyze_duc((
            _rule(1, (
                ("up-set-target-by-id", ("c:", "12345")),
                ("up-reset-search", ("1", "1", "1", "1")),
                ("up-reset-filters", ()),
            )),
        ))

        target = report.final_state.target
        self.assertIsNotNone(target)
        self.assertEqual(target.object_refs[0].native_object_id, "12345")
        self.assertEqual(target.validity, DucTargetStatus.UNKNOWN)
        self.assertEqual(target.proof.value, "NATIVE_ID_PROOF")


    def test_direct_target_survives_unrelated_list_mutations(self):
        report = analyze_duc((
            _rule(1, (
                ("up-set-target-by-id", ("c:", "12345")),
                ("up-find-local", ("c:", "villager", "c:", "4")),
                ("up-clean-search", ("search-local", "object-data-hitpoints", "1")),
                ("up-remove-objects", ("search-local", "-1", "==", "0")),
            )),
        ))

        target = report.final_state.target
        self.assertIsNotNone(target)
        self.assertEqual(target.object_refs[0].native_object_id, "12345")
        self.assertEqual(target.validity, DucTargetStatus.UNKNOWN)
        self.assertEqual(target.proof.value, "NATIVE_ID_PROOF")


    def test_same_native_id_branch_join_preserves_direct_identity(self):
        rules = (
            _rule(1, (("up-jump-rule", ("1",)),)),
            _rule(2, (("up-set-target-by-id", ("c:", "12345")),)),
            _rule(3, (("up-set-target-by-id", ("c:", "12345")),)),
            _rule(4, (("up-target-objects", ("0", "action-default", "-1", "-1")),)),
        )
        report = analyze_duc(self._branched_execution(rules))

        target = report.final_state.target
        self.assertIsNotNone(target)
        self.assertEqual(target.object_refs[0].native_object_id, "12345")
        self.assertEqual(target.validity, DucTargetStatus.UNKNOWN)
        self.assertEqual(target.proof.value, "NATIVE_ID_PROOF")


    def test_divergent_native_id_branch_join_widens_target_to_unknown(self):
        rules = (
            _rule(1, (("up-jump-rule", ("1",)),)),
            _rule(2, (("up-set-target-by-id", ("c:", "12345")),)),
            _rule(3, (("up-set-target-by-id", ("c:", "54321")),)),
            _rule(4, (("up-target-objects", ("0", "action-default", "-1", "-1")),)),
        )
        report = analyze_duc(self._branched_execution(rules))

        target = report.final_state.target
        self.assertIsNotNone(target)
        self.assertIsNone(target.object_refs[0].native_object_id)
        self.assertEqual(target.validity, DucTargetStatus.UNKNOWN)
        self.assertEqual(target.proof.value, "UNKNOWN")


    def test_symbolic_native_id_remains_unresolved(self):
        report = analyze_duc((
            _rule(1, (
                ("up-set-target-by-id", ("g:", "target-object-id")),
            )),
        ))

        target = report.final_state.target
        self.assertIsNotNone(target)
        self.assertIsNone(target.object_refs[0].native_object_id)
        self.assertEqual(target.validity, DucTargetStatus.UNKNOWN)
        self.assertEqual(target.proof.value, "UNKNOWN")


    def test_negative_native_id_is_rejected(self):
        report = analyze_duc((
            _rule(1, (
                ("up-set-target-by-id", ("c:", "-1")),
            )),
        ))

        self.assertTrue(any(
            item.code == "DUC-005"
            and "non-negative" in item.message
            for item in report.diagnostics
        ))
        self.assertIsNone(report.final_state.target)



    def test_direct_target_is_cleared_by_full_search_reset(self):
        report = analyze_duc((
            _rule(1, (
                ("up-set-target-by-id", ("c:", "12345")),
                ("up-full-reset-search", ()),
            )),
        ))

        self.assertIsNone(report.final_state.target)


    def test_direct_target_consumption_reports_liveness_boundary(self):
        report = analyze_duc((
            _rule(1, (
                ("up-set-target-by-id", ("c:", "12345")),
                ("up-target-objects", ("1", "action-default", "-1", "-1")),
            )),
        ))

        self.assertTrue(any(
            item.code == "DUC-007"
            and "liveness is unverified" in item.message
            for item in report.diagnostics
        ))




    def test_target_objects_option_zero_uses_local_list_without_selected_target(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "4")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-target-objects", ("0", "action-default", "-1", "-1")),
            )),
        ))

        self.assertIsNone(report.final_state.target)
        self.assertFalse(any(
            item.code == "DUC-005"
            and "up-target-objects" in item.message
            for item in report.diagnostics
        ))


    def test_target_objects_option_zero_requires_local_search_state(self):
        report = analyze_duc((
            _rule(1, (
                ("up-target-objects", ("0", "action-default", "-1", "-1")),
            )),
        ))

        self.assertTrue(any(
            item.code == "DUC-005"
            and "local" in item.message.lower()
            for item in report.diagnostics
        ))


    def test_target_objects_option_one_consumes_selected_object_target(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "4")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-set-target-object", ("search-remote", "c:", "0")),
                ("up-target-objects", ("1", "action-default", "-1", "-1")),
            )),
        ))

        self.assertFalse(any(
            item.code in {"DUC-005", "DUC-006"}
            and "up-target-objects" in item.message
            for item in report.diagnostics
        ))


    def test_target_objects_rejects_invalid_option(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "4")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-target-objects", ("2", "action-default", "-1", "-1")),
            )),
        ))

        self.assertTrue(any(
            item.code == "DUC-005"
            and "option" in item.message.lower()
            for item in report.diagnostics
        ))


    def test_sort_invalidates_list_index_target_before_selected_only_targeting(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "4")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-set-target-object", ("search-remote", "c:", "0")),
                ("up-clean-search", ("search-remote", "object-data-distance", "1")),
                ("up-target-objects", ("1", "action-default", "-1", "-1")),
            )),
        ))

        target = report.final_state.target
        self.assertIsNotNone(target)
        self.assertEqual(target.validity, DucTargetStatus.UNKNOWN)
        self.assertEqual(target.proof, DucTargetProof.UNKNOWN)
        self.assertTrue(any(
            item.code == "DUC-007"
            and "source-list identity" in item.message
            for item in report.diagnostics
        ))




    def test_target_objects_option_zero_records_local_search_consumer_effect(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "4")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-target-objects", ("0", "action-default", "-1", "-1")),
            )),
        ))

        self.assertEqual(len(report.target_consumers), 1)
        consumer = report.target_consumers[0]
        self.assertEqual(consumer.mode, DucTargetConsumerMode.LOCAL_SEARCH_RESULTS)
        self.assertEqual(consumer.local_list_generation, 1)
        self.assertEqual(consumer.remote_list_generation, 1)
        self.assertEqual(consumer.target_proof, DucTargetProof.UNKNOWN)


    def test_target_objects_option_one_records_selected_target_consumer_effect(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "4")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-set-target-object", ("search-remote", "c:", "0")),
                ("up-target-objects", ("1", "action-default", "-1", "-1")),
            )),
        ))

        self.assertEqual(len(report.target_consumers), 1)
        consumer = report.target_consumers[0]
        self.assertEqual(consumer.mode, DucTargetConsumerMode.SELECTED_OBJECT_ONLY)
        self.assertEqual(consumer.target_proof, DucTargetProof.CURRENT_PASS_PROOF)


    def test_target_objects_option_one_allows_direct_native_id_but_warns_liveness(self):
        report = analyze_duc((
            _rule(1, (
                ("up-set-target-by-id", ("c:", "12345")),
                ("up-target-objects", ("1", "action-default", "-1", "-1")),
            )),
        ))

        self.assertTrue(any(
            item.code == "DUC-007"
            and "liveness is unverified" in item.message
            for item in report.diagnostics
        ))
        self.assertEqual(
            report.target_consumers[0].target_proof,
            DucTargetProof.NATIVE_ID_PROOF,
        )


    def test_target_objects_option_zero_requires_local_search_but_not_selected_target(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-target-objects", ("0", "action-default", "-1", "-1")),
            )),
        ))

        self.assertTrue(any(
            item.code == "DUC-005"
            and "initialized local search list" in item.message
            for item in report.diagnostics
        ))





    def test_get_object_data_requires_selected_target(self):
        report = analyze_duc((
            _rule(1, (
                ("up-get-object-data", ("38", "41")),
            )),
        ))

        self.assertTrue(any(
            item.code == "DUC-005"
            and "up-get-object-data" in item.message
            and "target" in item.message
            for item in report.diagnostics
        ))


    def test_get_object_data_reads_current_selected_object_and_writes_goal_span(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-set-target-object", ("search-local", "c:", "0")),
                ("up-get-object-data", ("38", "41")),
            )),
        ))

        observation = report.target_data_observations[-1]
        self.assertEqual(observation.command, "up-get-object-data")
        self.assertEqual(observation.relation, DucTargetDataRelation.SELECTED_OBJECT)
        self.assertEqual(observation.source_kind, "ACTION")
        self.assertTrue(observation.writes_goal)
        self.assertEqual(observation.target_validity, DucTargetStatus.VALID)
        self.assertEqual(observation.target_proof, DucTargetProof.CURRENT_PASS_PROOF)
        self.assertEqual(observation.output_span.start_goal_id, 41)
        self.assertEqual(observation.output_span.width, 1)
        self.assertEqual(observation.output_span.generation, 1)
        self.assertEqual(observation.output_span.provenance.command, "up-get-object-data")
        self.assertEqual(report.final_state.goal_output_spans, (observation.output_span,))
        self.assertFalse(any(item.code in {"DUC-005", "DUC-006", "DUC-007"} for item in report.diagnostics))


    def test_object_data_fact_reads_current_selected_object(self):
        base = _rule(1, (
            ("up-find-local", ("c:", "villager", "c:", "1")),
            ("up-set-target-object", ("search-local", "c:", "0")),
        ))
        location = SourceLocation(1, 1, "fixture.per")
        fact = Expression(
            "(up-object-data 38 c:> 0)",
            "up-object-data",
            ("38", "c:>", "0"),
            location,
        )
        report = analyze_duc((
            replace(base, facts=(fact,)),
        ))

        observation = report.target_data_observations[0]
        self.assertEqual(observation.command, "up-object-data")
        self.assertEqual(observation.relation, DucTargetDataRelation.SELECTED_OBJECT)
        self.assertEqual(observation.source_kind, "FACT")
        self.assertFalse(observation.writes_goal)
        self.assertEqual(observation.target_validity, DucTargetStatus.UNKNOWN)
        self.assertEqual(observation.target_proof, DucTargetProof.UNKNOWN)
        self.assertTrue(any(
            item.code == "DUC-005"
            and "previously established object target" in item.message
            for item in report.diagnostics
        ))


    def test_get_object_target_data_exposes_runtime_target_of_target_boundary(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-set-target-object", ("search-local", "c:", "0")),
                ("up-get-object-target-data", ("38", "41")),
            )),
        ))

        observation = report.target_data_observations[-1]
        self.assertEqual(observation.relation, DucTargetDataRelation.SELECTED_OBJECT_TARGET)
        self.assertEqual(observation.target_validity, DucTargetStatus.VALID)
        self.assertEqual(observation.target_proof, DucTargetProof.CURRENT_PASS_PROOF)
        self.assertEqual(observation.output_span.provenance.command, "up-get-object-target-data")
        self.assertTrue(any(
            item.code == "DUC-007"
            and "target-of-target" in item.message
            for item in report.diagnostics
        ))


    def test_get_object_data_rejects_stale_selected_target(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-set-target-object", ("search-local", "c:", "0")),
                ("up-reset-search", ("1", "1", "0", "0")),
                ("up-get-object-data", ("38", "41")),
            )),
        ))

        self.assertTrue(any(
            item.code == "DUC-006"
            and "invalidated" in item.message
            for item in report.diagnostics
        ))
        self.assertEqual(
            report.target_data_observations[-1].target_validity,
            DucTargetStatus.STALE,
        )


    def test_get_object_data_preserves_native_id_liveness_boundary(self):
        report = analyze_duc((
            _rule(1, (
                ("up-set-target-by-id", ("c:", "12345")),
                ("up-get-object-data", ("38", "41")),
            )),
        ))

        observation = report.target_data_observations[-1]
        self.assertEqual(observation.target_proof, DucTargetProof.NATIVE_ID_PROOF)
        self.assertTrue(any(
            item.code == "DUC-007"
            and "liveness is unverified" in item.message
            for item in report.diagnostics
        ))


    def test_get_object_target_data_preserves_native_id_and_warns_target_of_target(self):
        report = analyze_duc((
            _rule(1, (
                ("up-set-target-by-id", ("c:", "12345")),
                ("up-get-object-target-data", ("38", "41")),
            )),
        ))

        observation = report.target_data_observations[-1]
        self.assertEqual(observation.target_proof, DucTargetProof.NATIVE_ID_PROOF)
        messages = [item.message for item in report.diagnostics if item.code == "DUC-007"]
        self.assertTrue(any("liveness is unverified" in message for message in messages))
        self.assertTrue(any("target-of-target" in message for message in messages))


    def test_get_object_data_goal_id_out_of_range_is_diagnostic(self):
        report = analyze_duc((
            _rule(1, (
                ("up-set-target-by-id", ("c:", "12345")),
                ("up-get-object-data", ("38", "16001")),
            )),
        ))

        self.assertTrue(any(
            item.code == "DUC-017"
            and "1..16000" in item.message
            for item in report.diagnostics
        ))
        self.assertIsNone(report.target_data_observations[-1].output_span)


    def test_get_object_data_overwrites_previous_goal_writer_with_provenance(self):
        report = analyze_duc((
            _rule(1, (
                ("up-set-target-by-id", ("c:", "12345")),
                ("up-get-object-data", ("38", "41")),
                ("up-get-object-data", ("39", "41")),
            )),
        ))

        first, second = report.target_data_observations[-2:]
        self.assertEqual(first.output_span.generation, 1)
        self.assertEqual(second.output_span.generation, 2)
        self.assertEqual(second.output_span.overwritten_generation, 1)
        self.assertEqual(
            second.output_span.overwritten_provenance.command,
            "up-get-object-data",
        )
        self.assertEqual(report.final_state.goal_output_spans, (second.output_span,))


    def test_get_object_data_fact_writes_goal_output_span(self):
        location = SourceLocation(1, 1, "fixture.per")
        fact = Expression(
            "(up-get-object-data 38 41)",
            "up-get-object-data",
            ("38", "41"),
            location,
        )
        report = analyze_duc((
            replace(_rule(1, ()), facts=(fact,)),
        ))

        observation = report.target_data_observations[0]
        self.assertEqual(observation.source_kind, "FACT")
        self.assertTrue(observation.writes_goal)
        self.assertEqual(report.final_state.goal_output_spans, (observation.output_span,))
        self.assertEqual(observation.output_span.provenance.command, "up-get-object-data")


    def test_cross_pass_target_data_reuse_warns_syntactic_retention(self):
        first = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-set-target-object", ("search-local", "c:", "0")),
            )),
        ))
        second = analyze_duc(
            (
                _rule(1, (
                    ("up-get-object-data", ("38", "41")),
                )),
            ),
            initial_state=first.next_pass_state,
        )

        self.assertEqual(
            second.target_data_observations[-1].target_proof,
            DucTargetProof.SYNTACTIC_RETENTION,
        )
        self.assertTrue(any(
            item.code == "DUC-007"
            and "retained across a pass" in item.message
            for item in second.diagnostics
        ))


    def test_object_target_data_fact_reads_current_object_target(self):
        first = _rule(1, (
            ("up-find-local", ("c:", "villager", "c:", "1")),
            ("up-set-target-object", ("search-local", "c:", "0")),
        ))
        location = SourceLocation(2, 1, "fixture.per")
        fact = Expression(
            "(up-object-target-data 38 c:> 0)",
            "up-object-target-data",
            ("38", "c:>", "0"),
            location,
        )
        report = analyze_duc((
            first,
            replace(_rule(2, ()), facts=(fact,)),
        ))

        observation = report.target_data_observations[-1]
        self.assertEqual(observation.command, "up-object-target-data")
        self.assertEqual(observation.relation, DucTargetDataRelation.SELECTED_OBJECT_TARGET)
        self.assertEqual(observation.source_kind, "FACT")
        self.assertFalse(observation.writes_goal)
        self.assertEqual(observation.target_validity, DucTargetStatus.VALID)
        self.assertTrue(any(
            item.code == "DUC-007"
            and "target-of-target" in item.message
            for item in report.diagnostics
        ))


    def test_get_object_target_data_fact_writes_goal_output_span(self):
        first = _rule(1, (
            ("up-find-local", ("c:", "villager", "c:", "1")),
            ("up-set-target-object", ("search-local", "c:", "0")),
        ))
        location = SourceLocation(2, 1, "fixture.per")
        fact = Expression(
            "(up-get-object-target-data 38 41)",
            "up-get-object-target-data",
            ("38", "41"),
            location,
        )
        report = analyze_duc((
            first,
            replace(_rule(2, ()), facts=(fact,)),
        ))

        observation = report.target_data_observations[-1]
        self.assertEqual(observation.command, "up-get-object-target-data")
        self.assertEqual(observation.source_kind, "FACT")
        self.assertTrue(observation.writes_goal)
        self.assertEqual(observation.output_span.start_goal_id, 41)
        self.assertEqual(report.final_state.goal_output_spans, (observation.output_span,))


    def test_query_change_reset_uses_shared_native_transition_contract(self):
        base = default_native_contract_catalog()
        query = replace(
            base.duc_search_index_transition("QUERY_CHANGE"),
            affected_lists=("REMOTE",),
        )
        catalog = NativeContractCatalog(
            duc_search_index_transitions=(
                query,
                *(
                    item
                    for item in base.duc_search_index_transitions
                    if item.trigger_kind != "QUERY_CHANGE"
                ),
            ),
        )
        report = analyze_duc(
            (
                _rule(
                    1,
                    (
                        ("up-find-local", ("c:", "villager", "c:", "1")),
                        ("up-find-local", ("c:", "archer", "c:", "1")),
                    ),
                ),
            ),
            contracts=catalog,
        )

        self.assertIsNone(report.searches[-1].index_reset_reason)
        self.assertEqual(report.final_state.local_list.search_index.generation, 0)

    def test_filter_change_reset_uses_shared_native_transition_contract(self):
        base = default_native_contract_catalog()
        filter_change = replace(
            base.duc_search_index_transition("FILTER_CHANGE"),
            affected_lists=("REMOTE",),
        )
        catalog = NativeContractCatalog(
            duc_search_index_transitions=(
                filter_change,
                *(
                    item
                    for item in base.duc_search_index_transitions
                    if item.trigger_kind != "FILTER_CHANGE"
                ),
            ),
        )
        report = analyze_duc(
            (
                _rule(
                    1,
                    (
                        ("up-find-local", ("c:", "villager", "c:", "1")),
                        ("up-filter-range", ("0", "100", "0", "100")),
                        ("up-find-local", ("c:", "villager", "c:", "1")),
                    ),
                ),
            ),
            contracts=catalog,
        )

        self.assertIsNone(report.searches[-1].index_reset_reason)
        self.assertEqual(report.final_state.local_list.search_index.generation, 0)

    def test_focus_player_reset_uses_shared_native_transition_contract(self):
        base = default_native_contract_catalog()
        focus_change = replace(
            base.duc_search_index_transition("FOCUS_PLAYER_CHANGE"),
            affected_lists=("LOCAL",),
        )
        catalog = NativeContractCatalog(
            duc_search_index_transitions=(
                focus_change,
                *(
                    item
                    for item in base.duc_search_index_transitions
                    if item.trigger_kind != "FOCUS_PLAYER_CHANGE"
                ),
            ),
        )
        report = analyze_duc(
            (
                _rule(
                    1,
                    (
                        ("up-find-remote", ("c:", "town-center", "c:", "1")),
                        ("set-strategic-number", ("sn-focus-player-number", "2")),
                        ("up-find-remote", ("c:", "town-center", "c:", "1")),
                    ),
                ),
            ),
            contracts=catalog,
        )

        self.assertIsNone(report.searches[-1].index_reset_reason)
        self.assertEqual(report.final_state.remote_list.search_index.generation, 0)

    def test_focus_player_change_resets_remote_search_index(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("set-strategic-number", ("sn-focus-player-number", "2")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
            )),
        ))

        first, second = report.searches
        self.assertIsNone(first.index_reset_reason)
        self.assertEqual(second.index_before, 0)
        self.assertEqual(
            second.index_reset_reason,
            DucSearchIndexResetReason.FOCUS_PLAYER_CHANGED,
        )
        self.assertEqual(second.focus_player_signature, "2")
        self.assertIsNotNone(second.focus_player_provenance)
        self.assertEqual(second.focus_player_provenance.command, "set-strategic-number")
        self.assertEqual(second.focus_player_provenance.within_rule_order, 1)
        self.assertEqual(report.final_state.remote_list.search_index.generation, 1)


    def test_same_focus_player_assignment_does_not_reset_remote_index(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("set-strategic-number", ("sn-focus-player-number", "0")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
            )),
        ))

        first, second = report.searches
        self.assertIsNone(first.index_reset_reason)
        self.assertIsNone(second.index_before)
        self.assertIsNone(second.index_reset_reason)
        self.assertEqual(second.focus_player_signature, "0")
        self.assertEqual(report.final_state.remote_list.search_index.generation, 0)
        self.assertEqual(
            second.focus_player_provenance.command,
            "set-strategic-number",
        )


    def test_up_modify_sn_constant_assignment_resets_remote_index_and_tracks_provenance(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("up-modify-sn", ("sn-focus-player-number", "c:=", "3")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
            )),
        ))

        search = report.searches[-1]
        self.assertEqual(search.index_before, 0)
        self.assertEqual(
            search.index_reset_reason,
            DucSearchIndexResetReason.FOCUS_PLAYER_CHANGED,
        )
        self.assertEqual(search.focus_player_signature, "3")
        self.assertEqual(search.focus_player_provenance.command, "up-modify-sn")
        self.assertEqual(search.focus_player_provenance.within_rule_order, 1)
        self.assertEqual(report.final_state.remote_list.search_index.generation, 1)


    def test_local_search_index_is_not_reset_by_focus_player_change(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("set-strategic-number", ("sn-focus-player-number", "2")),
                ("up-find-local", ("c:", "villager", "c:", "1")),
            )),
        ))

        first, second = report.searches
        self.assertIsNone(first.index_reset_reason)
        self.assertIsNone(second.index_reset_reason)
        self.assertIsNone(second.index_before)
        self.assertEqual(report.final_state.local_list.search_index.generation, 0)
        self.assertEqual(report.final_state.remote_list.search_index.focus_player_signature, "2")


    def test_dynamic_focus_player_mutation_resets_remote_index_but_preserves_unknown_value(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
                ("set-goal", ("focus-goal", "4")),
                ("up-modify-sn", ("sn-focus-player-number", "g:=", "focus-goal")),
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
            )),
        ))

        search = report.searches[-1]
        self.assertEqual(search.index_before, 0)
        self.assertEqual(
            search.index_reset_reason,
            DucSearchIndexResetReason.FOCUS_PLAYER_CHANGED,
        )
        self.assertIsNone(search.focus_player_signature)
        self.assertEqual(search.focus_player_provenance.command, "up-modify-sn")
        self.assertEqual(report.final_state.remote_list.search_index.generation, 1)


    def test_focus_player_provenance_survives_next_pass(self):
        first = analyze_duc((
            _rule(1, (
                ("set-strategic-number", ("sn-focus-player-number", "5")),
            )),
        ))
        second = analyze_duc((
            _rule(1, (
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
            )),
        ), initial_state=first.next_pass_state)

        self.assertEqual(
            second.final_state.remote_list.search_index.focus_player_signature,
            "5",
        )
        self.assertEqual(
            second.final_state.remote_list.search_index.focus_player_provenance.command,
            "set-strategic-number",
        )


    def test_branch_divergence_makes_focus_player_context_ambiguous(self):
        rules = (
            _rule(1, (("up-jump-rule", ("1",)),)),
            _rule(2, (
                ("set-strategic-number", ("sn-focus-player-number", "2")),
            )),
            _rule(3, (("up-do-nothing", ()),)),
            _rule(4, (
                ("up-find-remote", ("c:", "town-center", "c:", "1")),
            )),
        )
        execution = RuleExecutionReport(
            rules=rules,
            reachability=RuleReachabilityReport(
                reachable_rule_orders=(1, 2, 3, 4),
                unreachable_rule_orders=(),
                incoming_rule_orders=((1, ()), (2, (1,)), (3, (1,)), (4, (2, 3))),
                outgoing_rule_orders=((1, (2, 3)), (2, (4,)), (3, (4,)), (4, ())),
            ),
        )

        report = analyze_duc(execution)
        index = report.final_state.remote_list.search_index
        self.assertIsNone(index.focus_player_signature)
        self.assertTrue(index.path_ambiguous)
        self.assertIsNone(index.focus_player_provenance)



if __name__ == "__main__":
    unittest.main()

