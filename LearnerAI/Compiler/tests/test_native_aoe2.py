import json
import tempfile
import unittest
from pathlib import Path

from Compiler.backends.errors import BackendProtocolError
from Compiler.backends.models import ValidationStatus
from Compiler.backends.native_aoe2 import (
    Aoe2NativeBackend,
    BackendSpec,
    ProcessOutput,
)


class FakeRunner:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def run(self, args, *, cwd, env, timeout_seconds):
        self.calls.append((tuple(args), cwd, dict(env), timeout_seconds))
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


class NativeBackendTests(unittest.TestCase):
    def _installation(self, tmp: Path) -> BackendSpec:
        root = tmp / "backend"
        root.mkdir()
        (root / "manifest.json").write_text(
            json.dumps({
                "name": "aoe2-ai-parser",
                "project_version": "0.1.0",
                "commit_sha": "3dfa2583b7c2ec36b85ccb421ebd0abe9ff276ba",
            }),
            encoding="utf-8",
        )
        executable = root / "python.exe"
        executable.write_text("fake", encoding="utf-8")
        return BackendSpec(
            name="aoe2-ai-parser",
            project_version="0.1.0",
            commit_sha="3dfa2583b7c2ec36b85ccb421ebd0abe9ff276ba",
            python_major_minor="3.12",
            root=root,
            executable=executable,
            timeout_seconds=3.0,
        )

    def _python_probe(self):
        return ProcessOutput("Python 3.12.7\\n", "", 0, 1)

    def _fixture_path(self, name: str) -> Path:
        return Path(__file__).resolve().parent / "fixtures" / "native_backend" / "protocol" / name

    def _fixture_text(self, name: str) -> str:
        return self._fixture_path(name).read_text(encoding="utf-8")

    def _run_fixture(self, tmp: Path, fixture: str, *, exit_code: int = 1, stderr: str = ""):
        artifact = tmp / "Basilisk.per"
        artifact.write_text("(build castle)\\n", encoding="utf-8")
        runner = FakeRunner([
            self._python_probe(),
            ProcessOutput(self._fixture_text(fixture), stderr, exit_code, 4),
        ])
        result = Aoe2NativeBackend(self._installation(tmp), runner).validate(artifact)
        return artifact, runner, result

    def _backend_payload(self, artifact: Path, *, failed=False, findings=None):
        return json.dumps({
            "path": str(artifact),
            "finding_count": len(findings or []),
            "findings": findings or [],
            "failed": failed,
        })

    def test_validates_clean_backend_output(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            artifact = tmp / "Basilisk.per"
            artifact.write_text("(defrule (true) => (nop))\\n", encoding="utf-8")
            runner = FakeRunner([
                self._python_probe(),
                ProcessOutput(self._backend_payload(artifact), "", 0, 4),
            ])
            result = Aoe2NativeBackend(self._installation(tmp), runner).validate(artifact)
            self.assertEqual(result.status, ValidationStatus.VALIDATED)
            self.assertFalse(result.failed)
            self.assertEqual(result.summary.finding_count, 0)
            self.assertEqual(len(runner.calls), 2)
            self.assertEqual(runner.calls[1][0][1:3], ("-m", "aoe2_ai_lab"))
            self.assertFalse(runner.calls[1][2].get("PYTHONPATH"))
            self.assertEqual(runner.calls[1][2]["PYTHONNOUSERSITE"], "1")

    def test_normalizes_span_columns_to_one_based(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            artifact = tmp / "Basilisk.per"
            artifact.write_text("(build castle)\\n", encoding="utf-8")
            finding = {
                "path": str(artifact),
                "line": 1,
                "severity": "error",
                "confidence": "definite",
                "code": "command-role-mismatch",
                "message": "bad role",
                "suggestion": None,
                "references": [],
                "span": {"start_line": 1, "start_col": 1, "end_line": 1, "end_col": 6},
            }
            runner = FakeRunner([
                self._python_probe(),
                ProcessOutput(self._backend_payload(artifact, failed=True, findings=[finding]), "", 1, 4),
            ])
            result = Aoe2NativeBackend(self._installation(tmp), runner).validate(artifact)
            self.assertEqual(result.status, ValidationStatus.REJECTED)
            location = result.diagnostics[0].source_location
            self.assertEqual(location.column, 2)
            self.assertEqual(location.end_column, 7)
            self.assertEqual(result.diagnostics[0].code, "command-role-mismatch")

    def test_timeout_is_not_script_rejection(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            artifact = tmp / "Basilisk.per"
            artifact.write_text("(build castle)\\n", encoding="utf-8")
            runner = FakeRunner([
                self._python_probe(),
                TimeoutError("timed out"),
            ])
            result = Aoe2NativeBackend(self._installation(tmp), runner).validate(artifact)
            self.assertEqual(result.status, ValidationStatus.BACKEND_TIMEOUT)
            self.assertFalse(result.failed)
            self.assertEqual(result.diagnostics, ())

    def test_version_mismatch_is_blocked_before_lint(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            spec = self._installation(tmp)
            (spec.root / "manifest.json").write_text(json.dumps({
                "name": "aoe2-ai-parser",
                "project_version": "0.2.0",
                "commit_sha": spec.commit_sha,
            }), encoding="utf-8")
            artifact = tmp / "Basilisk.per"
            artifact.write_text("(nop)\\n", encoding="utf-8")
            runner = FakeRunner([])
            result = Aoe2NativeBackend(spec, runner).validate(artifact)
            self.assertEqual(result.status, ValidationStatus.BACKEND_VERSION_MISMATCH)
            self.assertEqual(runner.calls, [])

    def test_protocol_fixture_matrix_rejects_invalid_backend_payloads(self):
        cases = (
            ("malformed_json.txt", ValidationStatus.BACKEND_PROTOCOL_ERROR, 0),
            ("finding_count_mismatch.json", ValidationStatus.BACKEND_PROTOCOL_ERROR, 0),
            ("unknown_severity.json", ValidationStatus.BACKEND_PROTOCOL_ERROR, 1),
            ("unknown_confidence.json", ValidationStatus.BACKEND_PROTOCOL_ERROR, 1),
            ("span_missing_coordinate.json", ValidationStatus.BACKEND_PROTOCOL_ERROR, 1),
            ("span_negative.json", ValidationStatus.BACKEND_PROTOCOL_ERROR, 1),
            ("span_end_before_start.json", ValidationStatus.BACKEND_PROTOCOL_ERROR, 1),
            ("span_non_integer.json", ValidationStatus.BACKEND_PROTOCOL_ERROR, 1),
            ("path_mismatch.json", ValidationStatus.BACKEND_PROTOCOL_ERROR, 1),
            ("missing_findings.json", ValidationStatus.BACKEND_PROTOCOL_ERROR, 0),
            ("non_object_finding.json", ValidationStatus.BACKEND_PROTOCOL_ERROR, 1),
        )
        for fixture, expected_status, exit_code in cases:
            with self.subTest(fixture=fixture):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp = Path(tmp_dir)
                    _, runner, result = self._run_fixture(tmp, fixture, exit_code=exit_code)
                    self.assertEqual(result.status, expected_status)
                    self.assertFalse(result.failed)
                    self.assertEqual(result.diagnostics, ())
                    self.assertEqual(len(runner.calls), 2)

    def test_valid_rejection_fixture_preserves_native_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            artifact, _, result = self._run_fixture(tmp, "valid_rejection.json", exit_code=1)
            self.assertEqual(result.status, ValidationStatus.REJECTED)
            self.assertTrue(result.failed)
            self.assertEqual(result.summary.finding_count, 1)
            self.assertEqual(result.summary.error_count, 1)
            self.assertEqual(result.diagnostics[0].code, "command-role-mismatch")
            self.assertEqual(result.diagnostics[0].source, "aoe2-ai-parser")
            self.assertEqual(result.diagnostics[0].source_location.path, artifact.resolve())
            self.assertEqual(result.diagnostics[0].source_location.column, 2)
            self.assertEqual(result.diagnostics[0].source_location.end_column, 7)

    def test_inconsistent_failure_flags_are_protocol_errors(self):
        for fixture, exit_code in (
            ("failed_true_exit_zero.json", 0),
            ("failed_false_exit_nonzero.json", 1),
        ):
            with self.subTest(fixture=fixture):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp = Path(tmp_dir)
                    _, _, result = self._run_fixture(tmp, fixture, exit_code=exit_code)
                    self.assertEqual(result.status, ValidationStatus.BACKEND_PROTOCOL_ERROR)
                    self.assertFalse(result.failed)
                    self.assertEqual(result.diagnostics, ())

    def test_stderr_only_diagnostic_text_is_never_treated_as_native_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            stderr = self._fixture_text("stderr_only.txt")
            _, _, result = self._run_fixture(
                tmp, "malformed_json.txt", exit_code=1, stderr=stderr
            )
            self.assertEqual(result.status, ValidationStatus.BACKEND_PROTOCOL_ERROR)
            self.assertFalse(result.failed)
            self.assertEqual(result.diagnostics, ())
            self.assertIn("not valid JSON", result.stderr)

    def test_timeout_is_not_script_rejection(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            artifact = tmp / "Basilisk.per"
            artifact.write_text("(build castle)\\n", encoding="utf-8")
            runner = FakeRunner([self._python_probe(), TimeoutError("timed out")])
            result = Aoe2NativeBackend(self._installation(tmp), runner).validate(artifact)
            self.assertEqual(result.status, ValidationStatus.BACKEND_TIMEOUT)
            self.assertFalse(result.failed)
            self.assertEqual(result.diagnostics, ())

    def test_backend_process_error_is_distinct_from_native_rejection(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            artifact = tmp / "Basilisk.per"
            artifact.write_text("(nop)\\n", encoding="utf-8")
            runner = FakeRunner([self._python_probe(), OSError("process launch failed")])
            result = Aoe2NativeBackend(self._installation(tmp), runner).validate(artifact)
            self.assertEqual(result.status, ValidationStatus.BACKEND_PROCESS_ERROR)
            self.assertFalse(result.failed)
            self.assertEqual(result.diagnostics, ())

    def test_missing_executable_is_backend_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            spec = self._installation(tmp)
            spec.executable.unlink()
            artifact = tmp / "Basilisk.per"
            artifact.write_text("(nop)\\n", encoding="utf-8")
            runner = FakeRunner([])
            result = Aoe2NativeBackend(spec, runner).validate(artifact)
            self.assertEqual(result.status, ValidationStatus.BACKEND_UNAVAILABLE)
            self.assertFalse(result.failed)
            self.assertEqual(result.diagnostics, ())
            self.assertEqual(runner.calls, [])

    def test_project_and_commit_mismatches_block_before_probe(self):
        for manifest_name, manifest_value in (
            ("project version", "0.2.0"),
            ("commit", "0" * 40),
        ):
            with self.subTest(manifest_name=manifest_name):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp = Path(tmp_dir)
                    spec = self._installation(tmp)
                    manifest = {
                        "name": spec.name,
                        "project_version": spec.project_version if manifest_name == "commit" else manifest_value,
                        "commit_sha": manifest_value if manifest_name == "commit" else spec.commit_sha,
                    }
                    (spec.root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
                    artifact = tmp / "Basilisk.per"
                    artifact.write_text("(nop)\\n", encoding="utf-8")
                    runner = FakeRunner([])
                    result = Aoe2NativeBackend(spec, runner).validate(artifact)
                    self.assertEqual(result.status, ValidationStatus.BACKEND_VERSION_MISMATCH)
                    self.assertFalse(result.failed)
                    self.assertEqual(runner.calls, [])

    def test_python_version_mismatch_is_blocked_before_lint(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            spec = self._installation(tmp)
            artifact = tmp / "Basilisk.per"
            artifact.write_text("(nop)\\n", encoding="utf-8")
            runner = FakeRunner([ProcessOutput("Python 3.11.9\\n", "", 0, 1)])
            result = Aoe2NativeBackend(spec, runner).validate(artifact)
            self.assertEqual(result.status, ValidationStatus.BACKEND_VERSION_MISMATCH)
            self.assertFalse(result.failed)
            self.assertEqual(len(runner.calls), 1)




class LockTests(unittest.TestCase):
    def test_lock_file_loads_pinned_identity(self):
        lock = Path(__file__).parents[1] / "backends" / "aoe2-ai-parser.lock"
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            spec = BackendSpec.from_lock(root, root / "python.exe", lock)
            self.assertEqual(spec.name, "aoe2-ai-parser")
            self.assertEqual(spec.project_version, "0.1.0")
            self.assertEqual(spec.commit_sha, "3dfa2583b7c2ec36b85ccb421ebd0abe9ff276ba")
            self.assertEqual(spec.python_major_minor, "3.12")


if __name__ == "__main__":
    unittest.main()
