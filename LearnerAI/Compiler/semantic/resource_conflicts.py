"""Validation of transient resource claims and conflict contracts."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..diagnostics import DiagnosticSeverity
from ..ir.capability import CapabilityGraph, CapabilityProvider
from ..ir.model import SemanticId
from ..ir.resource import (
    ConflictContract,
    ResourceClaim,
    ResourceClaimId,
    ResourceConflictGraph,
    ResourceKind,
    ResourceScope,
)
from ..primitives import PrimitiveRegistry


class ResourceStatus(str, Enum):
    CONNECTED = "CONNECTED"
    BLOCKED = "BLOCKED"
    CONFLICTING = "CONFLICTING"
    DUPLICATE = "DUPLICATE"


class ResourceDiagnosticCode(str, Enum):
    ARBITRATION_WITHOUT_CONFLICT = "RES-002"
    CONFLICT_WITHOUT_OWNER = "RES-003"
    MULTIPLE_ARBITRATION_OWNERS = "RES-004"
    DUPLICATE_CLAIM = "RES-005"
    CONFLICT_INCOMPATIBLE_ARBITRATORS = "RES-006"
    INVALID_RESOURCE_CLASS = "RES-007"


@dataclass(frozen=True)
class ResourceDiagnostic:
    code: ResourceDiagnosticCode
    severity: DiagnosticSeverity
    message: str
    status: ResourceStatus
    provider: object | None = None
    conflict_class: str | None = None


@dataclass(frozen=True)
class ResourceValidationReport:
    diagnostics: tuple[ResourceDiagnostic, ...]
    claims: tuple[ResourceClaim, ...]
    conflicts: tuple[ConflictContract, ...]

    @property
    def errors(self) -> tuple[ResourceDiagnostic, ...]:
        return tuple(
            item
            for item in self.diagnostics
            if item.severity is DiagnosticSeverity.ERROR
        )

    @property
    def valid(self) -> bool:
        return not self.errors

    @property
    def graph(self) -> ResourceConflictGraph:
        return ResourceConflictGraph(
            claims=self.claims,
            conflicts=self.conflicts,
        )


def _identity_key(identity: SemanticId | None) -> tuple[str, str]:
    if identity is None:
        return ("", "")
    return identity.source_unit, identity.local_name


def _diag_key(item: ResourceDiagnostic) -> tuple[object, ...]:
    provider = item.provider
    return (
        item.code.value,
        item.conflict_class or "",
        _identity_key(provider),
        item.message,
    )


def _diag(
    code: ResourceDiagnosticCode,
    message: str,
    *,
    status: ResourceStatus,
    provider: SemanticId | None = None,
    conflict_class: str | None = None,
) -> ResourceDiagnostic:
    return ResourceDiagnostic(
        code=code,
        severity=DiagnosticSeverity.ERROR,
        message=message,
        status=status,
        provider=provider,
        conflict_class=conflict_class,
    )


def _claim_for(provider: CapabilityProvider) -> ResourceClaim | None:
    action = provider.action
    if action is None or action.conflict_class is None:
        return None
    if len(action.arbitration) != 1:
        return None
    arbitration_owner = action.arbitration[0]
    return ResourceClaim(
        identity=ResourceClaimId(
            provider.identity.source_unit,
            f"{provider.identity.local_name}-resource-claim",
        ),
        kind=ResourceKind.ACTION_EXCLUSION,
        scope=ResourceScope.TRANSIENT,
        claimant=SemanticId(
            provider.identity.source_unit,
            provider.identity.local_name,
        ),
        conflict_class=action.conflict_class,
        arbitration_owner=arbitration_owner,
        location=provider.location,
    )


def validate_resource_conflicts(
    graph: CapabilityGraph,
    primitive_registry: PrimitiveRegistry | None = None,
) -> ResourceValidationReport:
    del primitive_registry

    diagnostics: list[ResourceDiagnostic] = []
    claims: list[ResourceClaim] = []
    by_conflict: dict[str, list[CapabilityProvider]] = {}

    for provider in sorted(
        graph.providers,
        key=lambda item: (item.identity.source_unit, item.identity.local_name),
    ):
        action = provider.action
        if action is None:
            continue

        conflict_class = action.conflict_class
        arbitration = tuple(sorted(action.arbitration, key=_identity_key))

        if conflict_class is None:
            if arbitration:
                diagnostics.append(
                    _diag(
                        ResourceDiagnosticCode.ARBITRATION_WITHOUT_CONFLICT,
                        f"provider '{provider.identity.local_name}' declares arbitration "
                        "without a conflict class",
                        status=ResourceStatus.BLOCKED,
                        provider=SemanticId(
                            provider.identity.source_unit,
                            provider.identity.local_name,
                        ),
                    )
                )
            continue

        if not conflict_class.strip():
            diagnostics.append(
                _diag(
                    ResourceDiagnosticCode.INVALID_RESOURCE_CLASS,
                    f"provider '{provider.identity.local_name}' declares an empty "
                    "resource conflict class",
                    status=ResourceStatus.BLOCKED,
                    provider=SemanticId(
                        provider.identity.source_unit,
                        provider.identity.local_name,
                    ),
                )
            )
            continue

        if not arbitration:
            diagnostics.append(
                _diag(
                    ResourceDiagnosticCode.CONFLICT_WITHOUT_OWNER,
                    f"provider '{provider.identity.local_name}' conflict class "
                    f"'{conflict_class}' has no arbitration owner",
                    status=ResourceStatus.BLOCKED,
                    provider=SemanticId(
                        provider.identity.source_unit,
                        provider.identity.local_name,
                    ),
                    conflict_class=conflict_class,
                )
            )
            continue

        if len(arbitration) > 1:
            owners = ", ".join(
                f"{owner.source_unit}:{owner.local_name}"
                for owner in arbitration
            )
            diagnostics.append(
                _diag(
                    ResourceDiagnosticCode.MULTIPLE_ARBITRATION_OWNERS,
                    f"provider '{provider.identity.local_name}' conflict class "
                    f"'{conflict_class}' has multiple arbitration owners: {owners}",
                    status=ResourceStatus.CONFLICTING,
                    provider=SemanticId(
                        provider.identity.source_unit,
                        provider.identity.local_name,
                    ),
                    conflict_class=conflict_class,
                )
            )
            continue

        claim = _claim_for(provider)
        if claim is not None:
            claims.append(claim)
            by_conflict.setdefault(conflict_class, []).append(provider)

    claims.sort(
        key=lambda claim: (
            claim.identity.source_unit,
            claim.identity.local_name,
        )
    )

    seen_claims: dict[ResourceClaimId, ResourceClaim] = {}
    for claim in claims:
        prior = seen_claims.get(claim.identity)
        if prior is not None:
            diagnostics.append(
                _diag(
                    ResourceDiagnosticCode.DUPLICATE_CLAIM,
                    f"duplicate resource claim "
                    f"'{claim.identity.source_unit}:{claim.identity.local_name}'",
                    status=ResourceStatus.DUPLICATE,
                    provider=claim.claimant,
                    conflict_class=claim.conflict_class,
                )
            )
        else:
            seen_claims[claim.identity] = claim

    conflicts: list[ConflictContract] = []
    for conflict_class in sorted(by_conflict):
        providers = sorted(
            by_conflict[conflict_class],
            key=lambda item: (
                item.action.arbitration[0].source_unit,
                item.action.arbitration[0].local_name,
                item.identity.source_unit,
                item.identity.local_name,
            ),
        )
        owners = tuple(
            sorted(
                {
                    provider.action.arbitration[0]
                    for provider in providers
                },
                key=_identity_key,
            )
        )
        if len(owners) > 1:
            owner_text = ", ".join(
                f"{owner.source_unit}:{owner.local_name}"
                for owner in owners
            )
            diagnostics.append(
                _diag(
                    ResourceDiagnosticCode.CONFLICT_INCOMPATIBLE_ARBITRATORS,
                    f"conflict class '{conflict_class}' has incompatible "
                    f"arbitration owners: {owner_text}",
                    status=ResourceStatus.CONFLICTING,
                    conflict_class=conflict_class,
                )
            )
            continue

        conflicts.append(
            ConflictContract(
                conflict_class=conflict_class,
                kind=ResourceKind.ACTION_EXCLUSION,
                scope=ResourceScope.TRANSIENT,
                arbitration_owner=owners[0],
                providers=tuple(
                    SemanticId(
                        provider.identity.source_unit,
                        provider.identity.local_name,
                    )
                    for provider in providers
                ),
            )
        )

    return ResourceValidationReport(
        diagnostics=tuple(sorted(diagnostics, key=_diag_key)),
        claims=tuple(claims),
        conflicts=tuple(conflicts),
    )


__all__ = [
    "ResourceDiagnostic",
    "ResourceDiagnosticCode",
    "ResourceStatus",
    "ResourceValidationReport",
    "validate_resource_conflicts",
]
