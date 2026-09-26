import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from Compiler.ast import SourceLocation
from Compiler.ir import (
    CompletionWitnessContract,
    SemanticId,
    WitnessEvidenceKind,
)
from Compiler.diagnostics import DiagnosticSeverity
from Compiler.semantic.rule_diagnostics import (
    RuleDiagnosticCode,
    analyze_rule_diagnostics,
)
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
        self.assertEqual(diagnostic.severity, RuleDiagnosticSeverity.INFO)

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


if __name__ == "__main__":
    unittest.main()
