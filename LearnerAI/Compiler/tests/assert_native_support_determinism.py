from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.compiler import compile_source_with_report
from Compiler.artifact_diagnostics import append_persistent_rule_diagnostics
from Compiler.diagnostics import ReportStatus
from native_support_replay_schema import validate_snapshot
from test_compiler_native_integration import (
    CompilerNativeIntegrationTests,
    FakeBackend,
    ValidationStatus,
    fake_result,
)


def persistent_artifact_sha256() -> str:
    artifact = "(defrule (true) => (set-goal 7 1))\n"
    category = type("Category", (), {"value": "PERSISTENT_STATE"})()
    code = type("Code", (), {"value": "PSTATE-002"})()
    severity = type("Severity", (), {"value": "warning"})()
    diagnostic = type(
        "Diagnostic",
        (),
        {
            "category": category,
            "rule_order": 2,
            "code": code,
            "severity": severity,
            "state_kind": "GOAL",
            "state_identifier": "7",
            "related_rule_order": 1,
            "related_operation": "set-goal",
            "message": "goal state '7' has a later writer in rule 2 after writer in rule 1",
        },
    )()
    rendered = append_persistent_rule_diagnostics(artifact, (diagnostic,))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()

UNSUPPORTED_STATES = (
    "native-known",
    "native-typed",
    "semantically-adapted",
    "unsupported",
)

def build_snapshot() -> dict[str, object]:
    fixture_root = Path(__file__).parent / "fixtures" / "native_support_states"
    fixtures: dict[str, object] = {}

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        for name in UNSUPPORTED_STATES:
            source = (fixture_root / f"{name}.perdsl").read_text(encoding="utf-8")
            registry = CompilerNativeIntegrationTests._native_support_fixture_registry(name)
            output = tmp / f"{name}.per"
            output.write_bytes(b"KEEP UNSUPPORTED ARTIFACT\n")
            backend = FakeBackend(fake_result(output, ValidationStatus.VALIDATED))
            report = compile_source_with_report(
                source,
                output,
                native_backend=backend,
                registry=registry,
                source_unit=f"native-support/{name}.perdsl",
            )
            assessment = registry.assess_support("fixture-command")
            if report.status is not ReportStatus.SEMANTIC_REJECTED:
                raise AssertionError(
                    f"{name}: expected semantic rejection, got {report.status.value}"
                )
            if backend.seen_artifact is not None:
                raise AssertionError(f"{name}: native backend was invoked")
            if output.read_text(encoding="utf-8") != "KEEP UNSUPPORTED ARTIFACT\n":
                raise AssertionError(f"{name}: artifact was modified")
            fixtures[name] = {
                "diagnostics": report.to_dict()["diagnostics"],
                "support_diagnostics": [
                    {
                        "command": diagnostic.command,
                        "state": diagnostic.state.value,
                        "code": diagnostic.code,
                        "severity": diagnostic.severity,
                        "message": diagnostic.message,
                    }
                    for diagnostic in assessment.diagnostics
                ],
                "support_state_sequence": [
                    diagnostic.state.value for diagnostic in assessment.diagnostics
                ],
                "artifact_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            }

    snapshot = {
        "schema_version": 2,
        "python": ".".join(map(str, sys.version_info[:3])),
        "platform": sys.platform,
        "persistent_artifact_sha256": persistent_artifact_sha256(),
        "fixtures": fixtures,
    }
    return validate_snapshot(snapshot, source="generated snapshot")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_snapshot()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

if __name__ == "__main__":
    main()
