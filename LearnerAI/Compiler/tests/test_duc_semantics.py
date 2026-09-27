import unittest
from dataclasses import replace

from Compiler.ir.duc import DucCardinalityRange, DucListKind, DucListMutationKind, DucLoopWidening, DucTargetProof, DucTargetStatus, DucTargetTransition
from Compiler.primitives import NativeContractCatalog, default_native_contract_catalog
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
        self.assertEqual(third.output_generation.cardinality.maximum, 240)
        self.assertNotEqual(first.output_generation.content_fingerprint, third.output_generation.content_fingerprint)

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
        self.assertEqual(target.validity, DucTargetStatus.VALID)
        self.assertEqual(target.proof, DucTargetProof.CURRENT_PASS_PROOF)
        mutation = report.mutations[-1]
        self.assertEqual(mutation.kind, DucListMutationKind.SORT)
        self.assertEqual(mutation.target_transition, DucTargetTransition.UNCHANGED)

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



if __name__ == "__main__":
    unittest.main()

