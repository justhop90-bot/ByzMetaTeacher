"""Typed community-idiom coverage ledger (Phase 8 instrument).

Each major community idiom progresses DISCOVERED -> CORROBORATED ->
SEMANTICIZED -> EXPRESSIBLE -> LOWERABLE -> VERIFIED. This module is the
compiler-owned measurement instrument for that scale: a frozen record
per idiom with stage-gated evidence pointers, validated structurally.
It does not replace the research catalog (B-community_per_idiom_catalog)
and it never promotes an idiom past its evidence: every stage above
DISCOVERED requires named evidence, and VERIFIED additionally requires
named regression tests plus a lowering fixture.

Lineage discipline (no double-counting shared ancestry as independent
corroboration) lives in the corroboration text and is human-reviewed;
the validator enforces structure, not historiography.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IdiomStage(str, Enum):
    """Coverage stages in strict promotion order."""

    DISCOVERED = "DISCOVERED"
    CORROBORATED = "CORROBORATED"
    SEMANTICIZED = "SEMANTICIZED"
    EXPRESSIBLE = "EXPRESSIBLE"
    LOWERABLE = "LOWERABLE"
    VERIFIED = "VERIFIED"


_STAGE_ORDER = tuple(IdiomStage)


def _stage_rank(stage: IdiomStage) -> int:
    return _STAGE_ORDER.index(stage)


@dataclass(frozen=True)
class IdiomCoverageRecord:
    """One idiom's measured position on the coverage scale."""

    idiom_id: str
    domain: str
    stage: IdiomStage
    corroboration: str
    semantic_surface: str = ""
    construction_entry: str = ""
    lowering_evidence: str = ""
    verification_tests: tuple[str, ...] = ()
    open_boundary: str = ""

    def __post_init__(self) -> None:
        import re

        if not re.fullmatch(r"IDIOM-\d{3}", self.idiom_id):
            raise ValueError(
                f"idiom id '{self.idiom_id}' must look like IDIOM-001"
            )
        if not self.domain.strip():
            raise ValueError(f"idiom '{self.idiom_id}' domain must not be empty")
        if not isinstance(self.stage, IdiomStage):
            raise ValueError(f"idiom '{self.idiom_id}' stage must be an IdiomStage")
        if not self.corroboration.strip():
            raise ValueError(f"idiom '{self.idiom_id}' corroboration must not be empty")
        if not self.open_boundary.strip():
            raise ValueError(
                f"idiom '{self.idiom_id}' must state its explicit open boundary"
            )
        rank = _stage_rank(self.stage)
        if rank >= _stage_rank(IdiomStage.SEMANTICIZED) and not self.semantic_surface.strip():
            raise ValueError(
                f"idiom '{self.idiom_id}' at {self.stage.value} must name its semantic surface"
            )
        if rank >= _stage_rank(IdiomStage.EXPRESSIBLE) and not self.construction_entry.strip():
            raise ValueError(
                f"idiom '{self.idiom_id}' at {self.stage.value} must name its construction entry"
            )
        if rank >= _stage_rank(IdiomStage.LOWERABLE) and not self.lowering_evidence.strip():
            raise ValueError(
                f"idiom '{self.idiom_id}' at {self.stage.value} must name its lowering evidence"
            )
        if self.stage is IdiomStage.VERIFIED and not self.verification_tests:
            raise ValueError(
                f"idiom '{self.idiom_id}' at VERIFIED must name regression tests"
            )


# Seed: idioms this project train demonstrably closed, plus the two
# already-YES idioms with pre-existing proof. Stages are conservative:
# nothing above LOWERABLE except pre-existing YES rows with named tests.
IDIOM_COVERAGE_SEED: tuple[IdiomCoverageRecord, ...] = (
    IdiomCoverageRecord(
        idiom_id="IDIOM-006",
        domain="economy/production",
        stage=IdiomStage.LOWERABLE,
        corroboration="lewisc64/aoe2ai transpiler emits + Promisory trains (convergent)",
        semantic_surface="semantic/production_arbitration.py + ir/production.py",
        construction_entry="derive_production_arbitration",
        lowering_evidence="tests/fixtures/production_arbitration.perdsl + assert_production_arbitration_native.py",
        verification_tests=("tests/test_production_arbitration.py",),
        open_boundary="SN 264 enforcement, provider busy/queue, same-pass visibility, totals-as-witness rejected by design",
    ),
    IdiomCoverageRecord(
        idiom_id="IDIOM-007",
        domain="economy/research",
        stage=IdiomStage.LOWERABLE,
        corroboration="Promisory + Duke (independent impls; shared UP primitives)",
        semantic_surface="semantic/resource_control.py escrow plans + ir/resource_control.py",
        construction_entry="lower_strategy_profile escrow release operations",
        lowering_evidence="tests/fixtures/research_escrow.perdsl + assert_research_escrow_native.py",
        verification_tests=("tests/test_native_escrow_release.py",),
        open_boundary="same-pass release visibility, starvation/emergency release, competing-owner engine behavior",
    ),
    IdiomCoverageRecord(
        idiom_id="IDIOM-009",
        domain="strategy/goals",
        stage=IdiomStage.LOWERABLE,
        corroboration="Duke constants.per + Promisory const files (convergent need; independent values)",
        semantic_surface="ir/strategy.py GoalStateAssertion + control-plane channel",
        construction_entry="lower_strategy_profile goal-state control plan",
        lowering_evidence="assert_strategy_goal_state_native.py (castle+war-posture vertical)",
        verification_tests=("tests/test_strategy_goal_state.py",),
        open_boundary="multi-state FSM synthesis, jump dispatch, one-shot ownership; same-pass visibility engine-ordered",
    ),
    IdiomCoverageRecord(
        idiom_id="IDIOM-016",
        domain="military/duc",
        stage=IdiomStage.LOWERABLE,
        corroboration="Duke attack/discovery + lewisc64 templates (convergent UP patterns)",
        semantic_surface="semantic/duc.py target paths + ir/native_duc.py plans",
        construction_entry="NativeDucPlan + NativeDucGoalInputRequest handoff",
        lowering_evidence="assert_duc_target_reacquisition_native.py (discover/store/reacquire/consume)",
        verification_tests=("tests/test_duc_target_reacquisition.py",),
        open_boundary="DSL authoring absent by design; target liveness OPEN",
    ),
    IdiomCoverageRecord(
        idiom_id="IDIOM-017",
        domain="military/duc",
        stage=IdiomStage.EXPRESSIBLE,
        corroboration="lewisc64/aoe2ai + Promisory up-find volume (convergent need)",
        semantic_surface="semantic/duc.py filters/sorts/groups + ir/native_duc.py plans",
        construction_entry="NativeDucPlan with filter/mutation/group commands",
        open_boundary="no single filter+sort+groups+consume lowering vertical proven; runtime membership/flags OPEN",
    ),
    IdiomCoverageRecord(
        idiom_id="IDIOM-018",
        domain="economy/duc",
        stage=IdiomStage.SEMANTICIZED,
        corroboration="lewisc64 ManageScouting/LureBoars + Promisory boarhunting (convergent)",
        semantic_surface="semantic/duc.py up-find-remote + up-target-point paths",
        open_boundary="up-lerp-tiles and up-request-hunters unmodeled; no lure lowering vertical",
    ),
    IdiomCoverageRecord(
        idiom_id="IDIOM-019",
        domain="control/rules",
        stage=IdiomStage.VERIFIED,
        corroboration="universal across local corpus + Duke (convergent)",
        semantic_surface="emitter demand initialization + recurrent scheduler model",
        construction_entry="emitter/per.py demand-init rules with disable-self",
        lowering_evidence="generic CompilerFixture.per demand-init section",
        verification_tests=("tests/test_compiler_hardening.py",),
        open_boundary="first-pass firing order against later eligible rules stays engine-ordered",
    ),
    IdiomCoverageRecord(
        idiom_id="IDIOM-021",
        domain="control/loads",
        stage=IdiomStage.VERIFIED,
        corroboration="Duke loader + lib (single lineage; behavior standard)",
        semantic_surface="source_graph.py conditionals + semantic/source_graph_validation.py",
        construction_entry="SourceGraphRequest entrypoint with defined-symbol environment",
        lowering_evidence="tests/fixtures/source_graph/conditional-defined + conditional-not-defined",
        verification_tests=("tests/test_source_graph.py",),
        open_boundary="DE map-set drift (pre-DE map names); load-random runtime choice OPEN",
    ),
    IdiomCoverageRecord(
        idiom_id="IDIOM-024",
        domain="economy/production",
        stage=IdiomStage.EXPRESSIBLE,
        corroboration="Promisory research rules (needs file-level cite)",
        semantic_surface="ir/research.py lifecycle + semantic/resource_control.py escrow plans",
        construction_entry="ResearchLifecycle + NativeEscrowReleasePlan operations",
        open_boundary="no protected-reassertion lowering vertical proven; escrow-claim lowering open",
    ),
    IdiomCoverageRecord(
        idiom_id="IDIOM-028",
        domain="control/packaging",
        stage=IdiomStage.VERIFIED,
        corroboration="observed local single-source loader",
        semantic_surface="source_graph.py linear load resolution",
        construction_entry="SourceGraphRequest entrypoint",
        lowering_evidence="tests/fixtures/source_graph/linear",
        verification_tests=("tests/test_source_graph.py",),
        open_boundary="package collisions between co-loaded AIs OPEN",
    ),
)


def validate_idiom_coverage(
    records: tuple[IdiomCoverageRecord, ...] | list[IdiomCoverageRecord] = IDIOM_COVERAGE_SEED,
) -> tuple[IdiomCoverageRecord, ...]:
    """Validate ledger structure; returns records sorted by idiom id."""
    ordered = tuple(sorted(records, key=lambda record: record.idiom_id))
    seen: set[str] = set()
    for record in ordered:
        if record.idiom_id in seen:
            raise ValueError(f"duplicate idiom coverage id '{record.idiom_id}'")
        seen.add(record.idiom_id)
    return ordered


__all__ = [
    "IDIOM_COVERAGE_SEED",
    "IdiomCoverageRecord",
    "IdiomStage",
    "validate_idiom_coverage",
]
