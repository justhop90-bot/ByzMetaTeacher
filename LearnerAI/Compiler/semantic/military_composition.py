"""Cross-domain validation for the first military composition proof path."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..diagnostics import DiagnosticSeverity
from ..ir.attack import AttackCapabilityRole, AttackExecutionMode, AttackExecutionState
from ..ir.capability import CapabilityRecoveryContract, CapabilityRecoveryEvent, CapabilityRecoveryState, CapabilityRecoveryStateKind, DemandId
from ..ir.model import CompletionWitnessContract
from ..ir.resource import ResourceClaim, ResourceClaimId, ResourceKind, ResourceScope
from ..ir.program import CompilerSemanticProgram
from ..ir.military_composition import MilitaryCompositionProofPath
from ..ir.model import SemanticId
if TYPE_CHECKING:
    from ..ir.attack import AttackExecution
    from ..ir.strategy import StrategyCompilation


@dataclass(frozen=True)
class MilitaryProofDiagnostic:
    code: str
    severity: DiagnosticSeverity
    message: str

    @property
    def is_error(self) -> bool:
        return self.severity is DiagnosticSeverity.ERROR


@dataclass(frozen=True)
class MilitaryProofReport:
    diagnostics: tuple[MilitaryProofDiagnostic, ...]

    @property
    def errors(self) -> tuple[MilitaryProofDiagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.is_error)

    @property
    def valid(self) -> bool: