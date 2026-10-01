"""Phase 2 (ROADMAP): DUC target reacquisition by stored native identity.

Slice: DISCOVER -> STORE_ID -> REACQUIRE end to end.
- binder kind-coverage: a CONTRACTED Action-only mapping under a
  Fact/Action schema promotes Action emission (unblocks
  up-set-target-by-id and up-add-object-by-id); claiming a kind outside
  the schema stays rejected;
- goal-identity handoff: a NativeDucGoalInputRequest resolves a
  `g:`-operand read (up-set-target-by-id) to the writer output request's
  bound GoalSlot, so STORE_ID and REACQUIRE share one deterministic slot.

Hard invariants pinned here:
- Fact-position by-id stays rejected by semantics (DUC-005), not by the
  binder gate;
- the read never allocates storage and never invents an identity;
- target liveness stays advisory (DUC-007) on the emitted vertical;
- group-creation input allocation is explicitly out of scope.
"""
import re
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.ast import Expression, SourceLocation
from Compiler.compiler import compile_source
from Compiler.diagnostics import DiagnosticSeverity
from Compiler.ir.model import (
    GoalRole,
    GoalSlotRequest,
    GoalSpanKind,
    GoalSpanRequest,
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
from Compiler.primitives.engine_semantics import EngineSemanticMappingStatus
from Compiler.primitives.native_binder import (
    NativeSemanticBinder,
    NativeSupportState,
)
from Compiler.semantic.duc import analyze_duc
from Compiler.semantic.rule_diagnostics import analyze_rule_diagnostics
from Compiler.semantic.rule_execution import (
    EffectiveRule,
    RuleAction,
    RulePassBehavior,
)
from Compiler.source_graph import SourceGraphRequest, SourceGraphResolver

from Compiler.semantic.rule_execution import analyze_effective_rules


def _e(source, head, *args):
    return Expression(source=source, head=head, args=args)


def _binder():
    registry = default_de_registry()
    return NativeSemanticBinder(
        native_registry=registry._native,
        semantic_mappings=registry._semantic_mappings,
        native_contracts=registry.native_contracts,
        adapter_lookup=registry.get,
    )


def _slot(owner_local, purpose):
    return GoalSlotRequest(
        StorageRequestId(SemanticId("test", owner_local), purpose),
        role=GoalRole.NATIVE_OUTPUT,
    )


def _writer_request():
    return NativeDucOutputRequest(
        rule_identity="discover",
        section="ACTION",
        expression_index=2,
        request=_slot("reacquire", "up-get-object-data"),
        command="up-get-object-data",
        argument_index=1,
    )


def _reader_request(source):
    return NativeDucGoalInputRequest(
        rule_identity="reacquire",
        section="ACTION",
        expression_index=0,
        argument_index=1,
        source=source,
    )


def _vertical_plan(read_placeholder="0"):
    writer = _writer_request()
    return NativeDucPlan(
        rules=(
            NativeDucRule(
                identity="discover",
                order=0,
                facts=(_e("(true)", "true"),),
                actions=(
                    _e("(up-find-local c: 83 c: 1)", "up-find-local", "c:", "83", "c:", "1"),
                    _e("(up-set-target-object search-local c: 0)", "up-set-target-object", "search-local", "c:", "0"),
                    _e("(up-get-object-data id 41)", "up-get-object-data", "id", "41"),
                ),
            ),
            NativeDucRule(
                identity="reacquire",
                order=1,
                facts=(_e("(true)", "true"),),
                actions=(
                    _e(
                        "(up-set-target-by-id g: %s)" % read_placeholder,
                        "up-set-target-by-id",
                        "g:",
                        str(read_placeholder),
                    ),
                    _e("(up-target-objects 1 0 -1 -1)", "up-target-objects", "1", "0", "-1", "-1"),
                ),
            ),
        ),
        output_requests=(writer,),
        input_requests=(_reader_request(writer.request.request_id),),
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


class DucPromotionCoverageTests(unittest.TestCase):
    def test_action_only_mappings_promote_action_emission(self):
        binder = _binder()
        for name, params in (
            ("up-set-target-by-id", 2),
            ("up-add-object-by-id", 3),
        ):
            binding = binder.bind_duc_command(name)
            self.assertEqual(
                binding.support_state, NativeSupportState.EXECUTABLE_SAFE
            )
            self.assertEqual(binding.native_kind, "Fact/Action")
            self.assertEqual(binding.parameter_count, params)
            self.assertEqual(
                binding.mapping_status,
                EngineSemanticMappingStatus.CONTRACTED,
            )

    def test_contracted_mapping_kinds_stay_within_schema_kinds(self):
        registry = default_de_registry()
        over_claims = []
        for name in sorted(registry._native.names()):
            try:
                native = registry.require_native(name)
            except Exception:
                continue
            mapping = registry._semantic_mappings.for_command(name)
            if mapping is None:
                continue
            if mapping.status is not EngineSemanticMappingStatus.CONTRACTED:
                continue
            if not set(mapping.native_kind.split("/")) <= set(
                native.command_type.split("/")
            ):
                over_claims.append(name)
        self.assertEqual(over_claims, [])

    def test_mapping_claiming_outside_schema_stays_rejected(self):
        registry = default_de_registry()
        mappings = registry._semantic_mappings
        mapping = mappings.for_command("up-find-local")
        self.assertIsNotNone(mapping)
        # up-find-local contracts Fact/Action: checking it against a bare
        # Action schema kind must fail (subset direction is enforced).
        ok, message = mappings.validate_primitive(
            command="up-find-local",
            native_kind="Action",
            identity=mapping.identity,
        )
        self.assertFalse(ok)
        self.assertIn("outside contracted schema", message)

    def test_evidence_only_mappings_still_rejected(self):
        registry = default_de_registry()
        mappings = registry._semantic_mappings
        covered = 0
        for item in mappings.mappings:
            if item.status is not EngineSemanticMappingStatus.EVIDENCE_ONLY:
                continue
            # The status gate fires before any schema lookup: these mappings
            # name compiler-side evidence without a native schema entry.
            ok, message = mappings.validate_primitive(
                command=item.native_command,
                native_kind=item.native_kind,
                identity=item.identity,
            )
            self.assertFalse(ok)
            self.assertIn("evidence-only", message)
            covered += 1
        self.assertGreater(covered, 0)

    def test_fact_position_by_id_rejected_by_semantics(self):
        location = SourceLocation(1, 1, "fixture.per")
        rule = EffectiveRule(
            rule_order=1,
            source_location=location,
            source_slice_ordinal=0,
            instance_id="fixture:1",
            facts=(
                Expression(
                    "(up-set-target-by-id c: 12345)",
                    "up-set-target-by-id",
                    ("c:", "12345"),
                    location,
                ),
            ),
            actions=(),
            pass_behavior=RulePassBehavior.RECURRENT,
            disable_self_action_index=None,
        )
        report = analyze_duc((rule,))
        self.assertTrue(
            any(item.code == "DUC-005" for item in report.diagnostics)
        )


class DucGoalHandoffTests(unittest.TestCase):
    def test_input_without_writer_rejected(self):
        plan = _vertical_plan()
        orphan = NativeDucGoalInputRequest(
            rule_identity="reacquire",
            section="ACTION",
            expression_index=0,
            argument_index=1,
            source=StorageRequestId(
                SemanticId("test", "no-such-writer"), "up-get-object-data"
            ),
        )
        plan = NativeDucPlan(
            rules=plan.rules,
            output_requests=plan.output_requests,
            input_requests=(orphan,),
        )
        with self.assertRaisesRegex(ValueError, "has no writer output request"):
            default_de_registry().validate_duc_plan(plan)

    def test_input_wrong_command_rejected(self):
        plan = _vertical_plan()
        reader = NativeDucGoalInputRequest(
            rule_identity="reacquire",
            section="ACTION",
            expression_index=1,
            argument_index=1,
            source=plan.output_requests[0].request.request_id,
        )
        plan = NativeDucPlan(
            rules=plan.rules,
            output_requests=plan.output_requests,
            input_requests=(reader,),
        )
        with self.assertRaisesRegex(ValueError, "only up-set-target-by-id and up-create-group reads"):
            default_de_registry().validate_duc_plan(plan)

    def test_input_non_goal_operand_rejected(self):
        writer = NativeDucOutputRequest(
            rule_identity="discover",
            section="ACTION",
            expression_index=0,
            request=_slot("reacquire", "up-get-object-data"),
            command="up-get-object-data",
            argument_index=1,
        )
        plan = NativeDucPlan(
            rules=(
                NativeDucRule(
                    identity="discover",
                    order=0,
                    facts=(_e("(true)", "true"),),
                    actions=(
                        _e("(up-get-object-data id 41)", "up-get-object-data", "id", "41"),
                    ),
                ),
                NativeDucRule(
                    identity="reacquire",
                    order=1,
                    facts=(_e("(true)", "true"),),
                    actions=(
                        _e("(up-set-target-by-id c: 5)", "up-set-target-by-id", "c:", "5"),
                    ),
                ),
            ),
            output_requests=(writer,),
            input_requests=(
                NativeDucGoalInputRequest(
                    rule_identity="reacquire",
                    section="ACTION",
                    expression_index=0,
                    argument_index=1,
                    source=writer.request.request_id,
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "requires a literal g: typeOp"):
            default_de_registry().validate_duc_plan(plan)

    def test_input_span_writer_rejected(self):
        span_request = GoalSpanRequest(
            request_id=StorageRequestId(
                SemanticId("test", "reacquire"), "up-get-search-state"
            ),
            width=4,
            shape=GoalSpanKind.EXTENDED_4,
            contract_id="up-get-search-state.OutputGoalId",
            start_min=41,
            start_max=15996,
            role=GoalRole.NATIVE_OUTPUT,
        )
        writer = NativeDucOutputRequest(
            rule_identity="discover",
            section="ACTION",
            expression_index=0,
            request=span_request,
            command="up-get-search-state",
            argument_index=0,
        )
        plan = NativeDucPlan(
            rules=(
                NativeDucRule(
                    identity="discover",
                    order=0,
                    facts=(_e("(true)", "true"),),
                    actions=(
                        _e("(up-get-search-state 41)", "up-get-search-state", "41"),
                    ),
                ),
                NativeDucRule(
                    identity="reacquire",
                    order=1,
                    facts=(_e("(true)", "true"),),
                    actions=(
                        _e("(up-set-target-by-id g: 0)", "up-set-target-by-id", "g:", "0"),
                    ),
                ),
            ),
            output_requests=(writer,),
            input_requests=(
                NativeDucGoalInputRequest(
                    rule_identity="reacquire",
                    section="ACTION",
                    expression_index=0,
                    argument_index=1,
                    source=span_request.request_id,
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "writer is not a GoalSlot"):
            default_de_registry().validate_duc_plan(plan)

    def test_duplicate_input_site_rejected(self):
        writer = _writer_request()
        with self.assertRaisesRegex(ValueError, "duplicate native DUC input request site"):
            NativeDucPlan(
                rules=_vertical_plan().rules,
                output_requests=(writer,),
                input_requests=(
                    _reader_request(writer.request.request_id),
                    _reader_request(writer.request.request_id),
                ),
            )

    def test_input_output_site_collision_rejected(self):
        writer = _writer_request()
        with self.assertRaisesRegex(ValueError, "collides with an output request site"):
            NativeDucPlan(
                rules=_vertical_plan().rules,
                output_requests=(writer,),
                input_requests=(
                    NativeDucGoalInputRequest(
                        rule_identity="discover",
                        section="ACTION",
                        expression_index=2,
                        argument_index=1,
                        source=writer.request.request_id,
                    ),
                ),
            )


class DucReacquisitionVerticalTests(unittest.TestCase):
    def test_vertical_resolves_shared_slot(self):
        artifact = compile_source(_marker_source(), duc_plan=_vertical_plan())
        written = re.search(
            r"\(up-get-object-data id (\d+)\)", artifact
        )
        read = re.search(r"\(up-set-target-by-id g: (\d+)\)", artifact)
        self.assertIsNotNone(written)
        self.assertIsNotNone(read)
        self.assertEqual(written.group(1), read.group(1))
        self.assertIn("(up-find-local c: 83 c: 1)", artifact)
        self.assertIn("(up-set-target-object search-local c: 0)", artifact)
        self.assertIn("(up-target-objects 1 0 -1 -1)", artifact)

    def test_vertical_is_deterministic_and_placeholder_independent(self):
        first = compile_source(_marker_source(), duc_plan=_vertical_plan("0"))
        second = compile_source(_marker_source(), duc_plan=_vertical_plan("0"))
        other = compile_source(_marker_source(), duc_plan=_vertical_plan("7777"))
        self.assertEqual(first, second)
        self.assertEqual(first, other)

    def test_emitted_vertical_passes_semantic_diagnostics(self):
        artifact = compile_source(_marker_source(), duc_plan=_vertical_plan())
        start = artifact.index("; Native DUC rule: discover")
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
        # Liveness of the reacquired native ID stays advisory: the compiler
        # resolves identity, never proves the object is alive.
        advisory = tuple(
            item
            for item in report.diagnostics
            if item.code.value == "DUC-007"
        )
        self.assertTrue(advisory)


if __name__ == "__main__":
    unittest.main()
