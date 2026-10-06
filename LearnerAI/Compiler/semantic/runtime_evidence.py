"""Deterministic assessment of machine-readable Byzantine runtime witnesses.

This module consumes runtime evidence; it never invents engine observations.
A failed claim remains a failure even if later checkpoints show recovery, because
the purpose of first-broken-edge analysis is causal debugging, not optimism.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Mapping, Sequence


class RuntimeClaimStatus(str, Enum):
    OPEN = "OPEN"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


class RuntimeEvidenceStatus(str, Enum):
    OPEN = "OPEN"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class RuntimeFirstBrokenEdgeDiagnostic:
    scenario_id: str
    claim_id: str
    lifecycle_edge: str
    evidence_class: str
    rule_identities: tuple[str, ...]
    expected: tuple[tuple[str, str], ...]
    observed_facts: tuple[str, ...]
    world_witness: tuple[str, ...]
    game_time_seconds: float | None
    artifact_sha256: str | None
    message: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeAssessment:
    scenario_id: str
    status: RuntimeEvidenceStatus
    artifact_sha256: str | None
    confirmed_claims: tuple[str, ...]
    failed_claims: tuple[str, ...]
    open_claims: tuple[str, ...]
    first_broken_edge: RuntimeFirstBrokenEdgeDiagnostic | None

    def to_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "status": self.status.value,
            "artifact_sha256": self.artifact_sha256,
            "confirmed_claims": list(self.confirmed_claims),
            "failed_claims": list(self.failed_claims),
            "open_claims": list(self.open_claims),
            "first_broken_edge": (
                None
                if self.first_broken_edge is None
                else self.first_broken_edge.to_dict()
            ),
        }


def _checkpoint_statuses(
    checkpoints: Sequence[Mapping[str, object]],
    claim_id: str,
) -> tuple[Mapping[str, object], ...]:
    return tuple(
        checkpoint
        for checkpoint in checkpoints
        if checkpoint.get("claim_id") == claim_id
    )


def _claim_status(checkpoints: Sequence[Mapping[str, object]]) -> RuntimeClaimStatus:
    if any(
        checkpoint.get("assessment") == RuntimeClaimStatus.FAILED.value
        for checkpoint in checkpoints
    ):
        return RuntimeClaimStatus.FAILED
    if any(
        checkpoint.get("assessment") == RuntimeClaimStatus.CONFIRMED.value
        for checkpoint in checkpoints
    ):
        return RuntimeClaimStatus.CONFIRMED
    return RuntimeClaimStatus.OPEN


def _string_pairs(value: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, Mapping):
        return ()
    return tuple(
        sorted((str(key), str(item)) for key, item in value.items())
    )


def assess_runtime_witness(record: Mapping[str, object]) -> RuntimeAssessment:
    """Assess one SCENARIO/WITNESS record without interpreting engine syntax."""
    scenario_id = str(record.get("scenario_id", ""))
    artifact = record.get("artifact")
    artifact_sha256 = (
        artifact.get("sha256")
        if isinstance(artifact, Mapping)
        else None
    )
    raw_claims = record.get("claims", ())
    raw_checkpoints = record.get("checkpoint", ())
    claims = tuple(item for item in raw_claims if isinstance(item, Mapping))
    checkpoints = tuple(
        item for item in raw_checkpoints if isinstance(item, Mapping)
    )

    confirmed: list[str] = []
    failed: list[str] = []
    open_claims: list[str] = []
    first_broken: RuntimeFirstBrokenEdgeDiagnostic | None = None

    for claim in claims:
        claim_id = str(claim.get("id", ""))
        claim_checkpoints = _checkpoint_statuses(checkpoints, claim_id)
        status = _claim_status(claim_checkpoints)
        if status is RuntimeClaimStatus.CONFIRMED:
            confirmed.append(claim_id)
        elif status is RuntimeClaimStatus.FAILED:
            failed.append(claim_id)
            if first_broken is None:
                selected = next(
                    checkpoint
                    for checkpoint in claim_checkpoints
                    if checkpoint.get("assessment") == RuntimeClaimStatus.FAILED.value
                )
                observed_facts = tuple(
                    str(item)
                    for item in selected.get("observed_facts", ())
                    if isinstance(item, (str, int, float, bool))
                )
                world_witness = tuple(
                    str(item)
                    for item in selected.get("world_witness", ())
                    if isinstance(item, (str, int, float, bool))
                )
                game_time = selected.get("game_time_seconds")
                first_broken = RuntimeFirstBrokenEdgeDiagnostic(
                    scenario_id=scenario_id,
                    claim_id=claim_id,
                    lifecycle_edge=str(
                        selected.get(
                            "lifecycle_edge",
                            claim.get("lifecycle_edge", ""),
                        )
                    ),
                    evidence_class=str(
                        selected.get(
                            "evidence_class",
                            claim.get("evidence_class", "OPEN / UNKNOWN"),
                        )
                    ),
                    rule_identities=tuple(
                        str(item)
                        for item in selected.get(
                            "rule_identities",
                            claim.get("rule_identities", ()),
                        )
                    ),
                    expected=_string_pairs(claim.get("expected", {})),
                    observed_facts=observed_facts,
                    world_witness=world_witness,
                    game_time_seconds=(
                        float(game_time)
                        if isinstance(game_time, (int, float))
                        else None
                    ),
                    artifact_sha256=(
                        str(artifact_sha256)
                        if artifact_sha256 is not None
                        else None
                    ),
                    message=(
                        f"runtime claim {claim_id!r} failed at "
                        f"{selected.get('lifecycle_edge', claim.get('lifecycle_edge', 'UNKNOWN'))}"
                    ),
                )
        else:
            open_claims.append(claim_id)

    if failed:
        status = RuntimeEvidenceStatus.FAILED
    elif claims and len(confirmed) == len(claims):
        status = RuntimeEvidenceStatus.CONFIRMED
    else:
        status = RuntimeEvidenceStatus.OPEN

    return RuntimeAssessment(
        scenario_id=scenario_id,
        status=status,
        artifact_sha256=(
            str(artifact_sha256) if artifact_sha256 is not None else None
        ),
        confirmed_claims=tuple(confirmed),
        failed_claims=tuple(failed),
        open_claims=tuple(open_claims),
        first_broken_edge=first_broken,
    )


__all__ = [
    "RuntimeAssessment",
    "RuntimeClaimStatus",
    "RuntimeEvidenceStatus",
    "RuntimeFirstBrokenEdgeDiagnostic",
    "assess_runtime_witness",
]
