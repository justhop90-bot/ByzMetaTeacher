from __future__ import annotations

import argparse
import hashlib
import json
import sys
from types import SimpleNamespace
import tempfile
from pathlib import Path

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.compiler import compile_package_with_report, compile_source_with_report
from Compiler.diagnostics import ReportStatus
from Compiler.source_graph import SourceGraphRequest
from native_support_replay_schema import validate_snapshot
from test_compiler_native_integration import (
    CompilerNativeIntegrationTests,
    FakeBackend,
    ValidationStatus,
    fake_result,
    persistent_rule_diagnostic,
)


def persistent_artifact_hashes() -> dict[str, str]:
    source = '''
    demand castle {
        require (can-build castle)
        action (build castle)
        witness (building-type-count castle > 0)
        release (building-type-count castle > 0)
    }
    '''
    rule_report = SimpleNamespace(diagnostics=(persistent_rule_diagnostic(),))
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        file_output = tmp / 'file.per'
        file_backend = FakeBackend(
            fake_result(file_output, ValidationStatus.VALIDATED)
        )
        with patch(
            'Compiler.compiler.analyze_rule_diagnostics',
            return_value=rule_report,
        ):
            file_report = compile_source_with_report(
                source,
                file_output,
                native_backend=file_backend,
                source_unit='persistent-artifact.perdsl',
            )
        if file_report.status is not ReportStatus.VALIDATED:
            raise AssertionError(
                f'persistent file artifact promotion failed: {file_report.status.value}'
            )

        package_root = tmp / 'package-root.perdsl'
        package_child = tmp / 'package-child.perdsl'
        package_output = tmp / 'package.per'
        package_child.write_text(source, encoding='utf-8')
        package_root.write_text(
            '(load "package-child.perdsl")\n',
            encoding='utf-8',
        )
        package_backend = FakeBackend(
            fake_result(package_output, ValidationStatus.VALIDATED)
        )
        with patch(
            'Compiler.compiler.analyze_rule_diagnostics',
            return_value=rule_report,
        ):
            package_report = compile_package_with_report(
                SourceGraphRequest(entrypoint=package_root),
                package_output,
                native_backend=package_backend,
            )
        if package_report.status is not ReportStatus.VALIDATED:
            raise AssertionError(
                f'persistent package artifact promotion failed: {package_report.status.value}'
            )

        return {
            'file': hashlib.sha256(file_output.read_bytes()).hexdigest(),
            'package': hashlib.sha256(package_output.read_bytes()).hexdigest(),
        }
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
        "persistent_artifacts": persistent_artifact_hashes(),
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
