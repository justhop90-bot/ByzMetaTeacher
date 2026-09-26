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

    def test_bad_finding_count_is_protocol_error(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            artifact = tmp / "Basilisk.per"
            artifact.write_text("(nop)\\n", encoding="utf-8")
            payload = json.dumps({
                "path": str(artifact),
                "finding_count": 1,
                "findings": [],
                "failed": False,
            })
            runner = FakeRunner([
                self._python_probe(),
                ProcessOutput(payload, "", 0, 4),
            ])
            result = Aoe2NativeBackend(self._installation(tmp), runner).validate(artifact)
            self.assertEqual(result.status, ValidationStatus.BACKEND_PROTOCOL_ERROR)
            self.assertFalse(result.failed)

    def test_backend_process_failure_is_distinct_from_native_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            artifact = tmp / "Basilisk.per"
            artifact.write_text("(nop)\\n", encoding="utf-8")
            runner = FakeRunner([
                self._python_probe(),
                ProcessOutput("", "backend exploded", 2, 4),
            ])
            result = Aoe2NativeBackend(self._installation(tmp), runner).validate(artifact)
            self.assertEqual(result.status, ValidationStatus.BACKEND_PROTOCOL_ERROR)
            self.assertFalse(result.failed)
            self.assertIn("not valid JSON", result.stderr)


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
