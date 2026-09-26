"""Typed result models for external native validation."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ValidationStatus(str, Enum):
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    BACKEND_VERSION_MISMATCH = "BACKEND_VERSION_MISMATCH"
    BACKEND_PROTOCOL_ERROR = "BACKEND_PROTOCOL_ERROR"
    BACKEND_TIMEOUT = "BACKEND_TIMEOUT"
    BACKEND_PROCESS_ERROR = "BACKEND_PROCESS_ERROR"


class DiagnosticSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class DiagnosticConfidence(str, Enum):
    DEFINITE = "definite"
    CONDITIONAL = "conditional"


@dataclass(frozen=True)
class SourceLocation:
    path: Path
    line: int | None
    column: int | None
    end_line: int | None
    end_column: int | None


@dataclass(frozen=True)
class NativeDiagnostic:
    id: str
    source: str
    code: str
    severity: DiagnosticSeverity
    confidence: DiagnosticConfidence
    message: str
    suggestion: str | None
    source_location: SourceLocation
    references: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class BackendIdentity:
    name: str
    project_version: str
    commit_sha: str
    python_version: str


@dataclass(frozen=True)
class InvocationResult:
    profile: str
    path: Path
    exit_code: int
    duration_ms: int


@dataclass(frozen=True)
class ArtifactIdentity:
    path: Path
    sha256: str


@dataclass(frozen=True)
class ValidationSummary:
    finding_count: int
    error_count: int
    warning_count: int
    info_count: int
    conditional_count: int


@dataclass(frozen=True)
class NativeValidationResult:
    status: ValidationStatus
    failed: bool
    backend: BackendIdentity
    invocation: InvocationResult
    artifact: ArtifactIdentity
    summary: ValidationSummary
    diagnostics: tuple[NativeDiagnostic, ...]
    stderr: str = ""
