import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from Compiler.ast import SourceLocation
from Compiler.ir import (
    CleanupStatus,
    CompletionWitnessContract,
    SemanticId,
    WitnessEvidenceKind,
)
from Compiler.diagnostics import DiagnosticSeverity
from Compiler.semantic.rule_diagnostics import (
    RuleDiagnosticCategory,
    RuleDiagnosticCode,
    analyze_rule_diagnostics,
)
from Compiler.ir import PersistentControlCleanupObligation, PersistentControlId, PersistentControlKind, PersistentControlLifetime, PersistentControlRef
from Compiler.semantic.persistent_control import PersistentControlDiagnostic, PersistentControlDiagnosticCode, PersistentControlReport, PersistentControlStatus
from Compiler.semantic.persistent_state import (
    PersistentStateDiagnosticCode,
    analyze_persistent_state,
)
from Compiler.semantic.recurrent_execution import analyze_recurrent_execution
from Compiler.semantic.strategic_number_semantics import (
    StrategicNumberDiagnosticCode,
    analyze_strategic_number_expressions,
)
from Compiler.semantic.duc import analyze_duc
from Compiler.semantic.rule_execution import analyze_effective_rules
from Compiler.source_graph import SourceGraphRequest, SourceGraphResolver


class RuleDiagnosticsTests(unittest.TestCase):
    def _graph(self, source: str):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "root.per"
            path.write_text(source, encoding="utf-8")
            return SourceGraphResolver().resolve(
                SourceGraphRequest(entrypoint=path)
            )

    def _witness(self):
        return CompletionWitnessContract(
            identity=SemanticId("<test>", "demand"),
            evidence_kind=WitnessEvidenceKind.WORLD_STATE,
            primitive="building-type-count-total",
            expression=analyze_effective_rules.__annotations__.get(
                "return"
            ) if False else __import__("Compiler.semantic.analyzer", fromlist=["parse_expression"]).parse_expression(
                "(true)",
                SourceLocation(2, 1, "<test>"),
            ),
            establishes=SemanticId("<test>", "demand"),
            source_order=1,
            issuance_source_order=3,
            location=SourceLocation(2, 1, "<test>"),
        )

    def test_persistent_control_diagnostic_converts_through_rule_taxonomy(self):
        execution = analyze_effective_rules(
            self._graph("(defrule (true) => (disable-self))\n")
        )
        control = PersistentControlRef(
            id=PersistentControlId("<test>", "timer:cooldown"),
            kind=PersistentControlKind.TIMER,
            owner=SemanticId("<test>", "demand"),
            lifetime=PersistentControlLifetime.UNTIL_OWNER_RELEASE,
        )
        finding = PersistentControlDiagnostic(
            code=PersistentControlDiagnosticCode.RELEASE_MISSING,
            status=PersistentControlStatus.BLOCKED,
            severity=DiagnosticSeverity.WARNING,
            message="timer 'timer:cooldown' has no explicit cleanup after owner release",
            control=control.id,
            owner=control.owner,
            location=SourceLocation(1, 1, "<test>"),
        )
        report = PersistentControlReport(
            controls=(control,),
            obligations=(
                PersistentControlCleanupObligation(
                    control=control.id,
                    owner=control.owner,
                    release_contract=SemanticId("<test>", "demand-release"),
                    status=CleanupStatus.REQUIRED,
                ),
            ),
            diagnostics=(finding,),
        )

        diagnostics = analyze_rule_diagnostics(
            execution,
            persistent_control_report=report,
        )
        bridged = next(
            item
            for item in diagnostics.diagnostics
            if item.code is RuleDiagnosticCode.PERSISTENT_CONTROL_RELEASE_MISSING
        )

        self.assertEqual(bridged.category, RuleDiagnosticCategory.PERSISTENT_CONTROL)
        self.assertEqual(bridged.source_code, "PCONTROL-002")
        self.assertEqual(bridged.severity, DiagnosticSeverity.WARNING)
        self.assertEqual(bridged.state_kind, "timer")
        self.assertEqual(bridged.state_identifier, "cooldown")
        self.assertEqual(bridged.related_operation, "persistent-control")

    def test_duc_group_invalid_state_diagnostic_converts_through_rule_taxonomy(self):
        execution = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (up-set-group search-remote c: 99))\n"
            )
        )
        duc = analyze_duc(execution)
        self.assertTrue(any(item.code == "DUC-017" for item in duc.diagnostics))

        report = analyze_rule_diagnostics(execution, duc_report=duc)
        diagnostic = next(
            item for item in report.diagnostics
            if item.code.value == "DUC-017"
        )
        self.assertEqual(diagnostic.category, RuleDiagnosticCategory.DUC)
        self.assertEqual(diagnostic.source_code, "DUC-017")

    def test_duc_cross_rule_target_warning_carries_related_provenance(self):
        execution = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (up-set-target-by-id c: 12345))\\n"
                "(defrule (true) => (up-target-objects 1 action-default -1 -1))\\n"
            )
        )

        duc = analyze_duc(execution)
        finding = next(
            item
            for item in duc.diagnostics
            if item.code == "DUC-007"
            and item.rule_order == 2
            and "liveness is unverified" in item.message
        )

        self.assertEqual(finding.related_rule_order, 1)
        self.assertEqual(finding.related_operation, "up-set-target-by-id")
        self.assertEqual(finding.state_kind, "TARGET")
        self.assertTrue(finding.state_identifier.startswith("object-generation:"))

        diagnostics = analyze_rule_diagnostics(execution, duc_report=duc)
        bridged = next(
            item
            for item in diagnostics.diagnostics
            if item.code is RuleDiagnosticCode.DUC_TARGET_UNKNOWN
            and item.rule_order == 2
        )

        self.assertEqual(bridged.related_rule_order, 1)
        self.assertEqual(bridged.related_operation, "up-set-target-by-id")
        self.assertEqual(bridged.state_kind, "TARGET")
        self.assertEqual(bridged.state_identifier, finding.state_identifier)

    def test_duc_loop_widening_maps_to_rule_diagnostic(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (up-find-remote c: town-center c: 1))\\n"
                "(defrule (true) => (up-find-local c: villager c: 1))\\n"
                "(defrule (true) => (up-jump-rule -2))\\n"
                "(defrule (true) => (up-target-objects 1 action-default -1 -1))\\n"
            )
        )

        duc_report = analyze_duc(report)
        diagnostics = analyze_rule_diagnostics(report, duc_report=duc_report)

        finding = next(
            item for item in diagnostics.diagnostics
            if item.code is RuleDiagnosticCode.DUC_LOOP_WIDENING
        )
        self.assertEqual(finding.rule_order, 3)
        self.assertEqual(finding.severity, DiagnosticSeverity.WARNING)
        self.assertEqual(finding.category.value, "DUC")
        self.assertEqual(finding.source_code, "DUC-016")
        self.assertIn("loop head 2", finding.message)
        self.assertIn("back-edge source 3", finding.message)
        self.assertIn("iteration bound 3", finding.message)
        self.assertIn("widened fields: LOCAL_LIST", finding.message)

    def test_jump_into_disabled_rule_gets_control_flow_warning(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (disable-self) (up-jump-rule -1))\n"
                "(defrule (true) => (set-goal successor 1))\n"
            )
        )

        diagnostics = analyze_rule_diagnostics(report)

        finding = next(
            item
            for item in diagnostics.diagnostics
            if item.code.value == "RULE-CF-005"
        )
        self.assertEqual(finding.rule_order, 1)
        self.assertEqual(finding.severity, DiagnosticSeverity.WARNING)
        self.assertEqual(finding.related_rule_order, 1)
        self.assertEqual(finding.related_operation, "up-jump-rule")
        self.assertIn("disabled", finding.message)
        self.assertEqual(finding.category.value, "CONTROL_FLOW")

    def test_jump_before_disable_self_does_not_report_disabled_target(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (up-jump-rule -1) (disable-self))\n"
                "(defrule (true) => (set-goal successor 1))\n"
            )
        )

        diagnostics = analyze_rule_diagnostics(report)

        self.assertFalse(
            any(
                item.code.value == "RULE-CF-005"
                for item in diagnostics.diagnostics
            )
        )

    def test_forward_control_transfer_gets_bypass_diagnostic(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (up-jump-rule 1))\n"
                "(defrule (true) => (set-goal skipped 1))\n"
                "(defrule (true) => (set-goal reached 1))\n"
            )
        )

        diagnostics = analyze_rule_diagnostics(report)

        finding = next(
            item
            for item in diagnostics.diagnostics
            if item.code is RuleDiagnosticCode.CONTROL_TRANSFER_BYPASSES_RULE
        )
        self.assertEqual(finding.rule_order, 1)
        self.assertEqual(finding.severity, DiagnosticSeverity.INFO)
        self.assertEqual(finding.related_rule_order, 3)
        self.assertEqual(finding.related_operation, "up-jump-rule")
        self.assertEqual(finding.category.value, "CONTROL_FLOW")

    def test_out_of_range_control_transfer_gets_error_diagnostic(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (up-jump-rule 3))\n"
            )
        )

        diagnostics = analyze_rule_diagnostics(report)

        self.assertEqual(len(diagnostics.errors), 1)
        finding = diagnostics.errors[0]
        self.assertEqual(finding.code, RuleDiagnosticCode.CONTROL_TRANSFER_OUT_OF_RANGE)
        self.assertEqual(finding.rule_order, 1)
        self.assertEqual(finding.severity, DiagnosticSeverity.ERROR)
        self.assertIsNone(finding.related_rule_order)
        self.assertEqual(finding.related_operation, "up-jump-rule")
        self.assertEqual(finding.category.value, "CONTROL_FLOW")
    def test_never_eligible_rule_gets_error_diagnostic(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (false) => (set-goal dead 1))\n"
            )
        )

        diagnostics = analyze_rule_diagnostics(report)

        self.assertEqual(len(diagnostics.diagnostics), 1)
        diagnostic = diagnostics.diagnostics[0]
        self.assertEqual(diagnostic.rule_order, 1)
        self.assertEqual(
            diagnostic.code,
            RuleDiagnosticCode.NEVER_ELIGIBLE,
        )
        self.assertEqual(diagnostic.severity, DiagnosticSeverity.ERROR)
        self.assertEqual(diagnostic.eligibility.value, "NEVER_ELIGIBLE")

    def test_unknown_guard_gets_runtime_dependent_diagnostic(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (current-age >= castle-age) => (set-goal maybe 1))\n"
            )
        )

        diagnostics = analyze_rule_diagnostics(report)

        diagnostic = diagnostics.diagnostics[0]
        self.assertEqual(
            diagnostic.code,
            RuleDiagnosticCode.RUNTIME_DEPENDENT,
        )
        self.assertEqual(
            diagnostic.eligibility.value,
            "RUNTIME_DEPENDENT",
        )
        self.assertEqual(diagnostic.severity, DiagnosticSeverity.INFO)

    def test_recurrent_eligible_rule_gets_info_diagnostic(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (set-goal recurring 1))\n"
            )
        )

        diagnostics = analyze_rule_diagnostics(report)

        diagnostic = diagnostics.diagnostics[0]
        self.assertEqual(
            diagnostic.code,
            RuleDiagnosticCode.RECURRENTLY_ELIGIBLE,
        )
        self.assertEqual(
            diagnostic.eligibility.value,
            "RECURRENTLY_ELIGIBLE",
        )
        self.assertEqual(diagnostic.severity, DiagnosticSeverity.INFO)

    def test_one_shot_rule_gets_first_pass_diagnostic(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (set-goal once 1) (disable-self))\n"
            )
        )

        diagnostics = analyze_rule_diagnostics(report)

        diagnostic = diagnostics.diagnostics[0]
        self.assertEqual(
            diagnostic.code,
            RuleDiagnosticCode.FIRST_PASS_ELIGIBLE,
        )
        self.assertEqual(
            diagnostic.eligibility.value,
            "FIRST_PASS_ELIGIBLE",
        )

    def test_runtime_demand_state_and_witness_are_forwarded_to_eligibility(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (set-goal demand 1))\n"
            )
        )

        diagnostics = analyze_rule_diagnostics(
            report,
            runtime_demand_states={
                1: SimpleNamespace(value="STRATEGIC_ACTIVE_EXECUTABLE"),
            },
            completion_witnesses={1: self._witness()},
        )

        self.assertEqual(
            diagnostics.diagnostics[0].code,
            RuleDiagnosticCode.RECURRENTLY_ELIGIBLE,
        )

    def test_inactive_runtime_demand_is_reported_as_never_eligible(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (set-goal demand 1))\n"
            )
        )

        diagnostics = analyze_rule_diagnostics(
            report,
            runtime_demand_states={
                1: SimpleNamespace(value="STRATEGIC_INACTIVE"),
            },
            completion_witnesses={1: self._witness()},
        )

        self.assertEqual(
            diagnostics.diagnostics[0].code,
            RuleDiagnosticCode.NEVER_ELIGIBLE,
        )

    def test_strategic_number_dependency_findings_compile_into_rule_diagnostics(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => "
                "(up-modify-sn 510 s:+ 511) "
                "(set-strategic-number 511 4))\n"
            )
        )
        strategic_numbers = analyze_strategic_number_expressions(report)

        diagnostics = analyze_rule_diagnostics(
            report,
            strategic_number_report=strategic_numbers,
        )

        findings = tuple(
            item
            for item in diagnostics.diagnostics
            if item.code is RuleDiagnosticCode.STRATEGIC_NUMBER_FUTURE_SAME_RULE_DEPENDENCY
        )
        self.assertEqual(len(findings), 1)
        diagnostic = findings[0]
        self.assertEqual(diagnostic.rule_order, 1)
        self.assertEqual(diagnostic.severity, DiagnosticSeverity.ERROR)
        self.assertIsNone(diagnostic.eligibility)
        self.assertEqual(diagnostic.category.value, "STRATEGIC_NUMBER")
        self.assertEqual(
            diagnostic.source_code,
            StrategicNumberDiagnosticCode.FUTURE_SAME_RULE_DEPENDENCY.value,
        )

    def test_globally_unreachable_rule_gets_control_flow_error(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (up-jump-rule 1))\n"
                "(defrule (true) => (set-goal unreachable 1))\n"
                "(defrule (true) => (set-goal reached 1))\n"
            )
        )

        diagnostics = analyze_rule_diagnostics(report)

        findings = tuple(
            item
            for item in diagnostics.diagnostics
            if item.code is RuleDiagnosticCode.CONTROL_TRANSFER_UNREACHABLE_RULE
        )

        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding.rule_order, 2)
        self.assertEqual(finding.severity, DiagnosticSeverity.ERROR)
        self.assertEqual(finding.category.value, "CONTROL_FLOW")
        self.assertEqual(finding.related_operation, "control-flow")

    def test_one_shot_jump_does_not_create_global_unreachable_diagnostic(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (up-jump-rule 1) (disable-self))\n"
                "(defrule (true) => (set-goal successor 1))\n"
                "(defrule (true) => (set-goal target 1))\n"
            )
        )

        diagnostics = analyze_rule_diagnostics(report)

        self.assertFalse(
            any(
                item.code is RuleDiagnosticCode.CONTROL_TRANSFER_UNREACHABLE_RULE
                for item in diagnostics.diagnostics
            )
        )

    def test_alternate_backward_path_prevents_false_global_unreachable_diagnostic(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (up-jump-rule 2))\n"
                "(defrule (true) => (set-goal second 1))\n"
                "(defrule (true) => (set-goal third 1))\n"
                "(defrule (true) => (up-jump-rule -3))\n"
            )
        )

        diagnostics = analyze_rule_diagnostics(report)

        self.assertFalse(
            any(
                item.code is RuleDiagnosticCode.CONTROL_TRANSFER_UNREACHABLE_RULE
                for item in diagnostics.diagnostics
            )
        )

    def test_open_loop_persistent_write_compiles_to_warning(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (set-goal open-loop 1))\n"
            )
        )
        persistent_state = analyze_persistent_state(report)

        diagnostics = analyze_rule_diagnostics(
            report,
            persistent_state_report=persistent_state,
        )

        findings = tuple(
            item
            for item in diagnostics.diagnostics
            if item.code is RuleDiagnosticCode.PERSISTENT_OPEN_LOOP_WRITE_WITHOUT_CONSUMER
        )

        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding.rule_order, 1)
        self.assertEqual(finding.severity, DiagnosticSeverity.WARNING)
        self.assertIsNone(finding.related_rule_order)
        self.assertEqual(finding.state_kind, "GOAL")
        self.assertEqual(finding.state_identifier, "open-loop")
        self.assertEqual(finding.source_code, "PSTATE-005")
        self.assertEqual(finding.category.value, "PERSISTENT_STATE")

    def test_path_sensitive_persistent_diagnostic_maps_to_rule_diagnostic(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (set-goal seed 1))\n"
                "(defrule (current-age >= castle-age) => (set-goal gate 1) (up-jump-rule 1))\n"
                "(defrule (goal gate 1) => (set-goal observed 1))\n"
                "(defrule (true) => (set-goal tail 1))\n"
            )
        )
        persistent_state = analyze_persistent_state(report)

        diagnostics = analyze_rule_diagnostics(
            report,
            persistent_state_report=persistent_state,
        )

        finding = next(
            item
            for item in diagnostics.diagnostics
            if item.code is RuleDiagnosticCode.PERSISTENT_SAME_PASS_CONSUMER_PATH_BLOCKED
        )
        self.assertEqual(finding.rule_order, 2)
        self.assertEqual(finding.related_rule_order, 3)
        self.assertEqual(finding.severity, DiagnosticSeverity.WARNING)
        self.assertEqual(finding.state_kind, "GOAL")
        self.assertEqual(finding.state_identifier, "gate")
        self.assertEqual(finding.source_code, "PSTATE-006")
        self.assertEqual(finding.category.value, "PERSISTENT_STATE")
    def test_open_loop_diagnostic_does_not_fire_when_reachable_consumer_exists(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (set-goal open-loop 1))\n"
                "(defrule (goal open-loop 1) => (set-goal sink 1))\n"
            )
        )
        persistent_state = analyze_persistent_state(report)

        diagnostics = analyze_rule_diagnostics(
            report,
            persistent_state_report=persistent_state,
        )

        self.assertFalse(
            any(
                item.code is RuleDiagnosticCode.PERSISTENT_OPEN_LOOP_WRITE_WITHOUT_CONSUMER
                and item.state_identifier == "open-loop"
                for item in diagnostics.diagnostics
            )
        )
    def test_recurrent_guaranteed_writer_is_reported_as_persistent_starvation(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (set-goal gate 0))\n"
                "(defrule (goal gate 1) => (set-goal observed 1))\n"
            )
        )
        persistent = analyze_persistent_state(report)

        finding = next(
            item
            for item in persistent.diagnostics
            if item.code
            is PersistentStateDiagnosticCode.CONSUMER_STARVED_BY_RECURRENT_WRITER
        )

        self.assertEqual(finding.rule_order, 2)
        self.assertEqual(finding.severity, DiagnosticSeverity.ERROR)
        self.assertEqual(finding.related_access.rule_order, 1)
        self.assertEqual(finding.related_access.command, "set-goal")

        diagnostics = analyze_rule_diagnostics(
            report,
            persistent_state_report=persistent,
        )
        rule_finding = next(
            item
            for item in diagnostics.diagnostics
            if item.code is RuleDiagnosticCode.PERSISTENT_CONSUMER_STARVED_BY_RECURRENT_WRITER
        )
        self.assertEqual(rule_finding.rule_order, 2)
        self.assertEqual(rule_finding.severity, DiagnosticSeverity.ERROR)
        self.assertEqual(rule_finding.related_rule_order, 1)
        self.assertEqual(rule_finding.state_identifier, "gate")

    def test_one_shot_shadowing_is_warning_not_persistent_starvation(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (set-goal gate 0) (disable-self))\n"
                "(defrule (goal gate 1) => (set-goal observed 1) (disable-self))\n"
            )
        )
        persistent = analyze_persistent_state(report)

        shadow = next(
            item
            for item in persistent.diagnostics
            if item.code
            is PersistentStateDiagnosticCode.CONSUMER_SHADOWED_BY_WRITER
        )
        self.assertEqual(shadow.severity, DiagnosticSeverity.WARNING)
        self.assertEqual(shadow.rule_order, 2)
        self.assertEqual(shadow.related_access.rule_order, 1)
        self.assertFalse(
            any(
                item.code
                is PersistentStateDiagnosticCode.CONSUMER_STARVED_BY_RECURRENT_WRITER
                for item in persistent.diagnostics
            )
        )

    def test_one_shot_jump_has_bypass_info_but_no_recurrent_preemption_warning(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (up-jump-rule 2) (disable-self))\n"
                "(defrule (true) => (set-goal skipped-a 1))\n"
                "(defrule (true) => (set-goal skipped-b 1))\n"
                "(defrule (true) => (set-goal reached 1))\n"
            )
        )

        diagnostics = analyze_rule_diagnostics(report)

        self.assertFalse(
            any(
                item.code is RuleDiagnosticCode.CONTROL_TRANSFER_PREEMPTS_RULE
                for item in diagnostics.diagnostics
            )
        )
        self.assertTrue(
            any(
                item.code is RuleDiagnosticCode.CONTROL_TRANSFER_BYPASSES_RULE
                and item.severity is DiagnosticSeverity.INFO
                for item in diagnostics.diagnostics
            )
        )

    def test_recurrent_guaranteed_jump_gets_preemption_diagnostics_for_each_bypassed_rule(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (up-jump-rule 2))\n"
                "(defrule (true) => (set-goal skipped-a 1))\n"
                "(defrule (true) => (set-goal skipped-b 1))\n"
                "(defrule (true) => (set-goal reached 1))\n"
            )
        )

        diagnostics = analyze_rule_diagnostics(report)

        preemptions = tuple(
            item
            for item in diagnostics.diagnostics
            if item.code is RuleDiagnosticCode.CONTROL_TRANSFER_PREEMPTS_RULE
        )

        self.assertEqual(
            [(item.rule_order, item.related_rule_order, item.severity) for item in preemptions],
            [
                (1, 2, DiagnosticSeverity.WARNING),
                (1, 3, DiagnosticSeverity.WARNING),
            ],
        )
        self.assertTrue(
            all(
                "alternate control paths are not ruled out" in item.message
                for item in preemptions
            )
        )

    def test_recurrent_execution_findings_compile_into_rule_diagnostics(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (set-goal gate 0))\n"
                "(defrule (goal gate 1) => (set-goal observed 1))\n"
            )
        )
        recurrent = analyze_recurrent_execution(report)

        diagnostics = analyze_rule_diagnostics(
            report,
            recurrent_execution_report=recurrent,
        )

        finding = next(
            item
            for item in diagnostics.diagnostics
            if item.code is RuleDiagnosticCode.RECURRENT_STATE_STARVATION
        )
        self.assertEqual(finding.rule_order, 2)
        self.assertEqual(finding.related_rule_order, 1)
        self.assertEqual(finding.state_kind, "GOAL")
        self.assertEqual(finding.state_identifier, "gate")
        self.assertEqual(finding.severity, DiagnosticSeverity.ERROR)
        self.assertEqual(finding.category.value, "RECURRENT_EXECUTION")
        self.assertEqual(finding.source_code, "REX-004")

    def test_persistent_state_findings_compile_into_rule_diagnostics(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (set-goal 7 1))\\n"
                "(defrule (true) => (set-goal 7 2))\\n"
            )
        )
        persistent = analyze_persistent_state(report)

        diagnostics = analyze_rule_diagnostics(
            report,
            persistent_state_report=persistent,
        )

        persistent_diagnostics = tuple(
            item
            for item in diagnostics.diagnostics
            if item.code is RuleDiagnosticCode.PERSISTENT_LATER_OVERWRITE
        )
        self.assertEqual(len(persistent_diagnostics), 1)
        diagnostic = persistent_diagnostics[0]
        self.assertEqual(diagnostic.rule_order, 2)
        self.assertEqual(diagnostic.severity, DiagnosticSeverity.WARNING)
        self.assertIsNone(diagnostic.eligibility)
        self.assertEqual(diagnostic.state_kind, "GOAL")
        self.assertEqual(diagnostic.state_identifier, "7")
        self.assertEqual(diagnostic.related_rule_order, 1)
        self.assertEqual(diagnostic.related_operation, "set-goal")
        self.assertEqual(diagnostic.category.value, "PERSISTENT_STATE")
        self.assertEqual(
            diagnostic.source_code,
            PersistentStateDiagnosticCode.LATER_OVERWRITE.value,
        )

    def test_persistent_state_error_retains_primary_and_related_rule_order(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (goal 7 1) => (set-goal 7 2))\\n"
            )
        )
        persistent = analyze_persistent_state(report)

        diagnostics = analyze_rule_diagnostics(
            report,
            persistent_state_report=persistent,
        )

        diagnostic = next(
            item
            for item in diagnostics.diagnostics
            if item.code is RuleDiagnosticCode.PERSISTENT_CONSUMER_BEFORE_WRITER
        )
        self.assertEqual(diagnostic.rule_order, 1)
        self.assertEqual(diagnostic.related_rule_order, 1)
        self.assertEqual(diagnostic.related_operation, "set-goal")
        self.assertEqual(diagnostic.state_identifier, "7")
        self.assertEqual(diagnostic.severity, DiagnosticSeverity.ERROR)

    def test_mixed_firing_and_persistent_diagnostics_are_deterministically_ordered(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (set-goal 7 1))\\n"
                "(defrule (true) => (set-goal 7 2))\\n"
            )
        )
        persistent = analyze_persistent_state(report)

        first = analyze_rule_diagnostics(report, persistent_state_report=persistent)
        second = analyze_rule_diagnostics(report, persistent_state_report=persistent)

        self.assertEqual(first, second)
        self.assertEqual(
            [
                (item.rule_order, item.category.value, item.code.value)
                for item in first.diagnostics
            ],
            [
                (1, "FIRING_ELIGIBILITY", "RULE-FIRE-004"),
                (2, "FIRING_ELIGIBILITY", "RULE-FIRE-004"),
                (2, "PERSISTENT_STATE", "PSTATE-002"),
                (2, "PERSISTENT_STATE", "PSTATE-005"),
            ],
        )

    def test_diagnostic_order_matches_effective_rule_order(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (set-goal first 1))\n"
                "(defrule (false) => (set-goal second 1))\n"
                "(defrule (current-age >= castle-age) => (set-goal third 1))\n"
            )
        )

        diagnostics = analyze_rule_diagnostics(report)

        self.assertEqual(
            [item.rule_order for item in diagnostics.diagnostics],
            [1, 2, 3],
        )



    def test_up_compare_sn_goal_dependency_is_tracked(self):
        report = analyze_effective_rules(
            self._graph(
                "(defrule (true) => (set-goal goal-x 1) (set-strategic-number 510 7))\n"
                "(defrule (up-compare-sn 510 g:>= goal-x) => (disable-self))\n"
            )
        )
        strategic_numbers = analyze_strategic_number_expressions(report)
        self.assertEqual(len(strategic_numbers.dependencies), 1)
        dependency = strategic_numbers.dependencies[0]
        self.assertEqual(dependency.kind.value, "GOAL")
        self.assertEqual(dependency.identifier, "goal-x")

if __name__ == "__main__":
    unittest.main()
