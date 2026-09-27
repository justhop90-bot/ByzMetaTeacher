from .analyzer import analyze, parse_expression
from .capability_validation import (
    AdmissibilityValidationPass,
    CapabilityDiagnosticCode,
    DependencyValidationPass,
    DiagnosticSeverity,
    GraphDiagnostic,
    GraphStatus,
    LifecycleClosureValidationPass,
    ProviderContractValidationPass,
    StructuralValidationPass,
    ValidationContext,
    ValidationReport,
    ValidationPass,
    WitnessValidationPass,
    validate_capability_graph,
)

from .capability_bridge import project_capability_graph, validate_projected_capabilities

from .demand_ownership import (
    OwnershipBoundary,
    OwnershipDiagnostic,
    OwnershipDiagnosticCode,
    OwnershipReport,
    OwnershipStatus,
    analyze_demand_ownership,
    validate_demand_ownership,
)

from .resource_conflicts import (
    ResourceDiagnostic,
    ResourceDiagnosticCode,
    ResourceStatus,
    ResourceValidationReport,
    validate_resource_conflicts,
)

from .action_issuance import (
    IssuanceDiagnostic,
    IssuanceDiagnosticCode,
    IssuanceStatus,
    IssuanceValidationReport,
    validate_action_issuance,
)

from .completion_witness import (
    WitnessDiagnostic,
    WitnessDiagnosticCode,
    WitnessStatus,
    WitnessValidationReport,
    validate_completion_witnesses,
)

from .release_state import (
    ReleaseDiagnostic,
    ReleaseDiagnosticCode,
    ReleaseStatus,
    ReleaseValidationReport,
    validate_release_states,
)

from .invalidation import (
    CancellationDiagnosticCode,
    InvalidationDiagnostic,
    InvalidationDiagnosticCode,
    InvalidationStatus,
    InvalidationValidationReport,
    validate_invalidation_contracts,
)


from .source_order import (
    SourceOrderReport,
    StateOrderBoundary,
    StateOrderVisibility,
    analyze_non_lifecycle_source_order,
    validate_non_lifecycle_source_order,
)


from .community_engine import (
    CapabilityTransition,
    CommunityEngineSemanticsRegistry,
    EngineLifecycleContract,
    EnginePractice,
    EvidenceClass,
    PracticeStatus,
    capability_loss_preserves_demand,
    classify_capability_transition,
    default_community_engine_registry,
)

from .source_graph_validation import (
    SourceGraphDiagnostic,
    SourceGraphDiagnosticCode,
    SourceGraphValidationError,
    SourceGraphValidationPolicy,
    SourceGraphValidationReport,
    SourceGraphValidationSeverity,
    validate_effective_source_graph,
)

from .rule_execution import (
    EffectiveRule,
    RuleAction,
    RuleExecutionReport,
    RulePassBehavior,
    StaticControlTransfer,
    RuleReachabilityReport,
    analyze_effective_rules,
    analyze_rule_reachability,
)

from .persistent_state import (
    PersistentStateAccess,
    PersistentStateAccessKind,
    PersistentStateBoundary,
    PersistentStateDiagnostic,
    PersistentStateDiagnosticCode,
    PersistentStateKind,
    PersistentStateRef,
    PersistentStateReport,
    PersistentStateVisibility,
    analyze_persistent_state,
)

from .pass_scheduler import (
    ControlTransfer,
    PassScheduler,
    PassTrace,
    SchedulerSemanticError,
)

from .fact_evaluation import evaluate_static_truth
from .fact_registry import FactSemanticAdapter, NativeFactRegistry
from .guard_satisfiability import GuardSatisfiability, analyze_guard
from .firing_eligibility import FiringEligibility, analyze_firing_eligibility
from .rule_diagnostics import (
    RuleDiagnostic,
    RuleDiagnosticCategory,
    RuleDiagnosticCode,
    RuleDiagnosticReport,
    analyze_rule_diagnostics,
)

from .fact_values import (
    CanonicalEnum,
    CanonicalIdentifier,
    CanonicalInteger,
    CanonicalKind,
    CanonicalSymbol,
    CanonicalValue,
    CanonicalizationContext,
    FactDomain,
    FactDomainKind,
    NormalizedFact,
    EnumNormalization,
    IdentifierForm,
    IdentifierNormalization,
    ParameterSemanticKind,
    StaticTruth,
    SymbolNormalization,
    canonicalize_value,
)

from .strategic_number_semantics import (
    StrategicNumberCompilationError,
    StrategicNumberDiagnostic,
    StrategicNumberCompareOp,
    StrategicNumberDiagnosticCode,
    StrategicNumberSemanticError,
    StrategicNumberSemanticReport,
    analyze_strategic_number_expressions,
    evaluate_strategic_number_comparison,
    evaluate_strategic_number_mutation,
    parse_strategic_number_comparison,
    parse_strategic_number_mutation,
)
