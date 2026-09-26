#!/usr/bin/env python3
"""Basilisk compiler entry point.

Pipeline: source -> AST -> semantic IR -> deterministic .per.
Optional native validation adds:
    generated .per -> staged artifact -> aoe2-ai-parser -> promotion.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ""):
    compiler_dir = Path(__file__).resolve().parent
    sys.path[:] = [entry for entry in sys.path if Path(entry or ".").resolve() != compiler_dir]
    sys.path.insert(0, str(compiler_dir.parent))
    from Compiler.backends.errors import NativeBackendError
    from Compiler.backends.models import NativeValidationResult, ValidationStatus
    from Compiler.backends.native_aoe2 import Aoe2NativeBackend, BackendSpec
    from Compiler.errors import CompileError
    from Compiler.parser import parse
    from Compiler.primitives import default_de_registry
    from Compiler.semantic import analyze
    from Compiler.emitter import emit
else:
    from .backends.errors import NativeBackendError
    from .backends.models import NativeValidationResult, ValidationStatus
    from .backends.native_aoe2 import Aoe2NativeBackend, BackendSpec
    from .errors import CompileError
    from .parser import parse
    from .primitives import default_de_registry
    from .semantic import analyze
    from .emitter import emit


_DEFAULT_NATIVE_BACKEND_ROOT = (
    Path(__file__).resolve().parents[2] / "tools" / "native-backends" / "aoe2-ai-parser"
)


def compile_source(source: str, base_goal: int = 1000) -> str:
    ast = parse(source)
    ir = analyze(ast, default_de_registry(), base_goal)
    return emit(ir)


def compile_to_file(
    source: str,
    output: Path,
    *,
    base_goal: int = 1000,
    native_backend: Aoe2NativeBackend | None = None,
) -> NativeValidationResult | None:
    """Compile source and optionally promote it only after native validation passes."""
    result = compile_source(source, base_goal)
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    if native_backend is None:
        output.write_text(result, encoding="utf-8")
        return None

    fd, staged_name = tempfile.mkstemp(
        prefix=f".{output.stem}.",
        suffix=".per.stage",
        dir=output.parent,
    )
    os.close(fd)
    staged = Path(staged_name)
    try:
        staged.write_text(result, encoding="utf-8")
        validation = native_backend.validate(staged)
        if validation.status is ValidationStatus.VALIDATED:
            os.replace(staged, output)
        return validation
    finally:
        staged.unlink(missing_ok=True)


def _default_backend_python(root: Path) -> Path:
    if os.name == "nt":
        return root / "venv" / "Scripts" / "python.exe"
    return root / "venv" / "bin" / "python"


def _build_native_backend(
    root: Path,
    executable: Path | None,
    timeout_seconds: float,
    profile: str,
) -> Aoe2NativeBackend:
    backend_root = root.resolve()
    backend_python = (executable or _default_backend_python(backend_root)).resolve()
    spec = BackendSpec.from_lock(
        backend_root,
        backend_python,
        timeout_seconds=timeout_seconds,
        profile=profile,
    )
    return Aoe2NativeBackend(spec)


def _native_result_payload(result: NativeValidationResult) -> dict[str, object]:
    return {
        "status": result.status.value,
        "failed": result.failed,
        "backend": {
            "name": result.backend.name,
            "project_version": result.backend.project_version,
            "commit_sha": result.backend.commit_sha,
            "python_version": result.backend.python_version,
        },
        "invocation": {
            "profile": result.invocation.profile,
            "path": str(result.invocation.path),
            "exit_code": result.invocation.exit_code,
            "duration_ms": result.invocation.duration_ms,
        },
        "artifact": {
            "path": str(result.artifact.path),
            "sha256": result.artifact.sha256,
        },
        "summary": {
            "finding_count": result.summary.finding_count,
            "error_count": result.summary.error_count,
            "warning_count": result.summary.warning_count,
            "info_count": result.summary.info_count,
            "conditional_count": result.summary.conditional_count,
        },
        "diagnostics": [
            {
                "id": item.id,
                "source": item.source,
                "code": item.code,
                "severity": item.severity.value,
                "confidence": item.confidence.value,
                "message": item.message,
                "suggestion": item.suggestion,
                "source_location": {
                    "path": str(item.source_location.path),
                    "line": item.source_location.line,
                    "column": item.source_location.column,
                    "end_line": item.source_location.end_line,
                    "end_column": item.source_location.end_column,
                },
                "references": list(item.references),
            }
            for item in result.diagnostics
        ],
        "stderr": result.stderr,
    }


def _print_native_result(result: NativeValidationResult, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(_native_result_payload(result), indent=2, sort_keys=True))
        return
    print(f"native validation: {result.status.value}")
    for diagnostic in result.diagnostics:
        location = diagnostic.source_location
        if location.column is None:
            position = f"{location.path}:{location.line}"
        else:
            position = f"{location.path}:{location.line}:{location.column}"
        print(f"{position}: {diagnostic.severity.value} {diagnostic.code}: {diagnostic.message}", file=sys.stderr)
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Compile Basilisk demand DSL to .per")
    ap.add_argument("source", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--base-goal", type=int, default=1000)
    ap.add_argument(
        "--validate-native",
        action="store_true",
        help="validate the staged .per with the pinned aoe2-ai-parser backend before promotion",
    )
    ap.add_argument(
        "--native-backend-root",
        type=Path,
        default=_DEFAULT_NATIVE_BACKEND_ROOT,
        help="installed aoe2-ai-parser backend root",
    )
    ap.add_argument(
        "--native-backend-python",
        type=Path,
        help="backend virtual-environment Python executable; defaults to the platform venv path",
    )
    ap.add_argument(
        "--native-timeout",
        type=float,
        default=30.0,
        help="native backend timeout in seconds",
    )
    ap.add_argument(
        "--native-profile",
        choices=["default", "corpus"],
        default="default",
        help="native backend lint profile",
    )
    ap.add_argument(
        "--native-json",
        action="store_true",
        help="print normalized native validation JSON",
    )
    args = ap.parse_args()

    try:
        native_backend = None
        if args.validate_native:
            native_backend = _build_native_backend(
                args.native_backend_root,
                args.native_backend_python,
                args.native_timeout,
                args.native_profile,
            )
        validation = compile_to_file(
            args.source.read_text(encoding="utf-8"),
            args.output,
            base_goal=args.base_goal,
            native_backend=native_backend,
        )
    except (OSError, CompileError, NativeBackendError, ValueError) as exc:
        ap.error(str(exc))

    if validation is None:
        return 0

    _print_native_result(validation, as_json=args.native_json)
    if validation.status is ValidationStatus.VALIDATED:
        return 0
    if validation.status is ValidationStatus.REJECTED:
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
