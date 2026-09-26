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
from Compiler.diagnostics import ReportStatus
from native_support_replay_schema import validate_snapshot
from test_compiler_native_integration import (
    CompilerNativeIntegrationTests,
    FakeBackend,
    ValidationStatus,
    fake_result,
)

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
            source = (fixture_root / f"{name}.basilisk").read_text(encoding="utf-8")
            registry = CompilerNativeIntegrationTests._native_support_fixture_registry(name)
            output = tmp / f"{name}.per"
            output.write_bytes(b"KEEP UNSUPPORTED ARTIFACT\n")
            backend = FakeBackend(fake_result(output, ValidationStatus.VALIDATED))
            report = compile_source_with_report(
                source,
                output,
                native_backend=backend,
                registry=registry,
                source_unit=f"native-support/{name}.basilisk",
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
        "schema_version": 1,
        "python": ".".join(map(str, sys.version_info[:3])),
        "platform": sys.platform,
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
