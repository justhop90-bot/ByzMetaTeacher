#!/usr/bin/env python3
"""AoE2 .per compiler entry point.

Pipeline: source -> AST -> semantic IR -> deterministic .per.
Artifact promotion requires the pinned aoe2-ai-parser validation gate:
    generated .per -> staged artifact -> aoe2-ai-parser -> zero findings -> promotion.
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
    from dataclasses import replace
    from Compiler.backends.errors import NativeBackendError
    from Compiler.backends.models import NativeValidationResult, ValidationStatus
    from Compiler.artifact_diagnostics import append_persistent_rule_diagnostics
    from Compiler.diagnostics import (
        CombinedValidationReport,
        ReportStatus,
        backend_failure_report,
        exit_code_for_report,
        report_from_native_result,
        semantic_diagnostic,
        semantic_diagnostic_from_validator,
        semantic_failure_report,
    )
    from Compiler.backends.native_aoe2 import Aoe2NativeBackend, BackendSpec
    from Compiler.errors import CompileError
    from Compiler.parser import parse
    from Compiler.primitives import PrimitiveRegistry, default_de_registry
    from Compiler.semantic import analyze
    from Compiler.semantic.community_engine import default_community_engine_registry
    from Compiler.semantic.demand_ownership import validate_demand_ownership
    from Compiler.semantic.source_order import validate_non_lifecycle_source_order
    from Compiler.semantic.action_issuance import validate_action_issuance
    from Compiler.semantic.completion_witness import validate_completion_witnesses
    from Compiler.semantic.construction import canonicalize_construction_witnesses
    from Compiler.semantic.release_state import validate_release_states
    from Compiler.semantic.invalidation import validate_invalidation_contracts
    from Compiler.semantic.capability_bridge import project_capability_graph
    from Compiler.semantic.capability_validation import validate_capability_graph
    from Compiler.semantic.resource_conflicts import validate_resource_conflicts
    from Compiler.semantic.persistent_state import analyze_persistent_state
    from Compiler.semantic.strategic_number_semantics import (
        StrategicNumberCompilationError,
        analyze_strategic_number_expressions,
    )
    from Compiler.semantic.rule_diagnostics import analyze_rule_diagnostics
    from Compiler.semantic.duc import analyze_duc
    from Compiler.semantic.rule_execution import analyze_effective_rules
    from Compiler.semantic.recurrent_execution import analyze_recurrent_execution
    from Compiler.semantic.native_control import validate_native_control_plan
    from Compiler.emitter import emit
    from Compiler.ir import NativeDucPlan
    from Compiler.runtime_binding import BindingContext, RuntimeBinder, StrategicNumberRequest, StrategicNumberSlot
    from Compiler.primitives.strategic_number_catalog import default_strategic_number_inventory
    from Compiler.source_graph import EffectiveSourceGraph, SourceGraphRequest, SourceGraphResolver
    from Compiler.semantic.source_graph_validation import (
        SourceGraphValidationError,
        validate_effective_source_graph,
    )
else:
    from dataclasses import replace
    from .backends.errors import NativeBackendError
    from .backends.models import NativeValidationResult, ValidationStatus
    from .artifact_diagnostics import append_persistent_rule_diagnostics
    from .diagnostics import (
        CombinedValidationReport,
        ReportStatus,
        backend_failure_report,
        exit_code_for_report,
        report_from_native_result,
        semantic_diagnostic,
        semantic_diagnostic_from_validator,
        semantic_failure_report,
    )
    from .backends.native_aoe2 import Aoe2NativeBackend, BackendSpec
    from .errors import CompileError
    from .parser import parse
    from .primitives import PrimitiveRegistry, default_de_registry
    from .semantic import analyze
    from .semantic.community_engine import default_community_engine_registry
    from .semantic.demand_ownership import validate_demand_ownership
    from .semantic.source_order import validate_non_lifecycle_source_order
    from .semantic.action_issuance import validate_action_issuance
    from .semantic.completion_witness import validate_completion_witnesses
    from .semantic.construction import canonicalize_construction_witnesses
    from .semantic.release_state import validate_release_states
    from .semantic.invalidation import validate_invalidation_contracts
    from .semantic.capability_bridge import project_capability_graph
    from .semantic.capability_validation import validate_capability_graph
    from .semantic.resource_conflicts import validate_resource_conflicts
    from .semantic.persistent_state import analyze_persistent_state
    from .semantic.strategic_number_semantics import (
        StrategicNumberCompilationError,
        analyze_strategic_number_expressions,
    )
    from .semantic.rule_diagnostics import analyze_rule_diagnostics
    from .semantic.duc import analyze_duc
    from .semantic.rule_execution import analyze_effective_rules
    from .semantic.recurrent_execution import analyze_recurrent_execution
    from .semantic.native_control import validate_native_control_plan
    from .emitter import emit
    from .ir import NativeDucPlan
    from .runtime_binding import BindingContext, RuntimeBinder, StrategicNumberRequest, StrategicNumberSlot
    from .primitives.strategic_number_catalog import default_strategic_number_inventory
    from .source_graph import EffectiveSourceGraph, SourceGraphRequest, SourceGraphResolver
    from .semantic.source_graph_validation import (
        SourceGraphValidationError,
        validate_effective_source_graph,
    )


_DEFAULT_NATIVE_BACKEND_ROOT = (
    Path(__file__).resolve().parents[2] / "tools" / "native-backends" / "aoe2-ai-parser"
)


def _compiler_owned_state_identifiers(generated_source: str) -> frozenset[str]:
    ignored: set[str] = set()
    for line in generated_source.splitlines():
        stripped = line.strip()
        if not stripped.startswith("(defconst "):
            continue
        fields = stripped.rstrip(")").split()
        if len(fields) < 2:
            continue
        identifier = fields[1]
        if identifier.startswith(
            (
                "demand-",
                "issued-",
                "pending-",
                "complete-",
                "cancelled-",
                "action-claim-",
                "construction-retry-barrier-",
            )
        ):
            ignored.add(identifier)
    return frozenset(ignored)


def _storage_requests(ir, control_plan=None):
    requests = []
    seen = set()
    for demand in ir:
        for request in (
            demand.lifecycle.slot,
            demand.construction_retry_barrier,
            demand.action.arbitration_request,
            *(state.request for state in demand.strategic_number_states),
        ):
            if request is None or request.request_id in seen:
                continue
            seen.add(request.request_id)
            requests.append(request)
    if control_plan is not None:
        for request in control_plan.storage_requests:
            if request.request_id in seen:
                continue
            seen.add(request.request_id)
            requests.append(request)
    return tuple(requests)

def _semantic_compile_failure(
    diagnostics,
) -> CompileError:
    ordered = tuple(
        sorted(
            diagnostics,
            key=lambda item: (
                str(item.path or ""),
                item.line if item.line is not None else 0,
                item.column if item.column is not None else 0,
                item.code,
                item.message,
                item.id,
            ),
        )
    )
    lines = []
    for item in ordered:
        position = str(item.path or "<source>")
        if item.line is not None:
            position += f":{item.line}"
            if item.column is not None:
                position += f":{item.column}"
        lines.append(f"{position}: {item.code}: {item.message}")
    return CompileError(
        "\n".join(lines),
        diagnostics=ordered,
    )


def _compile_ir_parts(
    ir,
    registry,
    base_goal: int = 41,
    *,
    binding_context: BindingContext | None = None,
    control_plan=None,
    duc_plan: NativeDucPlan | None = None,
):
    reports = []

    # Validate the compiler's evidence registry before semantic compilation.
    # This is a registry-integrity gate, not proof that every native construct
    # has been semantically mapped; construct-level semantic mapping is a
    # separate frontier tracked by the Philosopher's Stone architecture.
    default_community_engine_registry().validate()

    ownership_report = validate_demand_ownership(ir)
    reports.append(ownership_report)

    source_order_report = validate_non_lifecycle_source_order(ir)
    reports.append(source_order_report)

    witness_report = validate_completion_witnesses(ir, registry)
    reports.append(witness_report)
    if witness_report.valid:
        ir = canonicalize_construction_witnesses(ir)

    release_report = validate_release_states(ir, registry)
    reports.append(release_report)

    invalidation_report = validate_invalidation_contracts(ir, registry)
    reports.append(invalidation_report)

    issuance_report = validate_action_issuance(ir, registry)
    reports.append(issuance_report)

    graph_failure: SemanticDiagnostic | None = None
    capability_graph = None
    try:
        capability_graph = project_capability_graph(ir, registry)
    except CompileError as exc:
        embedded = tuple(getattr(exc, "diagnostics", ()))
        if embedded:
            graph_failure = embedded[0]
        else:
            graph_failure = semantic_diagnostic(exc)

    if capability_graph is not None:
        resource_report = validate_resource_conflicts(capability_graph, registry)
        reports.append(resource_report)

        capability_report = validate_capability_graph(capability_graph, registry)
        reports.append(capability_report)

    fallback_source_unit = (
        ir[0].identity.source_unit
        if ir
        else "<source>"
    )
    semantic_diagnostics = list(
        semantic_diagnostic_from_validator(
            diagnostic,
            fallback_source_unit=fallback_source_unit,
        )
        for report in reports
        for diagnostic in report.errors
    )
    if graph_failure is not None:
        semantic_diagnostics.append(graph_failure)
    if semantic_diagnostics:
        raise _semantic_compile_failure(semantic_diagnostics)

    if control_plan is not None:
        try:
            validate_native_control_plan(control_plan, registry)
        except (TypeError, ValueError) as exc:
            raise CompileError(f"CONTROL-PLANE-VALIDATION: {exc}") from exc

    context = binding_context or BindingContext()
    if duc_plan is not None and not isinstance(duc_plan, NativeDucPlan):
        raise TypeError("duc_plan must be a NativeDucPlan")
    storage_requests = _storage_requests(ir, control_plan)
    if any(
        isinstance(request, StrategicNumberRequest)
        for request in storage_requests
    ) and context.strategic_number_inventory is None:
        context = replace(
            context,
            strategic_number_inventory=default_strategic_number_inventory(),
        )
    bindings = RuntimeBinder(base_goal=base_goal).bind(
        storage_requests,
        context,
    )
    for demand in ir:
        for state in demand.strategic_number_states:
            binding = bindings.binding_for(state.request.request_id)
            if not isinstance(binding, StrategicNumberSlot):
                raise CompileError(
                    f"NATIVE-SN-BINDING: compiler-owned Strategic Number state "
                    f"'{state.name}' did not receive a StrategicNumberSlot"
                )
    try:
        for demand in ir:
            registry.validate_demand_lowering(demand, bindings)
    except (KeyError, ValueError) as exc:
        raise CompileError(f"NATIVE-CONTRACT-LOWERING: {exc}") from exc
    return (
        emit(
            ir,
            bindings,
            registry=registry,
            control_plan=control_plan,
            duc_plan=duc_plan,
        ),
        bindings,
        context,
    )


def _parse_source_slices(slices) -> list:
    ast = []
    for slice_ in slices:
        ast.extend(
            parse(
                slice_.text,
                source_unit=str(slice_.path),
                line_offset=slice_.start_line - 1,
                first_line_column_offset=slice_.start_column - 1,
            )
        )
    return ast


def _compile_source_parts(
    source: str,
    base_goal: int = 41,
    *,
    source_unit: str = "<source>",
    binding_context: BindingContext | None = None,
    registry: PrimitiveRegistry | None = None,
    control_plan=None,
    duc_plan: NativeDucPlan | None = None,
):
    ast = parse(source, source_unit=source_unit)
    registry = registry or default_de_registry()
    ir = analyze(ast, registry, source_unit=source_unit)
    return _compile_ir_parts(
        ir,
        registry,
        base_goal,
        binding_context=binding_context,
        control_plan=control_plan,
        duc_plan=duc_plan,
    )


def _compile_package_parts(
    request: SourceGraphRequest,
    base_goal: int = 41,
    *,
    binding_context: BindingContext | None = None,
    registry: PrimitiveRegistry | None = None,
    control_plan=None,
    duc_plan: NativeDucPlan | None = None,
):
    graph = SourceGraphResolver().resolve(request)
    graph_report = validate_effective_source_graph(graph)
    if not graph_report.valid:
        raise SourceGraphValidationError(graph_report)
    ast = _parse_source_slices(graph.slices)
    registry = registry or default_de_registry()
    ir = analyze(ast, registry, source_unit=None)
    result, bindings, context = _compile_ir_parts(
        ir,
        registry,
        base_goal,
        binding_context=binding_context,
        control_plan=control_plan,
        duc_plan=duc_plan,
    )
    return result, bindings, context, graph




def compile_semantic_demands(
    demands,
    base_goal: int = 41,
    *,
    binding_context: BindingContext | None = None,
    registry: PrimitiveRegistry | None = None,
    control_plan=None,
    duc_plan: NativeDucPlan | None = None,
) -> str:
    """Compile generic semantic demands without importing downstream strategy policy."""
    registry = registry or default_de_registry()
    result, _bindings, _context = _compile_ir_parts(
        demands,
        registry,
        base_goal,
        binding_context=binding_context,
        control_plan=control_plan,
        duc_plan=duc_plan,
    )
    return result


def _normalize_native_validation(native_result: NativeValidationResult) -> NativeValidationResult:
    clean = (
        native_result.status is ValidationStatus.VALIDATED
        and not native_result.failed
        and native_result.summary.finding_count == 0
        and not native_result.diagnostics
    )
    if clean or native_result.status is not ValidationStatus.VALIDATED:
        return native_result
    return replace(
        native_result,
        status=ValidationStatus.BACKEND_PROTOCOL_ERROR,
        failed=False,
        stderr=(
            native_result.stderr
            or "native backend reported VALIDATED with non-zero findings"
        ),
    )


def _binding_manifest_text(bindings, context: BindingContext) -> str:
    return bindings.to_manifest(
        package_inventory_sha=context.package_inventory_sha,
        allocator_version=context.allocator_version,
    ).to_json()


def compile_package(
    request: SourceGraphRequest,
    base_goal: int = 41,
    *,
    binding_context: BindingContext | None = None,
    registry: PrimitiveRegistry | None = None,
    control_plan=None,
    duc_plan: NativeDucPlan | None = None,
) -> str:
    result, _bindings, _context, _graph = _compile_package_parts(
        request,
        base_goal,
        binding_context=binding_context,
        registry=registry,
        control_plan=control_plan,
        duc_plan=duc_plan,
    )
    return result


def compile_source(
    source: str,
    base_goal: int = 41,
    *,
    source_unit: str = "<source>",
    binding_context: BindingContext | None = None,
    registry: PrimitiveRegistry | None = None,
    control_plan=None,
    duc_plan: NativeDucPlan | None = None,
) -> str:
    result, _bindings, _context = _compile_source_parts(
        source,
        base_goal,
        source_unit=source_unit,
        binding_context=binding_context,
        registry=registry,
        control_plan=control_plan,
        duc_plan=duc_plan,
    )
    return result


def compile_package_with_report(
    request: SourceGraphRequest,
    output: Path,
    *,
    base_goal: int = 41,
    native_backend: Aoe2NativeBackend | None = None,
    binding_context: BindingContext | None = None,
    binding_manifest: Path | None = None,
    registry: PrimitiveRegistry | None = None,
    control_plan=None,
    duc_plan: NativeDucPlan | None = None,
) -> CombinedValidationReport:
    if native_backend is None:
        return backend_failure_report(
            "native validation backend is required before artifact promotion",
            output,
        )
    registry = registry or default_de_registry()
    try:
        result, bindings, context, _graph = _compile_package_parts(
            request,
            base_goal,
            binding_context=binding_context,
            registry=registry,
            control_plan=control_plan,
            duc_plan=duc_plan,
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
        staged.write_bytes(result.encode("utf-8"))
        if staged_manifest is not None:
            staged_manifest.write_bytes(manifest_text.encode("utf-8"))
        rule_graph = SourceGraphResolver().resolve(
            SourceGraphRequest(entrypoint=staged)
        )
        effective_rules = analyze_effective_rules(rule_graph)
        persistent_state_report = analyze_persistent_state(
            effective_rules,
            ignored_state_identifiers=_compiler_owned_state_identifiers(result),
        )
        strategic_number_report = analyze_strategic_number_expressions(effective_rules)
        recurrent_execution_report = analyze_recurrent_execution(effective_rules)
        duc_report = analyze_duc(
            effective_rules,
            registry.native_contracts,
            recurrent_execution=recurrent_execution_report,
        )
        rule_report = analyze_rule_diagnostics(
            effective_rules,
            registry,
            persistent_state_report=persistent_state_report,
            strategic_number_report=strategic_number_report,
            recurrent_execution_report=recurrent_execution_report,
            duc_report=duc_report,
        )
        duc_errors = tuple(
            item
            for item in getattr(rule_report, "errors", ())
            if getattr(getattr(item, "category", None), "value", getattr(item, "category", None)) == "DUC"
        )
        if duc_errors:
            summary = "; ".join(
                f"{item.code.value if hasattr(item.code, 'value') else item.code}: {item.message}"
                for item in duc_errors
            )
            return semantic_failure_report(
                CompileError(f"DUC semantic errors: {summary}"),
                output,
                rule_diagnostics=rule_report.diagnostics,
            )
        if strategic_number_report.errors:
            return semantic_failure_report(
                StrategicNumberCompilationError(strategic_number_report.errors),
                output,
                rule_diagnostics=rule_report.diagnostics,
            )
        artifact_result = append_persistent_rule_diagnostics(
            result,
            rule_report.diagnostics,
        )
        staged.write_bytes(artifact_result.encode("utf-8"))
        native_result = _normalize_native_validation(native_backend.validate(staged))
        report = report_from_native_result(
            native_result,
            output,
            rule_diagnostics=rule_report.diagnostics,
        )
        if report.status is ReportStatus.VALIDATED:
            os.replace(staged, output)
            if staged_manifest is not None:
                os.replace(staged_manifest, binding_manifest)
        return report
    finally:
        staged.unlink(missing_ok=True)
        if staged_manifest is not None:
            staged_manifest.unlink(missing_ok=True)


def compile_source_with_report(
    source: str,
    output: Path,
    *,
    base_goal: int = 41,
    native_backend: Aoe2NativeBackend | None = None,
    source_unit: str = "<source>",
    binding_context: BindingContext | None = None,
    binding_manifest: Path | None = None,
    registry: PrimitiveRegistry | None = None,
    control_plan=None,
    duc_plan: NativeDucPlan | None = None,
) -> CombinedValidationReport:
    """Compile and return one deterministic semantic/native validation report."""
    if native_backend is None:
        return backend_failure_report(
            "native validation backend is required before artifact promotion",
            output,
        )
    registry = registry or default_de_registry()
    try:
        result, bindings, context = _compile_source_parts(
            source,
            base_goal,
            source_unit=source_unit,
            binding_context=binding_context,
            registry=registry,
            control_plan=control_plan,
            duc_plan=duc_plan,
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
        staged.write_bytes(result.encode("utf-8"))
        if staged_manifest is not None:
            staged_manifest.write_bytes(manifest_text.encode("utf-8"))
        rule_graph = SourceGraphResolver().resolve(
            SourceGraphRequest(entrypoint=staged)
        )
        effective_rules = analyze_effective_rules(rule_graph)
        persistent_state_report = analyze_persistent_state(
            effective_rules,
            ignored_state_identifiers=_compiler_owned_state_identifiers(result),
        )
        strategic_number_report = analyze_strategic_number_expressions(effective_rules)
        recurrent_execution_report = analyze_recurrent_execution(effective_rules)
        duc_report = analyze_duc(effective_rules, registry.native_contracts)
        rule_report = analyze_rule_diagnostics(
            effective_rules,
            registry,
            persistent_state_report=persistent_state_report,
            strategic_number_report=strategic_number_report,
            recurrent_execution_report=recurrent_execution_report,
            duc_report=duc_report,
        )
        duc_errors = tuple(
            item
            for item in getattr(rule_report, "errors", ())
            if getattr(getattr(item, "category", None), "value", getattr(item, "category", None)) == "DUC"
        )
        if duc_errors:
            summary = "; ".join(
                f"{item.code.value if hasattr(item.code, 'value') else item.code}: {item.message}"
                for item in duc_errors
            )
            return semantic_failure_report(
                CompileError(f"DUC semantic errors: {summary}"),
                output,
                rule_diagnostics=rule_report.diagnostics,
            )
        if strategic_number_report.errors:
            return semantic_failure_report(
                StrategicNumberCompilationError(strategic_number_report.errors),
                output,
                rule_diagnostics=rule_report.diagnostics,
            )
        artifact_result = append_persistent_rule_diagnostics(
            result,
            rule_report.diagnostics,
        )
        staged.write_bytes(artifact_result.encode("utf-8"))
        native_result = _normalize_native_validation(native_backend.validate(staged))
        report = report_from_native_result(
            native_result,
            output,
            rule_diagnostics=rule_report.diagnostics,
        )
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
    base_goal: int = 41,
    native_backend: Aoe2NativeBackend | None = None,
    source_unit: str = "<source>",
    binding_context: BindingContext | None = None,
    binding_manifest: Path | None = None,
    registry: PrimitiveRegistry | None = None,
    control_plan=None,
) -> NativeValidationResult | None:
    """Compile an artifact; native validation is mandatory for promotion."""
    if native_backend is None:
        raise NativeBackendError(
            "native validation backend is required before artifact promotion"
        )
    registry = registry or default_de_registry()
    result, bindings, context = _compile_source_parts(
        source,
        base_goal,
        source_unit=source_unit,
        binding_context=binding_context,
        registry=registry,
        control_plan=control_plan,
    )
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_text = _binding_manifest_text(bindings, context)

    if binding_manifest is not None:
        binding_manifest = binding_manifest.resolve()
        binding_manifest.parent.mkdir(parents=True, exist_ok=True)
        if binding_manifest == output:
            raise ValueError("binding manifest path must differ from .per output path")

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
        staged.write_bytes(result.encode("utf-8"))
        if staged_manifest is not None:
            staged_manifest.write_bytes(manifest_text.encode("utf-8"))
        rule_graph = SourceGraphResolver().resolve(
            SourceGraphRequest(entrypoint=staged)
        )
        effective_rules = analyze_effective_rules(rule_graph)
        persistent_state_report = analyze_persistent_state(
            effective_rules,
            ignored_state_identifiers=_compiler_owned_state_identifiers(result),
        )
        strategic_number_report = analyze_strategic_number_expressions(effective_rules)
        recurrent_execution_report = analyze_recurrent_execution(effective_rules)
        duc_report = analyze_duc(effective_rules, registry.native_contracts)
        rule_report = analyze_rule_diagnostics(
            effective_rules,
            registry,
            persistent_state_report=persistent_state_report,
            strategic_number_report=strategic_number_report,
            recurrent_execution_report=recurrent_execution_report,
            duc_report=duc_report,
        )
        duc_errors = tuple(
            item
            for item in getattr(rule_report, "errors", ())
            if getattr(getattr(item, "category", None), "value", getattr(item, "category", None)) == "DUC"
        )
        if duc_errors:
            summary = "; ".join(
                f"{item.code.value if hasattr(item.code, 'value') else item.code}: {item.message}"
                for item in duc_errors
            )
            return semantic_failure_report(
                CompileError(f"DUC semantic errors: {summary}"),
                output,
                rule_diagnostics=rule_report.diagnostics,
            )
        if strategic_number_report.errors:
            return semantic_failure_report(
                StrategicNumberCompilationError(strategic_number_report.errors),
                output,
                rule_diagnostics=rule_report.diagnostics,
            )
        artifact_result = append_persistent_rule_diagnostics(
            result,
            rule_report.diagnostics,
        )
        staged.write_bytes(artifact_result.encode("utf-8"))
        validation = _normalize_native_validation(native_backend.validate(staged))
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
    ap = argparse.ArgumentParser(description="Compile AoE2 AI semantic source to native .per")
    ap.add_argument("source", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--base-goal", type=int, default=41)
    ap.add_argument(
        "--binding-manifest",
        type=Path,
        help="optional deterministic JSON artifact containing resolved runtime bindings",
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
