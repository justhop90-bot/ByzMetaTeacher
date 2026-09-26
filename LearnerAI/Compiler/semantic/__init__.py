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
