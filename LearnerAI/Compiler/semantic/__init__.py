from .analyzer import analyze, parse_expression
from .semantic_manifest import SemanticManifest, SemanticRuleRecord, build_semantic_manifest
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
    EvidenceConvergence,
    EvidenceLineage,
    PerformanceCostClass,
    PracticeStatus,
    capability_loss_preserves_demand,
    classify_capability_transition,
    classify_evidence_source,
    default_community_engine_registry,
    max_performance_cost,
    performance_cost_for_head,
    practice_evidence_convergence,
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

from .strategy_dependency import (
    FEATURE_STAGE_ORDER,
    FeatureEdge,
    FeatureEdgeStatus,
    FeatureNode,
    FeatureNodeStatus,
    FeatureStage,
    FeatureTrace,
    FeatureTraceBuilder,
    FeatureTraceDiagnostic,
    StrategyDependencyCode,
    StrategyDependencyEdge,
    StrategyDependencyFinding,
    StrategyDependencyNode,
    StrategyDependencyProof,
    StrategyDependencyReport,
    analyze_strategy_dependencies,
    first_broken_edge,
)

from .persistent_control import (
    PersistentControlDiagnostic,
    PersistentControlDiagnosticCode,
    PersistentControlReport,
    PersistentControlStatus,
    analyze_persistent_control_lifetimes,
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


from .recurrent_execution import (
    RecurrentDiagnosticCode,
    RecurrentExecutionDiagnostic,
    RecurrentExecutionReport,
    RecurrentExecutionStatus,
    analyze_recurrent_execution,
)


from .native_controller import (
    NativeController,
    NativeControllerBinding,
    NativeControllerCatalog,
    NativeControllerDomain,
    NativeControllerEdge,
    NativeControllerRelation,
    NativeControlSurface,
    NativeControlSurfaceKind,
    default_native_controller_catalog,
    bind_strategic_number_accesses,
)


from .native_controller_interactions import (
    NativeControllerInteraction,
    NativeControllerInteractionCatalog,
    NativeControllerInteractionKind,
    NativeInteractionCardinality,
    NativeInteractionEndpoint,
    NativeInteractionEndpointKind,
    NativeInteractionLifetime,
    NativeInteractionMutationOwner,
    NativeInteractionSupportState,
    NativeInteractionVisibility,
    default_native_controller_interaction_catalog,
)

from .native_control import (
    NativeControlValidationReport,
    storage_requests_for_plan,
    validate_native_control_plan,
    validate_native_control_plan_shape,
)

from .resource_control import (
    ResourceControlErrorCode,
    ResourceControlValidationError,
    ResourceControlValidationReport,
    validate_escrow_contract_set,
    validate_escrow_execution,
    validate_escrow_policy_plan,
    validate_escrow_against_arbitration,
    validate_escrow_contract,
    validate_native_arbitration_against_escrow,
    validate_native_arbitration_contract,
    validate_resource_control_contracts,
    validate_transient_action_exclusion_claim,
    validate_transient_against_escrow,
    validate_transient_against_native_arbitration,
)

from .construction import (
    is_construction_retryable,
    transition_construction,
)


from .operational_semantics import (
    OperationalDiagnostic,
    OperationalDiagnosticCode,
    OperationalStatus,
    OperationalValidationReport,
    build_operational_plan,
    operational_contract_for_demand,
    validate_operational_semantics,
)

from .operational_domains import (
    merge_operational_plan,
    operational_contracts_for_attack_plan,
    operational_contracts_for_duc_plan,
    operational_contracts_for_escrow_plan,
)

from .military_composition import (
    build_military_composition_proof,
    validate_military_composition_proof,
)


from .strategic_number_arbitration import (
    build_strategic_number_arbitration_plan,
    lower_strategic_number_arbitration,
    strategic_number_mode_to_controller,
    validate_strategic_number_arbitration,
)


from .policy_cause_graph import (
    CAUSE_RELATION_RANK,
    DIAGNOSTIC_PRECEDENCE,
    DIRECTED_CAUSAL_RELATIONS,
    PHASE_RANK,
    PolicyCauseEdge,
    PolicyCauseEdgeContext,
    PolicyCauseEdgeKey,
    PolicyCauseGraph,
    PolicyCauseGraphCausalCycleError,
    PolicyCauseGraphContradictionCanonicalizationError,
    PolicyCauseGraphDuplicateEdgeError,
    PolicyCauseGraphError,
    PolicyCauseGraphErrorCode,
    PolicyCauseGraphIllegalRelationError,
    PolicyCauseGraphInvalidCauseDirectionError,
    PolicyCauseGraphInvalidRelationEndpointError,
    PolicyCauseGraphInvalidRootReferenceError,
    PolicyCauseGraphPhaseOrderError,
    PolicyCauseGraphPriorityViolationError,
    PolicyCauseGraphSelfEdgeError,
    PolicyCauseGraphSubjectMismatchError,
    PolicyCauseGraphSuppressionWithoutCauseError,
    PolicyCauseGraphUnknownNodeError,
    PolicyCauseGraphWitnessMismatchError,
    PolicyCauseRelation,
    PolicyCauseWitness,
    PolicyDiagnostic,
    PolicyDiagnosticKey,
    PolicyDiagnosticPhase,
    PolicyDiagnosticRef,
    PolicyDiagnosticSubject,
    PolicySuppressionReason,
    PolicySuppressionRef,
    build_diagnostic,
    select_root_cause,
    validate_cause_direction,
    validate_policy_cause_graph,
)
