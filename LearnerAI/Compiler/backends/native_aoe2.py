"""Process-isolated adapter for the pinned aoe2-ai-parser backend."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import tempfile
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from .errors import BackendProtocolError, BackendUnavailableError, BackendVersionMismatchError
from .models import (
    ArtifactIdentity,
    BackendIdentity,
    DiagnosticConfidence,
    DiagnosticSeverity,
    InvocationResult,
    NativeDiagnostic,
    NativeValidationResult,
    SourceLocation,
    ValidationStatus,
    ValidationSummary,
)

_LOCK_PATH = Path(__file__).with_name("aoe2-ai-parser.lock")
_EXPECTED_MODULE = "aoe2_ai_lab"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class BackendSpec:
    name: str
    project_version: str
    commit_sha: str
    python_major_minor: str
    root: Path
    executable: Path
    timeout_seconds: float = 30.0
    profile: str = "default"

    @classmethod
    def from_lock(
        cls,
        root: Path,
        executable: Path,
        lock_path: Path = _LOCK_PATH,
        timeout_seconds: float = 30.0,
        profile: str = "default",
    ) -> "BackendSpec":
        with lock_path.open("rb") as handle:
            raw = tomllib.load(handle).get("backend", {})
        required = {"name", "project_version", "commit_sha", "python_major_minor"}
        missing = sorted(required - raw.keys())
        if missing:
            raise BackendProtocolError(f"backend lock is missing fields: {', '.join(missing)}")
        return cls(
            name=str(raw["name"]),
            project_version=str(raw["project_version"]),
            commit_sha=str(raw["commit_sha"]),
            python_major_minor=str(raw["python_major_minor"]),
            root=root.resolve(),
            executable=executable.resolve(),
            timeout_seconds=timeout_seconds,
            profile=profile,
        )


@dataclass(frozen=True)
class ProcessOutput:
    stdout: str
    stderr: str
    returncode: int
    duration_ms: int


class ProcessRunner(Protocol):
    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path,
        env: dict[str, str],
        timeout_seconds: float,
    ) -> ProcessOutput:
        ...


class SubprocessRunner:
    """Minimal process boundary: no shell, isolated stdin, deterministic env."""

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path,
        env: dict[str, str],
        timeout_seconds: float,
    ) -> ProcessOutput:
        started = time.monotonic()
        kwargs: dict[str, object] = {
            "args": list(args),
            "cwd": str(cwd),
            "env": env,
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "shell": False,
            "check": False,
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        else:
            kwargs["start_new_session"] = True
        try:
            completed = subprocess.run(timeout=timeout_seconds, **kwargs)
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"native backend timed out after {timeout_seconds:.1f}s") from exc
        return ProcessOutput(
            stdout=completed.stdout,
            stderr=completed.stderr,
            returncode=completed.returncode,
            duration_ms=int((time.monotonic() - started) * 1000),
        )


def _isolated_environment() -> dict[str, str]:
    env = dict(os.environ)
    for key in (
        "PYTHONPATH",
        "PYTHONHOME",
        "PYTHONSTARTUP",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        env.pop(key, None)
    env.update(
        {
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "NO_PROXY": "*",
            "no_proxy": "*",
        }
    )
    return env


def _python_version(executable: Path, runner: ProcessRunner, cwd: Path, timeout: float) -> str:
    result = runner.run(
        (str(executable), "--version"),
        cwd=cwd,
        env=_isolated_environment(),
        timeout_seconds=timeout,
    )
    if result.returncode != 0:
        raise BackendUnavailableError(result.stderr.strip() or "unable to query backend Python version")
    match = re.search(r"Python (\\d+\\.\\d+(?:\\.\\d+)?)", result.stdout + "\\n" + result.stderr)
    if not match:
        raise BackendProtocolError("backend Python --version output is not recognizable")
    return match.group(1)


def _read_manifest(root: Path) -> dict[str, object]:
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise BackendUnavailableError(f"backend manifest not found: {manifest_path}")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackendProtocolError(f"invalid backend manifest: {manifest_path}") from exc
    if not isinstance(payload, dict):
        raise BackendProtocolError("backend manifest root must be an object")
    return payload


def _verify_installation(spec: BackendSpec, runner: ProcessRunner) -> BackendIdentity:
    if not spec.executable.is_file():
        raise BackendUnavailableError(f"backend executable not found: {spec.executable}")
    manifest = _read_manifest(spec.root)
    actual_name = str(manifest.get("name", ""))
    actual_version = str(manifest.get("project_version", ""))
    actual_commit = str(manifest.get("commit_sha", ""))
    if actual_name != spec.name or actual_version != spec.project_version or actual_commit != spec.commit_sha:
        raise BackendVersionMismatchError(
            "backend identity mismatch: "
            f"expected {spec.name} {spec.project_version} {spec.commit_sha}, "
            f"found {actual_name} {actual_version} {actual_commit}"
        )
    python_version = _python_version(spec.executable, runner, spec.root, spec.timeout_seconds)
    if ".".join(python_version.split(".")[:2]) != spec.python_major_minor:
        raise BackendVersionMismatchError(
            f"backend Python mismatch: expected {spec.python_major_minor}, found {python_version}"
        )
    return BackendIdentity(
        name=actual_name,
        project_version=actual_version,
        commit_sha=actual_commit,
        python_version=python_version,
    )


def _artifact_identity(path: Path) -> ArtifactIdentity:
    resolved = path.resolve()
    digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
    return ArtifactIdentity(path=resolved, sha256=digest)


def _normal_path(raw: str, cwd: Path) -> Path:
    path = Path(raw)
    return (path if path.is_absolute() else cwd / path).resolve()


def _diagnostic_id(
    backend: BackendIdentity,
    code: str,
    location: SourceLocation,
    message: str,
) -> str:
    parts = (
        backend.name,
        backend.commit_sha,
        code,
        location.path.as_posix(),
        str(location.line),
        str(location.column),
        str(location.end_line),
        str(location.end_column),
        message,
    )
    return hashlib.sha256("\\0".join(parts).encode("utf-8")).hexdigest()


def _location(raw: object, finding: dict[str, object], cwd: Path) -> SourceLocation:
    raw_path = finding.get("path")
    raw_line = finding.get("line")
    if not isinstance(raw_path, str) or not raw_path:
        raise BackendProtocolError("native diagnostic path must be a non-empty string")
    if not isinstance(raw_line, int) or isinstance(raw_line, bool) or raw_line < 1:
        raise BackendProtocolError("native diagnostic line must be a positive integer")
    path = _normal_path(raw_path, cwd)
    if raw is None:
        return SourceLocation(path, raw_line, None, None, None)
    if not isinstance(raw, dict):
        raise BackendProtocolError("native diagnostic span must be an object or null")
    required = ("start_line", "start_col", "end_line", "end_col")
    if any(key not in raw for key in required):
        raise BackendProtocolError("native diagnostic span is missing coordinates")
    start_line = raw["start_line"]
    start_col = raw["start_col"]
    end_line = raw["end_line"]
    end_col = raw["end_col"]
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in (start_line, start_col, end_line, end_col)):
        raise BackendProtocolError("native diagnostic span coordinates must be integers")
    if min(start_line, end_line, start_col, end_col) < 0 or end_col < start_col:
        raise BackendProtocolError("native diagnostic span coordinates are invalid")
    return SourceLocation(
        path=path,
        line=start_line + 0 if start_line > 0 else raw_line,
        column=start_col + 1,
        end_line=end_line + 0 if end_line > 0 else raw_line,
        end_column=end_col + 1,
    )


def _normalize_diagnostics(
    payload: dict[str, object],
    *,
    backend: BackendIdentity,
    artifact: ArtifactIdentity,
    cwd: Path,
) -> tuple[NativeDiagnostic, ...]:
    raw_findings = payload.get("findings")
    count = payload.get("finding_count")
    if not isinstance(raw_findings, list) or not isinstance(count, int) or isinstance(count, bool):
        raise BackendProtocolError("native JSON must contain findings[] and finding_count")
    if count != len(raw_findings):
        raise BackendProtocolError(
            f"native finding_count mismatch: declared {count}, received {len(raw_findings)}"
        )
    diagnostics: list[NativeDiagnostic] = []
    artifact_path = artifact.path
    for raw_finding in raw_findings:
        if not isinstance(raw_finding, dict):
            raise BackendProtocolError("native finding must be an object")
        code = raw_finding.get("code")
        message = raw_finding.get("message")
        severity = raw_finding.get("severity")
        confidence = raw_finding.get("confidence")
        if not all(isinstance(value, str) and value for value in (code, message, severity, confidence)):
            raise BackendProtocolError("native finding has invalid code/message/severity/confidence")
        try:
            severity_value = DiagnosticSeverity(severity)
            confidence_value = DiagnosticConfidence(confidence)
        except ValueError as exc:
            raise BackendProtocolError("native finding uses an unknown severity or confidence") from exc
        suggestion = raw_finding.get("suggestion")
        if suggestion is not None and not isinstance(suggestion, str):
            raise BackendProtocolError("native finding suggestion must be string or null")
        references = raw_finding.get("references", [])
        if not isinstance(references, list) or any(not isinstance(item, dict) for item in references):
            raise BackendProtocolError("native finding references must be an array of objects")
        location = _location(raw_finding.get("span"), raw_finding, cwd)
        if location.path != artifact_path:
            raise BackendProtocolError(
                f"native diagnostic path escapes staged artifact: {location.path}"
            )
        diagnostic = NativeDiagnostic(
            id=_diagnostic_id(backend, code, location, message),
            source=backend.name,
            code=code,
            severity=severity_value,
            confidence=confidence_value,
            message=message,
            suggestion=suggestion,
            source_location=location,
            references=tuple(dict(item) for item in references),
        )
        diagnostics.append(diagnostic)
    return tuple(diagnostics)


def _summary(diagnostics: tuple[NativeDiagnostic, ...]) -> ValidationSummary:
    return ValidationSummary(
        finding_count=len(diagnostics),
        error_count=sum(item.severity is DiagnosticSeverity.ERROR for item in diagnostics),
        warning_count=sum(item.severity is DiagnosticSeverity.WARNING for item in diagnostics),
        info_count=sum(item.severity is DiagnosticSeverity.INFO for item in diagnostics),
        conditional_count=sum(item.confidence is DiagnosticConfidence.CONDITIONAL for item in diagnostics),
    )


def _empty_summary() -> ValidationSummary:
    return ValidationSummary(0, 0, 0, 0, 0)


class Aoe2NativeBackend:
    """Validate one generated .per file through the pinned external backend."""

    def __init__(self, spec: BackendSpec, runner: ProcessRunner | None = None) -> None:
        self.spec = spec
        self.runner = runner or SubprocessRunner()

    def validate(self, artifact: Path) -> NativeValidationResult:
        artifact_identity = _artifact_identity(artifact)
        invocation = InvocationResult(self.spec.profile, artifact_identity.path, -1, 0)
        fallback_backend = BackendIdentity(
            self.spec.name, self.spec.project_version, self.spec.commit_sha, "unknown"
        )
        try:
            backend = _verify_installation(self.spec, self.runner)
        except BackendUnavailableError as exc:
            return NativeValidationResult(
                ValidationStatus.BACKEND_UNAVAILABLE, False, fallback_backend,
                invocation, artifact_identity, _empty_summary(), (), str(exc),
            )
        except BackendVersionMismatchError as exc:
            return NativeValidationResult(
                ValidationStatus.BACKEND_VERSION_MISMATCH, False, fallback_backend,
                invocation, artifact_identity, _empty_summary(), (), str(exc),
            )
        except TimeoutError as exc:
            return NativeValidationResult(
                ValidationStatus.BACKEND_TIMEOUT, False, fallback_backend,
                invocation, artifact_identity, _empty_summary(), (), str(exc),
            )
        except (BackendProtocolError, OSError) as exc:
            return NativeValidationResult(
                ValidationStatus.BACKEND_PROTOCOL_ERROR, False, fallback_backend,
                invocation, artifact_identity, _empty_summary(), (), str(exc),
            )

        command = (
            str(self.spec.executable), "-m", _EXPECTED_MODULE, "lint",
            str(artifact_identity.path), "--profile", self.spec.profile, "--json",
        )
        try:
            with tempfile.TemporaryDirectory(prefix="learnerai-native-") as temp_dir:
                process = self.runner.run(
                    command,
                    cwd=Path(temp_dir),
                    env=_isolated_environment(),
                    timeout_seconds=self.spec.timeout_seconds,
                )
        except TimeoutError as exc:
            return NativeValidationResult(
                ValidationStatus.BACKEND_TIMEOUT, False, backend,
                invocation, artifact_identity, _empty_summary(), (), str(exc),
            )
        except OSError as exc:
            return NativeValidationResult(
                ValidationStatus.BACKEND_PROCESS_ERROR, False, backend,
                invocation, artifact_identity, _empty_summary(), (), str(exc),
            )

        invocation = InvocationResult(
            self.spec.profile, artifact_identity.path, process.returncode, process.duration_ms
        )
        try:
            payload = json.loads(process.stdout)
        except json.JSONDecodeError as exc:
            return NativeValidationResult(
                ValidationStatus.BACKEND_PROTOCOL_ERROR, False, backend,
                invocation, artifact_identity, _empty_summary(), (),
                f"backend stdout is not valid JSON: {exc}",
            )
        if not isinstance(payload, dict):
            return NativeValidationResult(
                ValidationStatus.BACKEND_PROTOCOL_ERROR, False, backend,
                invocation, artifact_identity, _empty_summary(), (),
                "backend JSON root must be an object",
            )
        failed = payload.get("failed")
        if not isinstance(failed, bool):
            return NativeValidationResult(
                ValidationStatus.BACKEND_PROTOCOL_ERROR, False, backend,
                invocation, artifact_identity, _empty_summary(), (),
                "backend JSON failed field must be boolean",
            )
        try:
            diagnostics = _normalize_diagnostics(
                payload, backend=backend, artifact=artifact_identity,
                cwd=artifact_identity.path.parent,
            )
        except BackendProtocolError as exc:
            return NativeValidationResult(
                ValidationStatus.BACKEND_PROTOCOL_ERROR, False, backend,
                invocation, artifact_identity, _empty_summary(), (), str(exc),
            )
        status = ValidationStatus.REJECTED if failed or diagnostics else ValidationStatus.VALIDATED
        if process.returncode == 0 and failed:
            status = ValidationStatus.BACKEND_PROTOCOL_ERROR
        elif process.returncode != 0 and not failed:
            status = ValidationStatus.BACKEND_PROTOCOL_ERROR
        return NativeValidationResult(
            status, status is ValidationStatus.REJECTED, backend,
            invocation, artifact_identity, _summary(diagnostics), diagnostics,
            process.stderr,
        )
