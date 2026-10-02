"""Phase 2 (ROADMAP): DUC group-creation window inputs by stored goals.

Slice: MEASURE -> WINDOW end to end on the shared NativeDucGoalInputRequest
type (introduced for up-set-target-by-id reads).
- up-create-group takes bare goal operands at arguments 0 (window start)
  and 1 (window size) with no typeOp prefix, per the pinned native schema;
- an input request rewrites the operand to the writer output request's
  bound GoalSlot; without one the operand emits verbatim (literal window);
- writers are any same-plan GoalSlot outputs (here: up-get-group-size and
  up-get-object-data slots).

Hard invariants pinned here (community meta + engine contracts):
- groups are engine-managed storage, never Goal slots
  (AIREF_COMMUNITY_META_HYGIENE_CHECKLIST); group ids stay 0..19
  fail-closed; capacity stays 40;
- group membership and flag runtime values stay OPEN (no liveness,
  no member identity, no flag values asserted);
- up-set-group keeps its list-replacement + target-STALE side effects
  (validated post-emission, unchanged by this slice).
"""
import re
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.ast import Expression
from Compiler.compiler import compile_source
from Compiler.diagnostics import DiagnosticSeverity
from Compiler.ir.model import (
    GoalRole,
    GoalSlotRequest,
    SemanticId,
    StorageRequestId,
)
from Compiler.ir.native_duc import (
    NativeDucGoalInputRequest,
    NativeDucOutputRequest,
    NativeDucPlan,
    NativeDucRule,
)
from Compiler.primitives import default_de_registry
from Compiler.semantic.duc import analyze_duc
from Compiler.semantic.rule_diagnostics import analyze_rule_diagnostics
from Compiler.semantic.rule_execution import analyze_effective_rules
from Compiler.source_graph import SourceGraphRequest, SourceGraphResolver


def _e(source, head, *args):
    return Expression(source=source, head=head, args=args)


def _slot(owner_local, purpose):
    return GoalSlotRequest(
        StorageRequestId(SemanticId("test", owner_local), purpose),
        role=GoalRole.NATIVE_OUTPUT,
    )


def _measure_writer():
    return NativeDucOutputRequest(
        rule_identity="measure",
        section="ACTION",
        expression_index=3,
        request=_slot("window", "up-get-group-size"),
        command="up-get-group-size",
        argument_index=2,
    )


def _identity_writer():
    return NativeDucOutputRequest(
        rule_identity="measure",
        section="ACTION",
        expression_index=4,
        request=_slot("window", "up-get-object-data"),
        command="up-get-object-data",
        argument_index=1,
    )


def _group_plan(start_placeholder="0", size_placeholder="0", object_data="0"):
    measure = _measure_writer()
    identity = _identity_writer()
    return NativeDucPlan(
        rules=(
            NativeDucRule(
                identity="measure",
                order=0,
                facts=(_e("(true)", "true"),),
                actions=(
                    _e("(up-find-local c: 83 c: 1)", "up-find-local", "c:", "83", "c:", "1"),
                    _e("(up-set-target-object search-local c: 0)", "up-set-target-object", "search-local", "c:", "0"),
                    _e("(up-create-group 0 40 c: 0)", "up-create-group", "0", "40", "c:", "0"),
                    _e("(up-get-group-size c: 0 41)", "up-get-group-size", "c:", "0", "41"),
                    _e(f"(up-get-object-data {object_data} 41)", "up-get-object-data", object_data, "41"),
                ),
            ),
            NativeDucRule(
                identity="window",
                order=1,
                facts=(_e("(true)", "true"),),
                actions=(
                    _e(
                        "(up-create-group %s %s c: 1)" % (start_placeholder, size_placeholder),
                        "up-create-group",
                        str(start_placeholder),
                        str(size_placeholder),
                        "c:",
                        "1",
                    ),
                ),
            ),
            NativeDucRule(
                identity="micro",
                order=2,
                facts=(_e("(true)", "true"),),
                actions=(
                    _e("(up-set-group search-local c: 1)", "up-set-group", "search-local", "c:", "1"),
                    _e("(up-set-target-object search-local c: 0)", "up-set-target-object", "search-local", "c:", "0"),
                    _e("(up-target-objects 1 0 -1 -1)", "up-target-objects", "1", "0", "-1", "-1"),
                ),
            ),
        ),
        output_requests=(measure, identity),
        input_requests=(
            NativeDucGoalInputRequest(
                rule_identity="window",
                section="ACTION",
                expression_index=0,
                argument_index=0,
                source=measure.request.request_id,
            ),
            NativeDucGoalInputRequest(
                rule_identity="window",
                section="ACTION",
                expression_index=0,
                argument_index=1,
                source=identity.request.request_id,
            ),
        ),
    )


def _marker_source():
    return """
demand marker {
    require (can-train spearman)
    action (train spearman)
    witness (unit-type-count spearman >= 1)
    release (unit-type-count spearman >= 1)
}
"""


def _graph(source: str):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "root.per"
        path.write_text(source, encoding="utf-8")
        return SourceGraphResolver().resolve(
            SourceGraphRequest(entrypoint=path)
        )


class DucGroupInputTests(unittest.TestCase):
    def test_create_group_inputs_resolve_writer_slots(self):
        artifact = compile_source(_marker_source(), duc_plan=_group_plan())
        size_slot = re.search(
            r"\(up-get-group-size c: 0 (\d+)\)", artifact
        )
        id_slot = re.search(r"\(up-get-object-data 0 (\d+)\)", artifact)
        windowed = re.search(
            r"\(up-create-group (\d+) (\d+) c: 1\)", artifact
        )
        self.assertIsNotNone(size_slot)
        self.assertIsNotNone(id_slot)
        self.assertIsNotNone(windowed)
        self.assertEqual(windowed.group(1), size_slot.group(1))
        self.assertEqual(windowed.group(2), id_slot.group(1))
        # The literal first window is untouched.
        self.assertIn("(up-create-group 0 40 c: 0)", artifact)

    def test_create_group_inputs_deterministic_and_placeholder_independent(self):
        first = compile_source(_marker_source(), duc_plan=_group_plan())
        second = compile_source(_marker_source(), duc_plan=_group_plan())
        other = compile_source(
            _marker_source(), duc_plan=_group_plan("11", "22")
        )
        self.assertEqual(first, second)
        self.assertEqual(first, other)

    def test_object_data_operand_must_be_numeric(self):
        plan = _group_plan(object_data="object-data-id")
        with self.assertRaisesRegex(ValueError, "requires a numeric ObjectData"):
            default_de_registry().validate_duc_plan(plan)

    def test_input_wrong_command_rejected(self):
        plan = _group_plan()
        reader = NativeDucGoalInputRequest(
            rule_identity="micro",
            section="ACTION",
            expression_index=2,
            argument_index=1,
            source=plan.output_requests[0].request.request_id,
        )
        plan = NativeDucPlan(
            rules=plan.rules,
            output_requests=plan.output_requests,
            input_requests=(reader,),
        )
        with self.assertRaisesRegex(
            ValueError, "only up-set-target-by-id and up-create-group reads"
        ):
            default_de_registry().validate_duc_plan(plan)

    def test_input_typeop_position_rejected(self):
        plan = _group_plan()
        reader = NativeDucGoalInputRequest(
            rule_identity="window",
            section="ACTION",
            expression_index=0,
            argument_index=2,
            source=plan.output_requests[0].request.request_id,
        )
        plan = NativeDucPlan(
            rules=plan.rules,
            output_requests=plan.output_requests,
            input_requests=(reader,),
        )
        with self.assertRaisesRegex(ValueError, "must bind argument 0 or 1"):
            default_de_registry().validate_duc_plan(plan)

    def test_input_prefixed_operand_rejected(self):
        plan = NativeDucPlan(
            rules=(
                NativeDucRule(
                    identity="measure",
                    order=0,
                    facts=(_e("(true)", "true"),),
                    actions=(
                        _e("(up-get-group-size c: 0 41)", "up-get-group-size", "c:", "0", "41"),
                    ),
                ),
                NativeDucRule(
                    identity="window",
                    order=1,
                    facts=(_e("(true)", "true"),),
                    actions=(
                        _e("(up-create-group g: 0 c: 1)", "up-create-group", "g:", "0", "c:", "1"),
                    ),
                ),
            ),
            output_requests=(
                NativeDucOutputRequest(
                    rule_identity="measure",
                    section="ACTION",
                    expression_index=0,
                    request=_slot("window", "up-get-group-size"),
                    command="up-get-group-size",
                    argument_index=2,
                ),
            ),
            input_requests=(
                NativeDucGoalInputRequest(
                    rule_identity="window",
                    section="ACTION",
                    expression_index=0,
                    argument_index=0,
                    source=_slot("window", "up-get-group-size").request_id,
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "requires a bare goal operand"):
            default_de_registry().validate_duc_plan(plan)

    def test_input_without_writer_rejected(self):
        plan = _group_plan()
        orphan = NativeDucGoalInputRequest(
            rule_identity="window",
            section="ACTION",
            expression_index=0,
            argument_index=0,
            source=StorageRequestId(
                SemanticId("test", "no-such-writer"), "up-get-group-size"
            ),
        )
        plan = NativeDucPlan(
            rules=plan.rules,
            output_requests=plan.output_requests,
            input_requests=(orphan,),
        )
        with self.assertRaisesRegex(ValueError, "has no writer output request"):
            default_de_registry().validate_duc_plan(plan)

    def test_emitted_group_vertical_passes_semantic_diagnostics(self):
        artifact = compile_source(_marker_source(), duc_plan=_group_plan())
        start = artifact.index("; Native DUC rule: measure")
        end = artifact.index("; Per-pass transient action arbitration")
        execution = analyze_effective_rules(_graph(artifact[start:end]))
        duc = analyze_duc(execution)
        report = analyze_rule_diagnostics(execution, duc_report=duc)
        errors = tuple(
            item
            for item in report.diagnostics
            if item.severity is DiagnosticSeverity.ERROR
        )
        self.assertEqual(errors, ())


if __name__ == "__main__":
    unittest.main()
