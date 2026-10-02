#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

from Compiler.primitives import default_de_registry
from Compiler.source_graph import EffectiveSourceGraph, SourceGraphRequest, SourceGraphResolver
from Compiler.semantic.source_graph_validation import validate_effective_source_graph
from Compiler.semantic.rule_execution import analyze_effective_rules
from Compiler.semantic.persistent_state import analyze_persistent_state
from Compiler.semantic.strategic_number_semantics import analyze_strategic_number_expressions
from Compiler.semantic.recurrent_execution import analyze_recurrent_execution
from Compiler.semantic.duc import analyze_duc
from Compiler.semantic.rule_diagnostics import analyze_rule_diagnostics

def diag_dict(item):
    code = getattr(item, "code", None)
    if hasattr(code, "value"):
        code = code.value
    return {
        "code": code,
        "category": getattr(getattr(item, "category", None), "value", getattr(item, "category", None)),
        "severity": getattr(getattr(item, "severity", None), "value", getattr(item, "severity", None)),
        "line": getattr(item, "line", None),
        "message": getattr(item, "message", str(item)),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("artifact", type=Path)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    artifact = args.artifact.resolve()
    registry = default_de_registry()
    report = {"artifact": str(artifact), "source_graph_valid": False, "effective_rule_count": 0,
              "persistent_state_errors": [], "strategic_number_errors": [], "duc_errors": [],
              "rule_diagnostics": [], "errors": []}
    try:
        graph = SourceGraphResolver().resolve(SourceGraphRequest(entrypoint=artifact))
        graph_report = validate_effective_source_graph(graph)
        report["source_graph_valid"] = bool(graph_report.valid)
        report["source_graph_errors"] = [diag_dict(x) for x in getattr(graph_report, "errors", ())]
        effective_rules = analyze_effective_rules(graph)
        report["effective_rule_count"] = len(effective_rules)
        persistent = analyze_persistent_state(effective_rules)
        sn = analyze_strategic_number_expressions(effective_rules)
        recurrent = analyze_recurrent_execution(effective_rules)
        duc = analyze_duc(effective_rules, registry.native_contracts, recurrent_execution=recurrent)
        rule_report = analyze_rule_diagnostics(
            effective_rules,
            registry,
            persistent_state_report=persistent,
            strategic_number_report=sn,
            recurrent_execution_report=recurrent,
            duc_report=duc,
            persistent_control_report=None,
        )
        report["persistent_state_errors"] = [diag_dict(x) for x in getattr(persistent, "errors", ())]
        report["strategic_number_errors"] = [diag_dict(x) for x in getattr(sn, "errors", ())]
        report["duc_errors"] = [diag_dict(x) for x in getattr(duc, "errors", ())]
        report["rule_diagnostics"] = [diag_dict(x) for x in getattr(rule_report, "diagnostics", ())]
        report["errors"] = [diag_dict(x) for x in getattr(rule_report, "errors", ())]
    except Exception as exc:
        report["errors"] = [{"code": "SEMANTIC-EXCEPTION", "message": f"{type(exc).__name__}: {exc}"}]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["source_graph_valid"] and not report["errors"] and not report["persistent_state_errors"] and not report["strategic_number_errors"] and not report["duc_errors"] else 1

if __name__ == "__main__":
    raise SystemExit(main())

# validation-harness touch
