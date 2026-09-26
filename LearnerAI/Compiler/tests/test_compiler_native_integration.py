import hashlib
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
from Compiler.primitives.native_schema import NativeCommandRegistry, NativeCommandSpec, NativeParameterSpec, load_default_native_schema
from Compiler.primitives.registry import NativeSupportState, Primitive, PrimitiveRegistry, default_de_registry
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
            self.assertEqual(payload["format_version"], 3)
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

    def test_native_support_state_fixtures_traverse_full_compiler_pipeline(self):
        fixture_root = Path(__file__).parent / "fixtures" / "native_support_states"
        cases = (
            ("native-known", NativeSupportState.UNSUPPORTED, "NATIVE-SUPPORT-005"),
            ("native-typed", NativeSupportState.UNSUPPORTED, "NATIVE-SUPPORT-005"),
            ("semantically-adapted", NativeSupportState.UNSUPPORTED, "NATIVE-SUPPORT-005"),
            ("executable-safe", NativeSupportState.EXECUTABLE_SAFE, None),
            ("unsupported", NativeSupportState.UNSUPPORTED, "NATIVE-SUPPORT-005"),
        )

        for name, expected_state, expected_code in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp_dir:
                source = (fixture_root / f"{name}.basilisk").read_text(encoding="utf-8")
                registry = self._native_support_fixture_registry(name)
                output = Path(tmp_dir) / f"{name}.per"
                backend = FakeBackend(fake_result(output, ValidationStatus.VALIDATED))

                if name != "executable-safe":
                    output.write_text("KEEP UNSUPPORTED ARTIFACT\\n", encoding="utf-8")
                    before = output.read_text(encoding="utf-8")
                else:
                    before = None

                report = compile_source_with_report(
                    source,
                    output,
                    native_backend=backend,
                    registry=registry,
                    source_unit=f"native-support/{name}.basilisk",
                )

                expected_states = {
                    "native-known": [
                        NativeSupportState.NATIVE_KNOWN,
                        NativeSupportState.UNSUPPORTED,
                    ],
                    "native-typed": [
                        NativeSupportState.NATIVE_KNOWN,
                        NativeSupportState.NATIVE_TYPED,
                        NativeSupportState.UNSUPPORTED,
                    ],
                    "semantically-adapted": [
                        NativeSupportState.NATIVE_KNOWN,
                        NativeSupportState.NATIVE_TYPED,
                        NativeSupportState.SEMANTICALLY_ADAPTED,
                        NativeSupportState.UNSUPPORTED,
                    ],
                    "executable-safe": [
                        NativeSupportState.NATIVE_KNOWN,
                        NativeSupportState.NATIVE_TYPED,
                        NativeSupportState.SEMANTICALLY_ADAPTED,
                        NativeSupportState.EXECUTABLE_SAFE,
                    ],
                    "unsupported": [
                        NativeSupportState.UNSUPPORTED,
                    ],
                }
                expected_codes = {
                    "native-known": ["NATIVE-SUPPORT-001", "NATIVE-SUPPORT-005"],
                    "native-typed": [
                        "NATIVE-SUPPORT-001",
                        "NATIVE-SUPPORT-002",
                        "NATIVE-SUPPORT-005",
                    ],
                    "semantically-adapted": [
                        "NATIVE-SUPPORT-001",
                        "NATIVE-SUPPORT-002",
                        "NATIVE-SUPPORT-003",
                        "NATIVE-SUPPORT-005",
                    ],
                    "executable-safe": [
                        "NATIVE-SUPPORT-001",
                        "NATIVE-SUPPORT-002",
                        "NATIVE-SUPPORT-003",
                        "NATIVE-SUPPORT-004",
                    ],
                    "unsupported": ["NATIVE-SUPPORT-005"],
                }

                assessment = registry.assess_support("fixture-command")
                repeat_assessment = registry.assess_support("fixture-command")
                self.assertEqual(assessment.state, expected_state)
                self.assertEqual(
                    [diagnostic.state for diagnostic in assessment.diagnostics],
                    expected_states[name],
                )
                self.assertEqual(
                    [diagnostic.code for diagnostic in assessment.diagnostics],
                    expected_codes[name],
                )
                self.assertEqual(
                    [diagnostic.code for diagnostic in repeat_assessment.diagnostics],
                    expected_codes[name],
                )

                if name == "executable-safe":
                    self.assertEqual(report.status, ReportStatus.VALIDATED)
                    self.assertIsNotNone(backend.seen_artifact)
                    self.assertTrue(output.exists())
                else:
                    self.assertEqual(report.status, ReportStatus.SEMANTIC_REJECTED)
                    self.assertEqual(
                        [diagnostic.code for diagnostic in report.diagnostics],
                        ["NATIVE-SUPPORT-005"],
                    )
                    self.assertIsNone(backend.seen_artifact)
                    self.assertTrue(output.exists())
                    self.assertEqual(output.read_text(encoding="utf-8"), before)

                    expected_support_payload = [
                        {
                            "command": diagnostic.command,
                            "state": diagnostic.state.value,
                            "code": diagnostic.code,
                            "severity": diagnostic.severity,
                            "message": diagnostic.message,
                        }
                        for diagnostic in assessment.diagnostics
                    ]
                    baseline_payload = report.to_dict()["diagnostics"]
                    baseline_state_sequence = [
                        diagnostic.state.value for diagnostic in assessment.diagnostics
                    ]
                    baseline_artifact_hash = hashlib.sha256(
                        output.read_bytes()
                    ).hexdigest()

                    self.assertEqual(
                        [item["code"] for item in baseline_payload],
                        ["NATIVE-SUPPORT-005"],
                    )
                    self.assertEqual(
                        baseline_state_sequence,
                        [state.value for state in expected_states[name]],
                    )
                    self.assertEqual(
                        [item["code"] for item in expected_support_payload],
                        expected_codes[name],
                    )

                    for run_number in range(2, 4):
                        replay_backend = FakeBackend(
                            fake_result(output, ValidationStatus.VALIDATED)
                        )
                        replay_report = compile_source_with_report(
                            source,
                            output,
                            native_backend=replay_backend,
                            registry=registry,
                            source_unit=f"native-support/{name}.basilisk",
                        )
                        replay_assessment = registry.assess_support("fixture-command")
                        replay_payload = replay_report.to_dict()["diagnostics"]
                        replay_state_sequence = [
                            diagnostic.state.value
                            for diagnostic in replay_assessment.diagnostics
                        ]
                        replay_artifact_hash = hashlib.sha256(
                            output.read_bytes()
                        ).hexdigest()

                        self.assertEqual(
                            replay_report.status,
                            ReportStatus.SEMANTIC_REJECTED,
                            msg=f"run {run_number}",
                        )
                        self.assertEqual(
                            replay_payload,
                            baseline_payload,
                            msg=f"diagnostic payload changed on run {run_number}",
                        )
                        self.assertEqual(
                            replay_state_sequence,
                            baseline_state_sequence,
                            msg=f"support-state sequence changed on run {run_number}",
                        )
                        self.assertEqual(
                            [
                                {
                                    "command": diagnostic.command,
                                    "state": diagnostic.state.value,
                                    "code": diagnostic.code,
                                    "severity": diagnostic.severity,
                                    "message": diagnostic.message,
                                }
                                for diagnostic in replay_assessment.diagnostics
                            ],
                            expected_support_payload,
                            msg=f"support diagnostic payload changed on run {run_number}",
                        )
                        self.assertEqual(
                            replay_artifact_hash,
                            baseline_artifact_hash,
                            msg=f"artifact hash changed on run {run_number}",
                        )
                        self.assertEqual(
                            output.read_text(encoding="utf-8"),
                            before,
                            msg=f"artifact content changed on run {run_number}",
                        )
                        self.assertIsNone(
                            replay_backend.seen_artifact,
                            msg=f"native backend invoked on run {run_number}",
                        )

    @staticmethod
    def _native_support_fixture_registry(name):
        parameter = NativeParameterSpec(
            "Value",
            "Const",
            "in",
            "fixture",
            "fixture parameter",
        )
        base_registry = default_de_registry()
        base_primitives = tuple(
            base_registry.get(command)
            for command in base_registry.names()
        )
        base_native = load_default_native_schema()
        base_native_commands = tuple(
            base_native.get(command)
            for command in base_native.names()
        )

        if name == "native-known":
            native = NativeCommandSpec(
                "fixture-command",
                "DE",
                "Fact",
                (NativeParameterSpec("", "", "", "", ""),),
            )
            primitive = None
        elif name == "native-typed":
            native = NativeCommandSpec(
                "fixture-command",
                "DE",
                "Fact",
                (parameter,),
            )
            primitive = None
        elif name == "semantically-adapted":
            native = NativeCommandSpec(
                "fixture-command",
                "DE",
                "Fact",
                (parameter,),
            )
            primitive = Primitive("fixture-command", "FACT", "FEASIBILITY", 2, 2)
        elif name == "executable-safe":
            native = NativeCommandSpec(
                "fixture-command",
                "DE",
                "Fact",
                (parameter,),
            )
            primitive = Primitive("fixture-command", "FACT", "FEASIBILITY", 1, 1)
        else:
            return base_registry

        primitives = base_primitives if primitive is None else base_primitives + (primitive,)
        native_registry = NativeCommandRegistry(
            base_native_commands + (native,),
            source_blob_sha=f"native-support-{name}",
            command_count=len(base_native_commands) + 1,
        )
        return PrimitiveRegistry(primitives, native_registry)


if __name__ == "__main__":
    unittest.main()
