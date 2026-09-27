"""AoE2 .per compiler package."""

from .semantic.source_graph_validation import (
    SourceGraphDiagnostic,
    SourceGraphDiagnosticCode,
    SourceGraphValidationError,
    SourceGraphValidationPolicy,
    SourceGraphValidationReport,
    SourceGraphValidationSeverity,
    validate_effective_source_graph,
)

from .source_graph import (
    EffectiveSourceGraph,
    EffectiveSourceSlice,
    LoadKind,
    LoadSymbolEnvironment,
    LoadSymbolState,
    SourceEdge,
    SourceGraphError,
    SourceGraphRequest,
    SourceGraphResolver,
    SourceInstance,
    SourceUnit,
)

__all__ = (
    "SourceGraphDiagnostic",
    "SourceGraphDiagnosticCode",
    "SourceGraphValidationError",
    "SourceGraphValidationPolicy",
    "SourceGraphValidationReport",
    "SourceGraphValidationSeverity",
    "validate_effective_source_graph",
    "EffectiveSourceGraph",
    "EffectiveSourceSlice",
    "LoadKind",
    "LoadSymbolEnvironment",
    "LoadSymbolState",
    "SourceEdge",
    "SourceGraphError",
    "SourceGraphRequest",
    "SourceGraphResolver",
    "SourceInstance",
    "SourceUnit",
)
