#!/usr/bin/env python3
"""Basilisk compiler entry point.

Pipeline: source -> AST -> semantic IR -> deterministic .per.
Optional native validation adds:
    generated .per -> staged artifact -> aoe2-ai-parser -> promotion.
"""
from __future__ import annotations

import argparse
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
    from Compiler.diagnostics import (
        CombinedValidationReport,
        ReportStatus,
        exit_code_for_report,
        report_from_native_result,
        semantic_failure_report,
    )
    from Compiler.backends.native_aoe2 import Aoe2NativeBackend, BackendSpec
    from Compiler.errors import CompileError
    from Compiler.parser import parse
    from Compiler.primitives import default_de_registry
    from Compiler.semantic import analyze
    from Compiler.semantic.demand_ownership import validate_demand_ownership
    from Compiler.semantic.capability_bridge import project_capability_graph
    from Compiler.semantic.capability_validation import validate_capability_graph
    from Compiler.semantic.resource_conflicts import validate_resource_conflicts
    from Compiler.emitter import emit
    from Compiler.runtime_binding import BindingContext, RuntimeBinder
else:
    from .backends.errors import NativeBackendError
    from .backends.models import NativeValidationResult, ValidationStatus
    from .diagnostics import (
        CombinedValidationReport,
        ReportStatus,
        exit_code_for_report,
        report_from_native_result,
        semantic_failure_report,
    )
    from .backends.native_aoe2 import Aoe2NativeBackend, BackendSpec
    from .errors import CompileError
    from .parser import parse
    from .primitives import default_de_registry
    from .semantic import analyze
    from .semantic.demand_ownership import validate_demand_ownership
    from .semantic.capability_bridge import project_capability_graph
    from .semantic.capability_validation import validate_capability_graph
    from .semantic.resource_conflicts import validate_resource_conflicts
    from .emitter import emit
    from .runtime_binding import BindingContext, RuntimeBinder


_DEFAULT_NATIVE_BACKEND_ROOT = (
    Path(__file__).resolve().parents[2] / "tools" / "native-backends" / "aoe2-ai-parser"
)


def _storage_requests(ir):
    requests = []
    seen = set()
    for demand in ir:
        for request in (demand.lifecycle.slot, demand.action.arbitration_request):
            if request is None or request.request_id in seen:
                continue
            seen.add(request.request_id)
            requests.append(request)
    return tuple(requests)

def _compile_source_parts(
    source: str,
    base_goal: int = 1000,
    *,
    source_unit: str = "<source>",
    binding_context: BindingContext | None = None,
):
    ast = parse(source)
    registry = default_de_registry()
    ir = analyze(ast, registry, source_unit=source_unit)
    ownership_report = validate_demand_ownership(ir)
    if ownership_report.errors:
        diagnostic = ownership_report.errors[0]
        raise CompileError(f"{diagnostic.code.value}: {diagnostic.message}")
    capability_graph = project_capability_graph(ir, registry)
    resource_report = validate_resource_conflicts(capability_graph, registry)
    if resource_report.errors:
        diagnostic = resource_report.errors[0]
        raise CompileError(f"{diagnostic.code.value}: {diagnostic.message}")
    capability_report = validate_capability_graph(capability_graph, registry)
    if capability_report.errors:
        diagnostic = capability_report.errors[0]
        raise CompileError(f"{diagnostic.code.value}: {diagnostic.message}")
    context = binding_context or BindingContext()
    bindings = RuntimeBinder(base_goal=base_goal).bind(
        _storage_requests(ir),
        context,
    )
    return emit(ir, bindings), bindings, context


def _binding_manifest_text(bindings, context: BindingContext) -> str:
    return bindings.to_manifest(
        package_inventory_sha=context.package_inventory_sha,
        allocator_version=context.allocator_version,
    ).to_json()


def compile_source(
    source: str,
    base_goal: int = 1000,
    *,
    source_unit: str = "<source>",
    binding_context: BindingContext | None = None,
) -> str:
    result, _bindings, _context = _compile_source_parts(
        source,
        base_goal,
        source_unit=source_unit,
        binding_context=binding_context,
    )
    return result


def compile_source_with_report(
    source: str,
    output: Path,
    *,
    base_goal: int = 1000,
    native_backend: Aoe2NativeBackend | None = None,
    source_unit: str = "<source>",
    binding_context: BindingContext | None = None,
    binding_manifest: Path | None = None,
) -> CombinedValidationReport:
    """Compile and return one deterministic semantic/native validation report."""
    try:
        result, bindings, context = _compile_source_parts(
            source,
            base_goal,
            source_unit=source_unit,
            binding_context=binding_context,
        )
        manifest_text = _binding_manifest_text(bindings, context)
    except (CompileError, OSError, ValueError) as exc:
        return semantic_failure_report(exc, output)

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if binding_manifest is not None:
        binding_manifest = binding_manifest.resolve()
        binding_manifest.parent.mkdir(parents=True, exist_ok=True)
        if binding_manifest == output:
            raise ValueError("binding manifest path must differ from .per output path")

    if native_backend is None:
        output.write_text(result, encoding="utf-8")
        if binding_manifest is not None:
            binding_manifest.write_text(manifest_text, encoding="utf-8")
        return CombinedValidationReport(
            status=ReportStatus.SEMANTIC_VALIDATED,
            diagnostics=(),
            native_result=None,
            output_path=output,
        )

    fd, staged_name = tempfile.mkstemp(
        prefix=f".{output.stem}.",
        suffix=".per.stage",
        dir=output.parent,
    )
    os.close(fd)
    staged = Path(staged_name)
    staged_manifest = None
    if binding_manifest is not None:
        fd, staged_manifest_name = tempfile.mkstemp(
            prefix=f".{binding_manifest.stem}.",
            suffix=".json.stage",
            dir=binding_manifest.parent,
        )
        os.close(fd)
        staged_manifest = Path(staged_manifest_name)

    try:
        staged.write_text(result, encoding="utf-8")
        if staged_manifest is not None:
            staged_manifest.write_text(manifest_text, encoding="utf-8")
        native_result = native_backend.validate(staged)
        report = report_from_native_result(native_result, output)
        if report.status is ReportStatus.VALIDATED:
            os.replace(staged, output)
            if staged_manifest is not None:
                os.replace(staged_manifest, binding_manifest)
        return report
    finally:
        staged.unlink(missing_ok=True)
        if staged_manifest is not None:
            staged_manifest.unlink(missing_ok=True)


def compile_to_file(
    source: str,
    output: Path,
    *,
    base_goal: int = 1000,
    native_backend: Aoe2NativeBackend | None = None,
    source_unit: str = "<source>",
    binding_context: BindingContext | None = None,
    binding_manifest: Path | None = None,
) -> NativeValidationResult | None:
    """Backward-compatible compile API; semantic errors still raise."""
    result, bindings, context = _compile_source_parts(
        source,
        base_goal,
        source_unit=source_unit,
        binding_context=binding_context,
    )
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_text = _binding_manifest_text(bindings, context)

    if binding_manifest is not None:
        binding_manifest = binding_manifest.resolve()
        binding_manifest.parent.mkdir(parents=True, exist_ok=True)
        if binding_manifest == output:
            raise ValueError("binding manifest path must differ from .per output path")

    if native_backend is None:
        output.write_text(result, encoding="utf-8")
        if binding_manifest is not None:
            binding_manifest.write_text(manifest_text, encoding="utf-8")
        return None

    fd, staged_name = tempfile.mkstemp(
        prefix=f".{output.stem}.",
        suffix=".per.stage",
        dir=output.parent,
    )
    os.close(fd)
    staged = Path(staged_name)
    staged_manifest = None
    if binding_manifest is not None:
        fd, staged_manifest_name = tempfile.mkstemp(
            prefix=f".{binding_manifest.stem}.",
            suffix=".json.stage",
            dir=binding_manifest.parent,
        )
        os.close(fd)
        staged_manifest = Path(staged_manifest_name)

    try:
        staged.write_text(result, encoding="utf-8")
        if staged_manifest is not None:
            staged_manifest.write_text(manifest_text, encoding="utf-8")
        validation = native_backend.validate(staged)
        if validation.status is ValidationStatus.VALIDATED:
            os.replace(staged, output)
            if staged_manifest is not None:
                os.replace(staged_manifest, binding_manifest)
        return validation
    finally:
        staged.unlink(missing_ok=True)
        if staged_manifest is not None:
            staged_manifest.unlink(missing_ok=True)

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


def main() -> int:
    ap = argparse.ArgumentParser(description="Compile Basilisk demand DSL to .per")
    ap.add_argument("source", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--base-goal", type=int, default=1000)
    ap.add_argument(
        "--binding-manifest",
        type=Path,
        help="optional deterministic JSON artifact containing resolved runtime bindings",
    )
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
        report = compile_source_with_report(
            args.source.read_text(encoding="utf-8"),
            args.output,
            base_goal=args.base_goal,
            native_backend=native_backend,
            source_unit=str(args.source.resolve()),
            binding_manifest=args.binding_manifest,
        )
    except (OSError, NativeBackendError, ValueError) as exc:
        ap.error(str(exc))

    if args.native_json:
        print(report.to_json())
    else:
        print(f"validation: {report.status.value}")
        for diagnostic in report.diagnostics:
            position = str(diagnostic.path) if diagnostic.path is not None else "<source>"
            if diagnostic.line is not None:
                position += f":{diagnostic.line}"
                if diagnostic.column is not None:
                    position += f":{diagnostic.column}"
            print(
                f"{position}: [{diagnostic.source.value}] "
                f"{diagnostic.severity.value} {diagnostic.code}: {diagnostic.message}",
                file=sys.stderr,
            )
        if report.native_result is not None and report.native_result.stderr:
            print(
                report.native_result.stderr,
                file=sys.stderr,
                end="" if report.native_result.stderr.endswith("\n") else "\n",
            )

    return exit_code_for_report(report)
if __name__ == "__main__":
    raise SystemExit(main())
