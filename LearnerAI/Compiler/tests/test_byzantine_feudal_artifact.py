from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import unittest

from LearnerAI.Compiler.primitives import default_de_registry
from LearnerAI.Compiler.semantic.rule_execution import analyze_effective_rules
from LearnerAI.Compiler.semantic.persistent_state import analyze_persistent_state
from LearnerAI.Compiler.semantic.persistent_control import analyze_persistent_control_lifetimes
from LearnerAI.Compiler.semantic.strategic_number_semantics import analyze_strategic_number_expressions
from LearnerAI.Compiler.semantic.recurrent_execution import analyze_recurrent_execution
from LearnerAI.Compiler.semantic.duc import analyze_duc
from LearnerAI.Compiler.semantic.rule_diagnostics import analyze_rule_diagnostics
from LearnerAI.Compiler.source_graph import SourceGraphRequest, SourceGraphResolver


ARTIFACT = Path(__file__).parent / "fixtures" / "byzantine_feudal_audited.per"


class ByzantineArtifactCompilerAudit(unittest.TestCase):
    def test_compiler_raw_rule_parser_and_semantic_validator(self):
        graph = SourceGraphResolver().resolve(SourceGraphRequest(entrypoint=ARTIFACT))
        execution = analyze_effective_rules(graph)
        self.assertGreater(len(execution.rules), 0)

        registry = default_de_registry()
        persistent = analyze_persistent_state(execution)
        strategic = analyze_strategic_number_expressions(execution)
        recurrent = analyze_recurrent_execution(execution)
        duc = analyze_duc(
            execution,
            registry.native_contracts,
            recurrent_execution=recurrent,
        )
        rule_report = analyze_rule_diagnostics(
            execution,
            registry,
            persistent_state_report=persistent,
            strategic_number_report=strategic,
            recurrent_execution_report=recurrent,
            duc_report=duc,
        )

        print(f"compiler raw parser: rules={len(execution.rules)}")
        print(f"compiler strategic-number errors={len(strategic.errors)}")
        recurrent_errors = tuple(d for d in recurrent.diagnostics if d.code != "REX-002")
        print(f"compiler recurrent errors={len(recurrent_errors)}")
        print(f"compiler duc errors={len(duc.errors)}")
        print(f"compiler rule-diagnostic errors={len(rule_report.errors)}")
        if strategic.errors:
            print("SN ERRORS", strategic.errors)
        if recurrent.errors:
            print("RECURRENT ERRORS", recurrent_errors)
        if duc.errors:
            print("DUC ERRORS", duc.errors)
        if rule_report.errors:
            print("RULE ERRORS", rule_report.errors)

        self.assertFalse(strategic.errors, strategic.errors)
        self.assertFalse(recurrent_errors, recurrent_errors)
        self.assertFalse(duc.errors, duc.errors)

    def test_pinned_native_parser(self):
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "aoe2_ai_lab",
                "lint",
                str(ARTIFACT),
                "--profile",
                "default",
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        print("native returncode=", proc.returncode)
        if proc.stdout:
            payload = json.loads(proc.stdout)
            print("native failed=", payload.get("failed"))
            print("native finding_count=", payload.get("finding_count"))
            for finding in payload.get("findings", [])[:20]:
                print("NATIVE", finding)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload.get("failed"), payload)
        self.assertEqual(payload.get("finding_count"), 0, payload)


if __name__ == "__main__":
    unittest.main()
