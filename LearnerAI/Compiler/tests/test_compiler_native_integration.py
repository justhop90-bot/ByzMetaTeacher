import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.backends.errors import NativeBackendError
from Compiler.backends.models import (
    ArtifactIdentity,
    BackendIdentity,
    InvocationResult,
    NativeValidationResult,
    ValidationStatus,
    ValidationSummary,
)
from Compiler.compiler import compile_source_with_report, compile_to_file
from Compiler.diagnostics import ReportStatus

EXAMPLES = (Path(__file__).parents[1] / "examples" / "basics.basilisk").read_text(encoding="utf-8")


def fake_result(output: Path, status: ValidationStatus) -> NativeValidationResult:
    backend = BackendIdentity("aoe2-ai-parser", "0.1.0", "3dfa2583b7c2ec36b85ccb421ebd0abe9ff276ba", "3.12.7")
    artifact = ArtifactIdentity(output.resolve(), "0" * 64)
    return NativeValidationResult(
        status=status,
        failed=status is ValidationStatus.REJECTED,
        backend=backend,
        invocation=InvocationResult("default", output.resolve(), 0 if status is ValidationStatus.VALIDATED else 1, 1),
        artifact=artifact,
        summary=ValidationSummary(0, 0, 0, 0, 0),
        diagnostics=(),
        stderr="" if status is ValidationStatus.VALIDATED else "backend unavailable",
    )


class FakeBackend:
    def __init__(self, result):
        self.result = result
        self.seen_artifact = None

    def validate(self, artifact: Path):
        self.seen_artifact = artifact
        return self.result

class CompilerNativeIntegrationTests(unittest.TestCase):
    def test_compile_to_file_requires_native_validation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "Basilisk.per"

            with self.assertRaises(NativeBackendError):
                compile_to_file(EXAMPLES, output)

            self.assertFalse(output.exists())

    def test_compile_source_with_report_requires_native_validation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "Basilisk.per"
            output.write_text("KEEP THIS\n", encoding="utf-8")

            report = compile_source_with_report(EXAMPLES, output)

            self.assertEqual(report.status, ReportStatus.BACKEND_FAILURE)
            self.assertEqual(output.read_text(encoding="utf-8"), "KEEP THIS\n")
            self.assertEqual(
                report.diagnostics[0].code,
                "NATIVE-VALIDATION-REQUIRED",
            )

    def test_validated_backend_with_findings_never_promotes(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            output = tmp / "Basilisk.per"
            output.write_text("KEEP THIS\n", encoding="utf-8")
            result = fake_result(output, ValidationStatus.VALIDATED)
            result = NativeValidationResult(
                status=result.status,
                failed=False,
                backend=result.backend,
                invocation=result.invocation,
                artifact=result.artifact,
                summary=ValidationSummary(1, 0, 1, 0, 0),
                diagnostics=(),
                stderr="",
            )
            fake = FakeBackend(result)

            validation = compile_to_file(EXAMPLES, output, native_backend=fake)

            self.assertEqual(validation.status, ValidationStatus.BACKEND_PROTOCOL_ERROR)
            self.assertEqual(output.read_text(encoding="utf-8"), "KEEP THIS\n")

    def test_validated_backend_promotes_staged_output(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            output = tmp / "Basilisk.per"
            output.write_text("OLD ARTIFACT\n", encoding="utf-8")
            fake = FakeBackend(fake_result(output, ValidationStatus.VALIDATED))

            result = compile_to_file(EXAMPLES, output, native_backend=fake)

            self.assertEqual(result.status, ValidationStatus.VALIDATED)
            self.assertIn("BASILISK GENERATED .PER", output.read_text(encoding="utf-8"))
            self.assertIsNotNone(fake.seen_artifact)
            self.assertNotEqual(fake.seen_artifact, output)

    def test_rejected_backend_does_not_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            output = tmp / "Basilisk.per"
            output.write_text("KEEP THIS\n", encoding="utf-8")
            fake = FakeBackend(fake_result(output, ValidationStatus.REJECTED))

            result = compile_to_file(EXAMPLES, output, native_backend=fake)

            self.assertEqual(result.status, ValidationStatus.REJECTED)
            self.assertEqual(output.read_text(encoding="utf-8"), "KEEP THIS\n")

    def test_backend_failure_does_not_promote_artifact(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            output = tmp / "Basilisk.per"
            output.write_text("KEEP THIS\n", encoding="utf-8")
            fake = FakeBackend(fake_result(output, ValidationStatus.BACKEND_TIMEOUT))

            result = compile_to_file(EXAMPLES, output, native_backend=fake)

            self.assertEqual(result.status, ValidationStatus.BACKEND_TIMEOUT)
            self.assertEqual(output.read_text(encoding="utf-8"), "KEEP THIS\n")


    def test_validated_backend_promotes_binding_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            output = tmp / "Basilisk.per"
            manifest = tmp / "Basilisk.bindings.json"
            fake = FakeBackend(fake_result(output, ValidationStatus.VALIDATED))

            result = compile_to_file(
                EXAMPLES,
                output,
                native_backend=fake,
                binding_manifest=manifest,
            )

            self.assertEqual(result.status, ValidationStatus.VALIDATED)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(payload["format_version"], 2)
            self.assertEqual(len(payload["records"]), 4)
            self.assertTrue(all("goal_id" in record for record in payload["records"]))

    def test_rejected_backend_does_not_overwrite_existing_binding_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            output = tmp / "Basilisk.per"
            manifest = tmp / "Basilisk.bindings.json"
            output.write_text("KEEP THIS\n", encoding="utf-8")
            manifest.write_text("KEEP MANIFEST\n", encoding="utf-8")
            fake = FakeBackend(fake_result(output, ValidationStatus.REJECTED))

            result = compile_to_file(
                EXAMPLES,
                output,
                native_backend=fake,
                binding_manifest=manifest,
            )

            self.assertEqual(result.status, ValidationStatus.REJECTED)
            self.assertEqual(output.read_text(encoding="utf-8"), "KEEP THIS\n")
            self.assertEqual(manifest.read_text(encoding="utf-8"), "KEEP MANIFEST\n")

if __name__ == "__main__":
    unittest.main()
