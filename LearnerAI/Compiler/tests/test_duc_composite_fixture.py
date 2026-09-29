import unittest

from Compiler.ast import Expression, SourceLocation
from Compiler.ir.duc import (
    DucListMutationKind,
    DucTargetProof,
    DucTargetStatus,
    DucTargetTransition,
)
from Compiler.semantic.duc import analyze_duc
from Compiler.semantic.recurrent_execution import (
    RecurrentExecutionStatus,
    analyze_recurrent_execution,
)
from Compiler.semantic.rule_execution import (
    EffectiveRule,
    RuleAction,
    RuleExecutionReport,
    RulePassBehavior,
    RuleReachabilityReport,
)


def _rule(order, *, facts=(), actions=()):
    location = SourceLocation(order, 1, "duc-composite.per")
    return EffectiveRule(
        rule_order=order,
        source_location=location,
        source_slice_ordinal=0,
        instance_id=f"duc-composite:{order}",
        facts=tuple(
            Expression(source, head, tuple(args), location)
            for source, head, args in facts
        ),
        actions=tuple(
            RuleAction(
                expression=Expression(source, head, tuple(args), location),
                within_rule_order=index,
            )
            for index, (source, head, args) in enumerate(actions)
        ),
        pass_behavior=RulePassBehavior.RECURRENT,
        disable_self_action_index=None,
    )


def composite_recurrent_mutation_branch_target_fixture():
    rules = (
        _rule(
            1,
            facts=(("(true)", "true", ()),),
            actions=(
                ("(set-goal duc-gate 0)", "set-goal", ("duc-gate", "0")),
                ("(up-jump-rule 3)", "up-jump-rule", ("3",)),
            ),
        ),
        _rule(
            2,
            facts=(
                (
                    "(up-compare-goal duc-gate c:== 1)",
                    "up-compare-goal",
                    ("duc-gate", "c:==", "1"),
                ),
            ),
            actions=(
                (
                    "(up-find-local c: villager c: 1)",
                    "up-find-local",
                    ("c:", "villager", "c:", "1"),
                ),
            ),
        ),
        _rule(
            3,
            facts=(("(true)", "true", ()),),
            actions=(
                (
                    "(up-find-local c: villager c: 1)",
                    "up-find-local",
                    ("c:", "villager", "c:", "1"),
                ),
            ),
        ),
        _rule(
            4,
            facts=(("(true)", "true", ()),),
            actions=(
                (
                    "(up-set-target-object search-local c: 0)",
                    "up-set-target-object",
                    ("search-local", "c:", "0"),
                ),
            ),
        ),
        _rule(
            5,
            facts=(("(true)", "true", ()),),
            actions=(
                (
                    "(up-clean-search search-local object-data-hitpoints 1)",
                    "up-clean-search",
                    ("search-local", "object-data-hitpoints", "1"),
                ),
            ),
        ),
        _rule(
            6,
            facts=(("(true)", "true", ()),),
            actions=(
                (
                    "(up-set-target-object search-local c: 0)",
                    "up-set-target-object",
                    ("search-local", "c:", "0"),
                ),
            ),
        ),
        _rule(
            7,
            facts=(("(true)", "true", ()),),
            actions=(
                (
                    "(up-remove-objects search-local -1 > 1)",
                    "up-remove-objects",
                    ("search-local", "-1", ">", "1"),
                ),
            ),
        ),
        _rule(
            8,
            facts=(("(true)", "true", ()),),
            actions=(
                (
                    "(up-set-target-object search-local c: 0)",
                    "up-set-target-object",
                    ("search-local", "c:", "0"),
                ),
            ),
        ),
        _rule(
            9,
            facts=(("(true)", "true", ()),),
            actions=(
                (
                    "(up-remove-objects search-local -1 == 0)",
                    "up-remove-objects",
                    ("search-local", "-1", "==", "0"),
                ),
            ),
        ),
        _rule(
            10,
            facts=(("(true)", "true", ()),),
            actions=(
                (
                    "(up-target-objects 1 action-default -1 -1)",
                    "up-target-objects",
                    ("1", "action-default", "-1", "-1"),
                ),
            ),
        ),
    )

    reachability = RuleReachabilityReport(
        reachable_rule_orders=tuple(range(1, 11)),
        unreachable_rule_orders=(),
        incoming_rule_orders=(
            (1, ()),
            (2, (1,)),
            (3, (1, 2)),
            *((order, (order - 1,)) for order in range(4, 11)),
        ),
        outgoing_rule_orders=(
            (1, (2, 3)),
            (2, (3,)),
            *((order, (order + 1,)) for order in range(3, 10)),
            (10, ()),
        ),
    )
    return RuleExecutionReport(rules=rules, reachability=reachability)


class CompositeDucFixtureTests(unittest.TestCase):
    def test_composite_fixture_covers_recurrent_branch_mutation_and_target_lifetime(self):
        execution = composite_recurrent_mutation_branch_target_fixture()
        recurrent = analyze_recurrent_execution(execution)

        self.assertEqual(
            recurrent.status_for_rule(2),
            RecurrentExecutionStatus.NEVER_RUNNABLE,
        )

        report = analyze_duc(execution, recurrent_execution=recurrent)

        self.assertEqual(
            len(report.searches),
            1,
            "unreachable recurrent branch must not seed a second DUC search",
        )
        self.assertEqual(report.searches[0].provenance.rule_order, 3)

        join = next(
            merge for merge in report.branch_merges if merge.rule_order == 3
        )
        self.assertEqual(join.predecessor_rule_orders, (1, 2))
        self.assertEqual(join.state_variants, 1)

        clean = report.mutations[1]
        self.assertEqual(clean.kind, DucListMutationKind.SORT)
        self.assertEqual(clean.target_transition, DucTargetTransition.UNKNOWN)

        after_clean = next(
            state for order, state in report.states if order == 5
        )
        self.assertEqual(after_clean.target.validity, DucTargetStatus.UNKNOWN)
        self.assertEqual(after_clean.target.proof, DucTargetProof.UNKNOWN)

        preserved = report.mutations[2]
        self.assertEqual(preserved.kind, DucListMutationKind.REMOVE_MATCHES)
        self.assertEqual(
            preserved.target_transition,
            DucTargetTransition.UNCHANGED,
        )

        stale = report.mutations[4]
        self.assertEqual(stale.kind, DucListMutationKind.REMOVE_MATCHES)
        self.assertEqual(stale.target_transition, DucTargetTransition.STALE)

        final_target = report.final_state.target
        self.assertIsNotNone(final_target)
        self.assertEqual(final_target.validity, DucTargetStatus.STALE)
        self.assertTrue(
            any(
                diagnostic.code == "DUC-006"
                and diagnostic.rule_order == 10
                and "up-target-objects" in diagnostic.message
                for diagnostic in report.diagnostics
            )
        )


if __name__ == "__main__":
    unittest.main()
