"""Combined semantic/native compiler diagnostics and exit-state model."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .backends.models import NativeDiagnostic, NativeValidationResult, ValidationStatus


class DiagnosticSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class DiagnosticSource(str, Enum):
    LEARNERAI = "LearnerAI"
    NATIVE = "aoe2-ai-parser"


class ReportStatus(str, Enum):
    SEMANTIC_VALIDATED = "SEMANTIC_VALIDATED"
    VALIDATED = "VALIDATED"
    SEMANTIC_REJECTED = "SEMANTIC_REJECTED"
    NATIVE_REJECTED = "NATIVE_REJECTED"
    BACKEND_FAILURE = "BACKEND_FAILURE"


@dataclass(frozen=True)
class SemanticDiagnostic:
    id: str
    source: DiagnosticSource
    code: str
    severity: DiagnosticSeverity
    message: str
    path: Path | None = None
    line: int | None = None
    column: int | None = None
    end_line: int | None = None
    end_column: int | None = None


@dataclass(frozen=True)
class ReportDiagnostic:
    id: str
    source: DiagnosticSource
    code: str
    severity: DiagnosticSeverity
    confidence: str | None
    message: str
    suggestion: str | None
    path: Path | None
    line: int | None
    column: int | None
    end_line: int | None
    end_column: int | None
    references: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class CombinedValidationReport:
    status: ReportStatus
    diagnostics: tuple[ReportDiagnostic, ...]
    native_result: NativeValidationResult | None
    output_path: Path

    @property
    def semantic_diagnostics(self) -> tuple[ReportDiagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.source is DiagnosticSource.LEARNERAI)

    @property
    def native_diagnostics(self) -> tuple[ReportDiagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.source is DiagnosticSource.NATIVE)

    def to_dict(self) -> dict[str, object]:
        native = None
        if self.native_result is not None:
            native = {
                "status": self.native_result.status.value,
                "failed": self.native_result.failed,
                "backend": {
                    "name": self.native_result.backend.name,
                    "project_version": self.native_result.backend.project_version,
                    "commit_sha": self.native_result.backend.commit_sha,
                    "python_version": self.native_result.backend.python_version,
                },
                "invocation": {
                    "profile": self.native_result.invocation.profile,
                    "path": str(self.native_result.invocation.path),
                    "exit_code": self.native_result.invocation.exit_code,
                    "duration_ms": self.native_result.invocation.duration_ms,
                },
                "artifact": {
                    "path": str(self.native_result.artifact.path),
                    "sha256": self.native_result.artifact.sha256,
                },
                "summary": {
                    "finding_count": self.native_result.summary.finding_count,
                    "error_count": self.native_result.summary.error_count,
                    "warning_count": self.native_result.summary.warning_count,
                    "info_count": self.native_result.summary.info_count,
                    "conditional_count": self.native_result.summary.conditional_count,
                },
                "stderr": self.native_result.stderr,
            }
        return {
            "status": self.status.value,
            "output_path": str(self.output_path),
            "diagnostics": [
                {
                    "id": item.id,
                    "source": item.source.value,
                    "code": item.code,
                    "severity": item.severity.value,
                    "confidence": item.confidence,
                    "message": item.message,
                    "suggestion": item.suggestion,
                    "path": str(item.path) if item.path is not None else None,
                    "line": item.line,
                    "column": item.column,
                    "end_line": item.end_line,
                    "end_column": item.end_column,
                    "references": list(item.references),
                }
                for item in self.diagnostics
            ],
            "native": native,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def _semantic_id(code: str, message: str) -> str:
    return hashlib.sha256(f"LearnerAI\x00{code}\x00{message}".encode("utf-8")).hexdigest()


def semantic_diagnostic(error: Exception) -> SemanticDiagnostic:
    text = str(error).strip() or error.__class__.__name__
    code = "SEMANTIC-COMPILE-ERROR"
    if ": " in text:
        prefix, _ = text.split(": ", 1)
        if prefix and all(ch.isupper() or ch.isdigit() or ch == "-" for ch in prefix):
            code = prefix
    return SemanticDiagnostic(
        id=_semantic_id(code, text),
        source=DiagnosticSource.LEARNERAI,
        code=code,
        severity=DiagnosticSeverity.ERROR,
        message=text,
    )


def _from_semantic(item: SemanticDiagnostic) -> ReportDiagnostic:
    return ReportDiagnostic(
        id=item.id,
        source=item.source,
        code=item.code,
        severity=item.severity,
        confidence=None,
        message=item.message,
        suggestion=None,
        path=item.path,
        line=item.line,
        column=item.column,
        end_line=item.end_line,
        end_column=item.end_column,
        references=(),
    )


def _from_native(item: NativeDiagnostic) -> ReportDiagnostic:
    location = item.source_location
    return ReportDiagnostic(
        id=item.id,
        source=DiagnosticSource.NATIVE,
        code=item.code,
        severity=DiagnosticSeverity(item.severity.value),
        confidence=item.confidence.value,
        message=item.message,
        suggestion=item.suggestion,
        path=location.path,
        line=location.line,
        column=location.column,
        end_line=location.end_line,
        end_column=location.end_column,
        references=item.references,
    )


_SOURCE_ORDER = {
    DiagnosticSource.LEARNERAI: 0,
    DiagnosticSource.NATIVE: 1,
}
_SEVERITY_ORDER = {
    DiagnosticSeverity.ERROR: 0,
    DiagnosticSeverity.WARNING: 1,
    DiagnosticSeverity.INFO: 2,
}


def _diagnostic_sort_key(item: ReportDiagnostic) -> tuple[object, ...]:
    return (
        _SOURCE_ORDER[item.source],
        str(item.path or ""),
        item.line if item.line is not None else 0,
        item.column if item.column is not None else 0,
        _SEVERITY_ORDER[item.severity],
        item.code,
        item.message,
        item.id,
    )


def order_diagnostics(
    semantic: tuple[SemanticDiagnostic, ...] = (),
    native: tuple[NativeDiagnostic, ...] = (),
) -> tuple[ReportDiagnostic, ...]:
    combined = [_from_semantic(item) for item in semantic]
    combined.extend(_from_native(item) for item in native)
    return tuple(sorted(combined, key=_diagnostic_sort_key))


def exit_code_for_report(report: CombinedValidationReport) -> int:
    if report.status in {ReportStatus.SEMANTIC_VALIDATED, ReportStatus.VALIDATED}:
        return 0
    if report.status in {ReportStatus.SEMANTIC_REJECTED, ReportStatus.NATIVE_REJECTED}:
        return 1
    return 2


def report_from_native_result(
    native_result: NativeValidationResult,
    output_path: Path,
    semantic: tuple[SemanticDiagnostic, ...] = (),
) -> CombinedValidationReport:
    clean = (
        native_result.status is ValidationStatus.VALIDATED
        and not native_result.failed
        and native_result.summary.finding_count == 0
        and not native_result.diagnostics
    )
    if clean:
        status = ReportStatus.VALIDATED
    elif native_result.status is ValidationStatus.REJECTED:
        status = ReportStatus.NATIVE_REJECTED
    elif native_result.status is ValidationStatus.VALIDATED:
        status = ReportStatus.BACKEND_FAILURE
    else:
        status = ReportStatus.BACKEND_FAILURE
    return CombinedValidationReport(
        status=status,
        diagnostics=order_diagnostics(semantic, native_result.diagnostics),
        native_result=native_result,
        output_path=output_path.resolve(),
    )


def semantic_failure_report(error: Exception, output_path: Path) -> CombinedValidationReport:
    diagnostic = semantic_diagnostic(error)
    return CombinedValidationReport(
        status=ReportStatus.SEMANTIC_REJECTED,
        diagnostics=order_diagnostics((diagnostic,), ()),
        native_result=None,
        output_path=output_path.resolve(),
    )

def backend_failure_report(
    message: str,
    output_path: Path,
) -> CombinedValidationReport:
    code = "NATIVE-VALIDATION-REQUIRED"
    diagnostic = ReportDiagnostic(
        id=_semantic_id(code, message),
        source=DiagnosticSource.NATIVE,
        code=code,
        severity=DiagnosticSeverity.ERROR,
        confidence=None,
        message=message,
        suggestion="Provide the pinned native aoe2-ai-parser backend before promoting an artifact.",
        path=output_path.resolve(),
        line=None,
        column=None,
        end_line=None,
        end_column=None,
        references=(),
    )
    return CombinedValidationReport(
        status=ReportStatus.BACKEND_FAILURE,
        diagnostics=(diagnostic,),
        native_result=None,
        output_path=output_path.resolve(),
    )
