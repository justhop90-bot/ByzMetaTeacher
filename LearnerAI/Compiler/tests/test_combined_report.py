import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]
import sys
sys.path.insert(0, str(ROOT))

from Compiler.compiler import compile_source_with_report, exit_code_for_report
from Compiler.diagnostics import DiagnosticSeverity, DiagnosticSource, ReportStatus, SemanticDiagnostic, order_diagnostics
from Compiler.backends.models import (
    ArtifactIdentity,
    BackendIdentity,
    InvocationResult,
    NativeDiagnostic,
    DiagnosticConfidence,
    NativeValidationResult,
    SourceLocation,
    ValidationStatus,
    ValidationSummary,
)

def native_finding(artifact: Path, *, line: int, column: int, code: str, message: str, severity: DiagnosticSeverity = DiagnosticSeverity.ERROR) -> NativeDiagnostic:
    location = SourceLocation(artifact.resolve(), line, column, line, column + 4)
    return NativeDiagnostic(
        id=f'{line:02d}{column:02d}{code}',
        source='aoe2-ai-parser',
        code=code,
        severity=severity,
        confidence=DiagnosticConfidence.DEFINITE,
        message=message,
        suggestion=None,
        source_location=location,
        references=(),
    )

def native_result(artifact: Path, status: ValidationStatus, diagnostics=()):
    backend = BackendIdentity('aoe2-ai-parser', '0.1.0', '3dfa2583b7c2ec36b85ccb421ebd0abe9ff276ba', '3.12.7')
    return NativeValidationResult(
        status=status,
        failed=status is ValidationStatus.REJECTED,
        backend=backend,
        invocation=InvocationResult('default', artifact.resolve(), 1 if status is not ValidationStatus.VALIDATED else 0, 1),
        artifact=ArtifactIdentity(artifact.resolve(), '0' * 64),
        summary=ValidationSummary(len(diagnostics), len(diagnostics), 0, 0, 0),
        diagnostics=tuple(diagnostics),
        stderr='backend unavailable' if status.name.startswith('BACKEND_') else '',
    )

class FakeBackend:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def validate(self, artifact):
        self.calls += 1
        return self.result

class CombinedReportTests(unittest.TestCase):
    def test_mixed_semantic_and_native_order_is_source_then_location(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            artifact = tmp / "Basilisk.per"
            semantic = SemanticDiagnostic(
                id="semantic",
                source=DiagnosticSource.LEARNERAI,
                code="SEMANTIC-A",
                severity=DiagnosticSeverity.ERROR,
                message="semantic first",
            )
            native = native_finding(
                artifact, line=2, column=1, code="NATIVE-A", message="native second"
            )
            ordered = order_diagnostics((semantic,), (native,))
            self.assertEqual([item.source for item in ordered], [
                DiagnosticSource.LEARNERAI,
                DiagnosticSource.NATIVE,
            ])
            self.assertEqual([item.code for item in ordered], ["SEMANTIC-A", "NATIVE-A"])

    def test_native_diagnostics_are_stably_ordered_by_origin_location_code(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            artifact = tmp / 'Basilisk.per'
            first = native_finding(artifact, line=20, column=3, code='z-code', message='later')
            second = native_finding(artifact, line=2, column=3, code='a-code', message='earlier')
            backend = FakeBackend(native_result(artifact, ValidationStatus.REJECTED, (first, second)))
            source = '''
            demand castle {
                require (can-build castle)
                action (build castle)
                witness (building-type-count castle > 0)
                release (building-type-count castle > 0)
            }
            '''
            report = compile_source_with_report(source, native_backend=backend, output=artifact)
            self.assertEqual([item.code for item in report.diagnostics], ['a-code', 'z-code'])
            self.assertEqual(report.status, ReportStatus.NATIVE_REJECTED)
            self.assertEqual(exit_code_for_report(report), 1)

    def test_semantic_failure_skips_native_backend_and_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            artifact = tmp / 'Basilisk.per'
            backend = FakeBackend(native_result(artifact, ValidationStatus.VALIDATED))
            source = '''
            demand bad {
                require (can-build castle)
                action (can-build castle)
                witness (building-type-count castle > 0)
                release (building-type-count castle > 0)
            }
            '''
            report = compile_source_with_report(source, native_backend=backend, output=artifact)
            self.assertEqual(report.status, ReportStatus.SEMANTIC_REJECTED)
            self.assertEqual(backend.calls, 0)
            self.assertEqual(len(report.diagnostics), 1)
            self.assertEqual(report.diagnostics[0].source, 'LearnerAI')
            self.assertEqual(exit_code_for_report(report), 1)

    def test_backend_failure_has_infrastructure_exit_state(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            artifact = tmp / 'Basilisk.per'
            backend = FakeBackend(native_result(artifact, ValidationStatus.BACKEND_TIMEOUT))
            source = '''
            demand castle {
                require (can-build castle)
                action (build castle)
                witness (building-type-count castle > 0)
                release (building-type-count castle > 0)
            }
            '''
            report = compile_source_with_report(source, native_backend=backend, output=artifact)
            self.assertEqual(report.status, ReportStatus.BACKEND_FAILURE)
            self.assertEqual(exit_code_for_report(report), 2)

    def test_validated_status_with_findings_is_not_validation_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            artifact = tmp / 'Basilisk.per'
            finding = native_finding(
                artifact,
                line=4,
                column=1,
                code='NATIVE-FINDING',
                message='non-zero finding',
                severity=DiagnosticSeverity.WARNING,
            )
            backend = FakeBackend(
                native_result(
                    artifact,
                    ValidationStatus.VALIDATED,
                    (finding,),
                )
            )
            source = '''
            demand castle {
                require (can-build castle)
                action (build castle)
                witness (building-type-count castle > 0)
                release (building-type-count castle > 0)
            }
            '''
            report = compile_source_with_report(source, native_backend=backend, output=artifact)
            self.assertEqual(report.status, ReportStatus.BACKEND_FAILURE)
            self.assertNotEqual(exit_code_for_report(report), 0)
            self.assertEqual(report.native_diagnostics[0].code, 'NATIVE-FINDING')

    def test_validated_report_has_zero_exit_and_no_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            artifact = tmp / 'Basilisk.per'
            backend = FakeBackend(native_result(artifact, ValidationStatus.VALIDATED))
            source = '''
            demand castle {
                require (can-build castle)
                action (build castle)
                witness (building-type-count castle > 0)
                release (building-type-count castle > 0)
            }
            '''
            report = compile_source_with_report(source, native_backend=backend, output=artifact)
            self.assertEqual(report.status, ReportStatus.VALIDATED)
            self.assertEqual(report.diagnostics, ())
            self.assertEqual(exit_code_for_report(report), 0)

    def test_cli_semantic_rejection_uses_validation_exit_state(self):
        import subprocess
        import sys

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            source = tmp / "bad.basilisk"
            output = tmp / "Basilisk.per"
            source.write_text(
                """demand bad {
    require (can-build castle)
    action (can-build castle)
    witness (building-type-count castle > 0)
    release (building-type-count castle > 0)
}
""",
                encoding="utf-8",
            )
            run = subprocess.run(
                [sys.executable, str(ROOT / "Compiler" / "compiler.py"), str(source), str(output)],
                cwd=ROOT.parent,
                capture_output=True,
                text=True,
            )
            self.assertEqual(run.returncode, 1)
            self.assertFalse(output.exists())
            self.assertIn("SEMANTIC_REJECTED", run.stdout)
            self.assertIn("LearnerAI", run.stderr)

    def test_report_json_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            artifact = tmp / 'Basilisk.per'
            backend = FakeBackend(native_result(artifact, ValidationStatus.VALIDATED))
            source = '''
            demand castle {
                require (can-build castle)
                action (build castle)
                witness (building-type-count castle > 0)
                release (building-type-count castle > 0)
            }
            '''
            a = compile_source_with_report(source, native_backend=backend, output=artifact)
            b = compile_source_with_report(source, native_backend=backend, output=artifact)
            self.assertEqual(a.to_json(), b.to_json())
            json.loads(a.to_json())

if __name__ == '__main__':
    unittest.main()