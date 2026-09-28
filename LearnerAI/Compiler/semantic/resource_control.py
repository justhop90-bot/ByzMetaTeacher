"""Cross-domain validation for native resource control and transient action claims."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..ast import SourceLocation
from ..diagnostics import DiagnosticSeverity
from ..ir.resource_control import (
    EscrowAdmissionMode,
    EscrowConsumptionMode,
    EscrowContract,
    EscrowReserveKind,
    EscrowRetentionPolicy,
    NativeArbitrationContract,
    NativeArbitrationRecoveryKind,
    NativeArbitrationReleaseKind,
    NativeArbitrationStarvationPolicy,
    NativeControlStorage,
    TransientActionExclusionClaim,
    TransientClaimKind,
    TransientClaimScope,
)


class ResourceControlErrorCode(str, Enum):
    ARBITRATION_EMPTY_IDENTITY = "RCTRL-001"
    ARBITRATION_INVALID_STORAGE = "RCTRL-002"
    ARBITRATION_INVALID_VALUES = "RCTRL-003"
    ARBITRATION_MISSING_GUARD = "RCTRL-004"
    ARBITRATION_RELEASE_SHAPE = "RCTRL-005"
    ARBITRATION_HANDOFF_RECOVERY_MISMATCH = "RCTRL-006"
    ARBITRATION_SELF_HANDOFF = "RCTRL-007"
    ARBITRATION_RECOVERY_DROPS_DEMAND = "RCTRL-008"
    ARBITRATION_STARVATION_POLICY = "RCTRL-009"
    ESCROW_EMPTY_IDENTITY = "RCTRL-010"
    ESCROW_RESOURCES = "RCTRL-011"
    ESCROW_RESERVE_SHAPE = "RCTRL-012"
    ESCROW_RELEASE_SHAPE = "RCTRL-013"
    ESCROW_ADMISSION_CONSUMPTION_MISMATCH = "RCTRL-014"
    ESCROW_ARBITRATION_REFERENCE_MISSING = "RCTRL-015"
    ESCROW_ARBITRATION_REFERENCE_MISMATCH = "RCTRL-016"
    ESCROW_RETENTION_POLICY = "RCTRL-017"
    NATIVE_ESCROW_IDENTITY_ALIAS = "RCTRL-018"
    TRANSIENT_EMPTY_IDENTITY = "RCTRL-019"
    TRANSIENT_INVALID_KIND = "RCTRL-020"
    TRANSIENT_INVALID_SCOPE = "RCTRL-021"
    TRANSIENT_MISSING_CLAIMANT = "RCTRL-022"
    TRANSIENT_MISSING_CONFLICT_CLASS = "RCTRL-023"
    TRANSIENT_NATIVE_SURFACE_ALIAS = "RCTRL-024"
    TRANSIENT_ESCROW_ALIAS = "RCTRL-025"


@dataclass(frozen=True)
class ResourceControlValidationError:
    code: ResourceControlErrorCode
    message: str
    subject: str
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR
    location: SourceLocation | None = None


@dataclass(frozen=True)
class ResourceControlValidationReport:
    errors: tuple[ResourceControlValidationError, ...] = ()

    @property
    def valid(self) -> bool:
        return not self.errors

    @property
    def diagnostics(self) -> tuple[ResourceControlValidationError, ...]:
        return self.errors


def _error(
    code: ResourceControlErrorCode,
    message: str,
    *,
    subject: str,
    location: SourceLocation | None = None,
) -> ResourceControlValidationError:
    return ResourceControlValidationError(
        code=code,
        message=message,
        subject=subject,
        location=location,
    )


def validate_native_arbitration_contract(
    contract: NativeArbitrationContract,
) -> tuple[ResourceControlValidationError, ...]:
    errors: list[ResourceControlValidationError] = []
    subject = contract.identity or "<anonymous-arbitration>"

    if not contract.identity.strip() or not contract.surface_id.strip():
        errors.append(
            _error(
                ResourceControlErrorCode.ARBITRATION_EMPTY_IDENTITY,
                "native arbitration requires non-empty identity and native surface",
                subject=subject,
                location=contract.location,
            )
        )

    if contract.storage_kind not in (
        NativeControlStorage.GOAL,
        NativeControlStorage.STRATEGIC_NUMBER,
    ) or not contract.storage.purpose.strip():
        errors.append(
            _error(
                ResourceControlErrorCode.ARBITRATION_INVALID_STORAGE,
                "native arbitration storage must be a named persistent Goal or Strategic Number surface",
                subject=subject,
                location=contract.location,
            )
        )

    if contract.free_value == contract.claim_value:
        errors.append(
            _error(
                ResourceControlErrorCode.ARBITRATION_INVALID_VALUES,
                "native arbitration free_value and claim_value must differ",
                subject=subject,
                location=contract.location,
            )
        )

    if contract.acquisition_guard is None:
        errors.append(
            _error(
                ResourceControlErrorCode.ARBITRATION_MISSING_GUARD,
                "native arbitration requires an acquisition guard",
                subject=subject,
                location=contract.location,
            )
        )

    release = contract.release
    if release.trigger is None:
        errors.append(
            _error(
                ResourceControlErrorCode.ARBITRATION_RELEASE_SHAPE,
                "native arbitration release requires a trigger",
                subject=subject,
                location=contract.location,
            )
        )

    if release.kind is NativeArbitrationReleaseKind.HANDOFF:
        if release.handoff_owner is None:
            errors.append(
                _error(
                    ResourceControlErrorCode.ARBITRATION_RELEASE_SHAPE,
                    "handoff release requires exactly one successor owner",
                    subject=subject,
                    location=contract.location,
                )
            )
        elif release.handoff_owner == contract.owner:
            errors.append(
                _error(
                    ResourceControlErrorCode.ARBITRATION_SELF_HANDOFF,
                    "native arbitration cannot hand off to its current owner",
                    subject=subject,
                    location=contract.location,
                )
            )
    elif release.handoff_owner is not None:
        errors.append(
            _error(
                ResourceControlErrorCode.ARBITRATION_RELEASE_SHAPE,
                "reset-to-free release cannot declare a successor owner",
                subject=subject,
                location=contract.location,
            )
        )

    recovery = contract.recovery
    if recovery.trigger is None:
        errors.append(
            _error(
                ResourceControlErrorCode.ARBITRATION_RELEASE_SHAPE,
                "native arbitration recovery requires a trigger",
                subject=subject,
                location=contract.location,
            )
        )

    if not recovery.preserves_demand:
        errors.append(
            _error(
                ResourceControlErrorCode.ARBITRATION_RECOVERY_DROPS_DEMAND,
                "resource recovery must preserve the original demand identity",
                subject=subject,
                location=contract.location,
            )
        )

    if (
        recovery.kind is NativeArbitrationRecoveryKind.HANDOFF_AND_RETRY
        and release.kind is not NativeArbitrationReleaseKind.HANDOFF
    ):
        errors.append(
            _error(
                ResourceControlErrorCode.ARBITRATION_HANDOFF_RECOVERY_MISMATCH,
                "HANDOFF_AND_RETRY recovery requires a HANDOFF release",
                subject=subject,
                location=contract.location,
            )
        )

    if contract.starvation_policy is not (
        NativeArbitrationStarvationPolicy.REQUIRE_RELEASE_OR_HANDOFF
    ):
        errors.append(
            _error(
                ResourceControlErrorCode.ARBITRATION_STARVATION_POLICY,
                "native arbitration must use explicit release-or-handoff starvation semantics",
                subject=subject,
                location=contract.location,
            )
        )

    return tuple(errors)


def validate_escrow_contract(
    contract: EscrowContract,
) -> tuple[ResourceControlValidationError, ...]:
    errors: list[ResourceControlValidationError] = []
    subject = contract.identity or "<anonymous-escrow>"

    if not contract.identity.strip():
        errors.append(
            _error(
                ResourceControlErrorCode.ESCROW_EMPTY_IDENTITY,
                "escrow requires a non-empty identity",
                subject=subject,
                location=contract.location,
            )
        )

    if not contract.resources or any(not item.strip() for item in contract.resources):
        errors.append(
            _error(
                ResourceControlErrorCode.ESCROW_RESOURCES,
                "escrow requires at least one non-empty resource identifier",
                subject=subject,
                location=contract.location,
            )
        )
    elif len(contract.resources) != len(set(contract.resources)):
        errors.append(
            _error(
                ResourceControlErrorCode.ESCROW_RESOURCES,
                "escrow resource identifiers must be unique",
                subject=subject,
                location=contract.location,
            )
        )

    reserve = contract.reserve
    if not reserve.command.strip():
        errors.append(
            _error(
                ResourceControlErrorCode.ESCROW_RESERVE_SHAPE,
                "escrow reserve requires a native command",
                subject=subject,
                location=contract.location,
            )
        )

    if reserve.kind is EscrowReserveKind.SET_PERCENTAGE:
        if reserve.percentage is None or not 0 <= reserve.percentage <= 100:
            errors.append(
                _error(
                    ResourceControlErrorCode.ESCROW_RESERVE_SHAPE,
                    "percentage escrow reservation must be within 0..100",
                    subject=subject,
                    location=contract.location,
                )
            )
        if reserve.amount_expression is not None:
            errors.append(
                _error(
                    ResourceControlErrorCode.ESCROW_RESERVE_SHAPE,
                    "percentage escrow reservation cannot also specify an amount",
                    subject=subject,
                    location=contract.location,
                )
            )
    elif reserve.kind is EscrowReserveKind.MODIFY_AMOUNT:
        if reserve.amount_expression is None:
            errors.append(
                _error(
                    ResourceControlErrorCode.ESCROW_RESERVE_SHAPE,
                    "amount escrow reservation requires an amount expression",
                    subject=subject,
                    location=contract.location,
                )
            )
        if reserve.percentage is not None:
            errors.append(
                _error(
                    ResourceControlErrorCode.ESCROW_RESERVE_SHAPE,
                    "amount escrow reservation cannot also specify a percentage",
                    subject=subject,
                    location=contract.location,
                )
            )

    if not contract.release.command.strip() or contract.release.trigger is None:
        errors.append(
            _error(
                ResourceControlErrorCode.ESCROW_RELEASE_SHAPE,
                "escrow requires an explicit native release command and trigger",
                subject=subject,
                location=contract.location,
            )
        )

    if contract.admission_mode is EscrowAdmissionMode.INCLUDE_ESCROW:
        if contract.consumption.mode is not EscrowConsumptionMode.ESCROW_AWARE_ACTION:
            errors.append(
                _error(
                    ResourceControlErrorCode.ESCROW_ADMISSION_CONSUMPTION_MISMATCH,
                    "INCLUDE_ESCROW admission requires ESCROW_AWARE_ACTION consumption",
                    subject=subject,
                    location=contract.location,
                )
            )
    elif contract.consumption.mode is EscrowConsumptionMode.ESCROW_AWARE_ACTION:
        errors.append(
            _error(
                ResourceControlErrorCode.ESCROW_ADMISSION_CONSUMPTION_MISMATCH,
                "ESCROW_AWARE_ACTION consumption requires INCLUDE_ESCROW admission",
                subject=subject,
                location=contract.location,
            )
        )

    if contract.arbitration_identity is not None and not contract.arbitration_identity.strip():
        errors.append(
            _error(
                ResourceControlErrorCode.ESCROW_ARBITRATION_REFERENCE_MISSING,
                "escrow arbitration_identity must be non-empty when supplied",
                subject=subject,
                location=contract.location,
            )
        )

    if contract.retention_policy is not (
        EscrowRetentionPolicy.REQUIRE_RELEASE_OR_CONSUMPTION
    ):
        errors.append(
            _error(
                ResourceControlErrorCode.ESCROW_RETENTION_POLICY,
                "escrow must require explicit release or consumption",
                subject=subject,
                location=contract.location,
            )
        )

    return tuple(errors)


def validate_transient_action_exclusion_claim(
    claim: TransientActionExclusionClaim,
) -> tuple[ResourceControlValidationError, ...]:
    errors: list[ResourceControlValidationError] = []
    subject = claim.identity

    if not claim.identity_source_unit.strip() or not claim.identity_local_name.strip():
        errors.append(
            _error(
                ResourceControlErrorCode.TRANSIENT_EMPTY_IDENTITY,
                "transient action exclusion requires a source unit and local identity",
                subject=subject or "<anonymous-transient-claim>",
                location=claim.location,
            )
        )

    if claim.kind is not TransientClaimKind.ACTION_EXCLUSION:
        errors.append(
            _error(
                ResourceControlErrorCode.TRANSIENT_INVALID_KIND,
                "transient resource claim must be ACTION_EXCLUSION",
                subject=subject,
                location=claim.location,
            )
        )

    if claim.scope is not TransientClaimScope.RULE_PASS:
        errors.append(
            _error(
                ResourceControlErrorCode.TRANSIENT_INVALID_SCOPE,
                "transient action exclusion must be RULE_PASS scoped",
                subject=subject,
                location=claim.location,
            )
        )

    if not claim.claimant.local_name.strip():
        errors.append(
            _error(
                ResourceControlErrorCode.TRANSIENT_MISSING_CLAIMANT,
                "transient action exclusion requires one claimant",
                subject=subject,
                location=claim.location,
            )
        )

    if not claim.conflict_class.strip():
        errors.append(
            _error(
                ResourceControlErrorCode.TRANSIENT_MISSING_CONFLICT_CLASS,
                "transient action exclusion requires a conflict class",
                subject=subject,
                location=claim.location,
            )
        )

    return tuple(errors)


def validate_native_arbitration_against_escrow(
    arbitration: NativeArbitrationContract,
    escrow: EscrowContract,
) -> tuple[ResourceControlValidationError, ...]:
    if arbitration.identity == escrow.identity:
        return (
            _error(
                ResourceControlErrorCode.NATIVE_ESCROW_IDENTITY_ALIAS,
                "native arbitration and escrow contracts must have distinct semantic identities",
                subject=arbitration.identity,
                location=arbitration.location or escrow.location,
            ),
        )
    return ()


def validate_escrow_against_arbitration(
    escrow: EscrowContract,
    arbitration: NativeArbitrationContract | None,
) -> tuple[ResourceControlValidationError, ...]:
    if escrow.arbitration_identity is None:
        return ()

    if arbitration is None:
        return (
            _error(
                ResourceControlErrorCode.ESCROW_ARBITRATION_REFERENCE_MISSING,
                f"escrow references arbitration '{escrow.arbitration_identity}' but no arbitration contract was supplied",
                subject=escrow.identity,
                location=escrow.location,
            ),
        )

    if escrow.arbitration_identity != arbitration.identity:
        return (
            _error(
                ResourceControlErrorCode.ESCROW_ARBITRATION_REFERENCE_MISMATCH,
                f"escrow references arbitration '{escrow.arbitration_identity}', supplied '{arbitration.identity}'",
                subject=escrow.identity,
                location=escrow.location or arbitration.location,
            ),
        )

    return ()


def validate_transient_against_native_arbitration(
    claim: TransientActionExclusionClaim,
    arbitration: NativeArbitrationContract | None,
) -> tuple[ResourceControlValidationError, ...]:
    if arbitration is None:
        return ()

    aliases = {
        arbitration.identity,
        arbitration.surface_id,
    }
    if claim.conflict_class in aliases:
        return (
            _error(
                ResourceControlErrorCode.TRANSIENT_NATIVE_SURFACE_ALIAS,
                "transient ACTION_EXCLUSION cannot alias persistent native arbitration identity or surface",
                subject=claim.identity,
                location=claim.location or arbitration.location,
            ),
        )

    return ()


def validate_transient_against_escrow(
    claim: TransientActionExclusionClaim,
    escrow: EscrowContract | None,
) -> tuple[ResourceControlValidationError, ...]:
    if escrow is None:
        return ()

    aliases = {escrow.identity}
    if escrow.arbitration_identity is not None:
        aliases.add(escrow.arbitration_identity)

    if claim.conflict_class in aliases:
        return (
            _error(
                ResourceControlErrorCode.TRANSIENT_ESCROW_ALIAS,
                "transient ACTION_EXCLUSION cannot alias persistent escrow identity or arbitration reference",
                subject=claim.identity,
                location=claim.location or escrow.location,
            ),
        )

    return ()


def validate_resource_control_contracts(
    *,
    arbitration: NativeArbitrationContract | None = None,
    escrow: EscrowContract | None = None,
    transient: TransientActionExclusionClaim | None = None,
) -> ResourceControlValidationReport:
    errors: list[ResourceControlValidationError] = []

    if arbitration is not None:
        errors.extend(validate_native_arbitration_contract(arbitration))

    if escrow is not None:
        errors.extend(validate_escrow_contract(escrow))

    if transient is not None:
        errors.extend(validate_transient_action_exclusion_claim(transient))

    if arbitration is not None and escrow is not None:
        errors.extend(validate_native_arbitration_against_escrow(arbitration, escrow))
        errors.extend(validate_escrow_against_arbitration(escrow, arbitration))
    elif escrow is not None:
        errors.extend(validate_escrow_against_arbitration(escrow, None))

    if transient is not None:
        errors.extend(
            validate_transient_against_native_arbitration(transient, arbitration)
        )
        errors.extend(
            validate_transient_against_escrow(transient, escrow)
        )

    ordered = tuple(
        sorted(
            errors,
            key=lambda item: (
                item.code.value,
                item.subject,
                item.message,
            ),
        )
    )
    return ResourceControlValidationReport(errors=ordered)


__all__ = [
    "ResourceControlErrorCode",
    "ResourceControlValidationError",
    "ResourceControlValidationReport",
    "validate_escrow_against_arbitration",
    "validate_escrow_contract",
    "validate_native_arbitration_against_escrow",
    "validate_native_arbitration_contract",
    "validate_resource_control_contracts",
    "validate_transient_action_exclusion_claim",
    "validate_transient_against_escrow",
    "validate_transient_against_native_arbitration",
]
