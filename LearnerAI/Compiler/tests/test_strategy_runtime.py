import unittest
from dataclasses import replace

from LearnerAI.Compiler.compiler import compile_strategy_runtime_profile
from LearnerAI.Compiler.ir.civ_profile import ByzantineProfile, resolve_effective_civ
from LearnerAI.Compiler.ir.game_data import CivId
from LearnerAI.Compiler.ir.strategy import (
    PostureTransition,
    StrategicEvidence,
    StrategicEvidenceKind,
    StrategyPosture,
    StrategyProfile,
    build_byzantine_castle_strategy,
)
from LearnerAI.Compiler.ir.strategy_runtime import (
    EvidenceTruth,
    OpportunityCostRuntimeState,
    RuntimeObservationSnapshot,
    StrategicDemandRuntimeState,
    StrategicObservationType,
    StrategyRuntimeState,
    bind_strategic_evidence,
    evaluate_strategy_runtime,
)


class StrategyRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        self.profile = build_byzantine_castle_strategy(self.effective)

    def snapshot(self, facts=(), completed=(), previous=None, signals=()):
        return RuntimeObservationSnapshot(
            fact_results=tuple(facts),
            completed_demands=frozenset(completed),
            previous_posture=previous,
            reassessment_signals=frozenset(signals),
        )

    def test_persistent_castle_reason_survives_blocked_can_build(self):
        runtime = evaluate_strategy_runtime(
            self.profile,
            self.effective,
            self.snapshot(
                facts=(
                    ("(current-age >= feudal-age)", True),
                    ("(building-available castle)", True),
                    ("(can-afford-building castle)", True),
                    ("(can-build castle)", False),
                ),
                previous=StrategyPosture.BOOM,
            ),
        )
        self.assertEqual(
            runtime.demand_state("castle-commitment"),
            StrategicDemandRuntimeState.STRATEGIC_ACTIVE_BLOCKED,
        )
        self.assertIn("castle-commitment", runtime.strategically_blocked_demands)

    def test_strategic_invalidation_requires_invalidation_evidence(self):
        runtime = evaluate_strategy_runtime(
            self.profile,
            self.effective,
            self.snapshot(
                facts=(
                    ("(current-age >= feudal-age)", True),
                    ("(current-age >= imperial-age)", True),
                    ("(building-available castle)", True),
                    ("(can-afford-building castle)", True),
                    ("(can-build castle)", False),
                ),
                previous=StrategyPosture.BOOM,
            ),
        )
        self.assertEqual(
            runtime.demand_state("castle-commitment"),
            StrategicDemandRuntimeState.STRATEGIC_INVALIDATED,
        )

    def test_timing_only_posture_transition_is_rejected(self):
        bad = replace(
            self.profile,
            transitions=(
                PostureTransition(
                    from_postures=(StrategyPosture.BOOM,),
                    to_posture=StrategyPosture.RUSH,
                    priority=10,
                    evidence=(
                        StrategicEvidence(
                            StrategicEvidenceKind.TIMING,
                            "(game-time >= 600)",
                            "timer-only",
                        ),
                    ),
                    label="timer-rush",
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "timer-only"):
            evaluate_strategy_runtime(bad, self.effective, self.snapshot(
                facts=(("(game-time >= 600)", True),),
                previous=StrategyPosture.BOOM,
            ))

    def test_equal_priority_incompatible_transitions_are_rejected(self):
        bad = replace(
            self.profile,
            transitions=(
                PostureTransition(
                    from_postures=(StrategyPosture.BOOM,),
                    to_posture=StrategyPosture.FLUSH,
                    priority=50,
                    evidence=(StrategicEvidence(
                        StrategicEvidenceKind.PERSISTENT,
                        "(current-age >= feudal-age)",
                        "a",
                    ),),
                    label="a",
                ),
                PostureTransition(
                    from_postures=(StrategyPosture.BOOM,),
                    to_posture=StrategyPosture.RUSH,
                    priority=50,
                    evidence=(StrategicEvidence(
                        StrategicEvidenceKind.PERSISTENT,
                        "(current-age >= feudal-age)",
                        "b",
                    ),),
                    label="b",
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "equal-priority"):
            evaluate_strategy_runtime(
                bad,
                self.effective,
                self.snapshot(
                    facts=(("(current-age >= feudal-age)", True),),
                    previous=StrategyPosture.BOOM,
                ),
            )

    def test_highest_priority_transition_wins_deterministically(self):
        profile = replace(
            self.profile,
            transitions=(
                PostureTransition(
                    from_postures=(StrategyPosture.BOOM,),
                    to_posture=StrategyPosture.RUSH,
                    priority=10,
                    evidence=(StrategicEvidence(
                        StrategicEvidenceKind.PERSISTENT,
                        "(current-age >= feudal-age)",
                        "rush",
                    ),),
                    label="rush",
                ),
                PostureTransition(
                    from_postures=(StrategyPosture.BOOM,),
                    to_posture=StrategyPosture.FLUSH,
                    priority=20,
                    evidence=(StrategicEvidence(
                        StrategicEvidenceKind.PERSISTENT,
                        "(current-age >= feudal-age)",
                        "flush",
                    ),),
                    label="flush",
                ),
            ),
        )
        runtime = evaluate_strategy_runtime(
            profile,
            self.effective,
            self.snapshot(
                facts=(("(current-age >= feudal-age)", True),),
                previous=StrategyPosture.BOOM,
            ),
        )
        self.assertEqual(runtime.current_posture, StrategyPosture.FLUSH)

    def test_one_strategic_owner_survives_multiple_execution_mappings(self):
        spec = self.profile.demand("castle-commitment")
        self.assertGreaterEqual(len(spec.execution_demands), 1)
        runtime = evaluate_strategy_runtime(
            self.profile,
            self.effective,
            self.snapshot(
                facts=(
                    ("(current-age >= feudal-age)", True),
                    ("(building-available castle)", True),
                    ("(can-afford-building castle)", False),
                    ("(can-build castle)", False),
                    ("(current-age >= imperial-age)", False),
                ),
                previous=StrategyPosture.BOOM,
            ),
        )
        self.assertEqual(runtime.strategic_owner("castle-commitment"), "castle-trajectory")

    def test_shared_capability_identity_keeps_distinct_strategic_demands(self):
        first = self.profile.demand("castle-commitment")
        second = replace(
            first,
            identity="castle-secondary",
            owner="secondary-owner",
            opportunity_cost=None,
        )
        profile = replace(
            self.profile,
            demands=(first, second, *(item for item in self.profile.demands if item.identity not in {"castle-commitment"})),
        )
        runtime = evaluate_strategy_runtime(
            profile,
            self.effective,
            self.snapshot(
                facts=(
                    ("(current-age >= feudal-age)", True),
                    ("(building-available castle)", True),
                    ("(can-afford-building castle)", False),
                    ("(can-build castle)", False),
                    ("(current-age >= imperial-age)", False),
                ),
                previous=StrategyPosture.BOOM,
            ),
        )
        self.assertIn("castle-commitment", runtime.active_or_blocked_demands)
        self.assertIn("castle-secondary", runtime.active_or_blocked_demands)
        self.assertNotEqual(
            runtime.strategic_owner("castle-commitment"),
            runtime.strategic_owner("castle-secondary"),
        )

    def test_protected_castle_stone_survives_ordinary_feudal_execution(self):
        runtime = evaluate_strategy_runtime(
            self.profile,
            self.effective,
            self.snapshot(
                facts=(
                    ("(current-age >= feudal-age)", True),
                    ("(building-available castle)", True),
                    ("(can-afford-building castle)", False),
                    ("(can-build castle)", False),
                    ("(current-age >= imperial-age)", False),
                ),
                previous=StrategyPosture.BOOM,
            ),
        )
        self.assertEqual(
            runtime.opportunity_cost_state("castle-commitment"),
            OpportunityCostRuntimeState.PROTECTED_ACTIVE,
        )

    def test_emergency_posture_can_override_castle_protection_only_by_policy(self):
        runtime = evaluate_strategy_runtime(
            self.profile,
            self.effective,
            self.snapshot(
                facts=(
                    ("(current-age >= feudal-age)", True),
                    ("(building-available castle)", True),
                    ("(can-afford-building castle)", False),
                    ("(can-build castle)", False),
                    ("(current-age >= imperial-age)", False),
                ),
                previous=StrategyPosture.FLUSH,
            ),
        )
        self.assertEqual(
            runtime.opportunity_cost_state("castle-commitment"),
            OpportunityCostRuntimeState.OVERRIDDEN,
        )

    def test_castle_completion_releases_policy_without_resetting_other_strategy_state(self):
        runtime = evaluate_strategy_runtime(
            self.profile,
            self.effective,
            self.snapshot(
                facts=(
                    ("(current-age >= feudal-age)", True),
                    ("(building-available castle)", True),
                    ("(can-afford-building castle)", True),
                    ("(can-build castle)", False),
                    ("(building-type-count castle > 0)", True),
                    ("(current-age >= imperial-age)", False),
                ),
                completed=("castle-commitment",),
                previous=StrategyPosture.BOOM,
            ),
        )
        self.assertEqual(runtime.demand_state("castle-commitment"), StrategicDemandRuntimeState.STRATEGIC_COMPLETE)
        self.assertEqual(runtime.opportunity_cost_state("castle-commitment"), OpportunityCostRuntimeState.RELEASED)
        self.assertEqual(runtime.demand_state("early-defensive-spears"), StrategicDemandRuntimeState.STRATEGIC_ACTIVE_BLOCKED)

    def test_current_age_binds_to_native_age_parameter_family(self):
        binding = bind_strategic_evidence(
            StrategicEvidence(
                StrategicEvidenceKind.PERSISTENT,
                "(current-age >= feudal-age)",
                "age",
            ),
            self.effective,
        )
        self.assertEqual(binding.observations[0].semantic_type, StrategicObservationType.CURRENT_AGE)
        with self.assertRaisesRegex(ValueError, "native parameter family"):
            bind_strategic_evidence(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    "(current-age >= castle)",
                    "bad-age-token",
                ),
                self.effective,
            )

    def test_enemy_composition_uses_verified_native_unit_observation(self):
        binding = bind_strategic_evidence(
            StrategicEvidence(
                StrategicEvidenceKind.PERSISTENT,
                "(players-unit-type-count any-enemy knight >= 2)",
                "enemy-knights",
            ),
            self.effective,
        )
        self.assertEqual(binding.observations[0].semantic_type, StrategicObservationType.ENEMY_UNIT_COUNT)
        with self.assertRaisesRegex(ValueError, "UnitId"):
            bind_strategic_evidence(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    "(players-unit-type-count any-enemy castle >= 2)",
                    "wrong-family",
                ),
                self.effective,
            )

    def test_unresolved_native_evidence_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unresolved"):
            bind_strategic_evidence(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    "(current-age >= future-age)",
                    "unknown",
                ),
                self.effective,
            )

    def test_runtime_state_does_not_define_a_second_lifecycle(self):
        lifecycle_names = {"ACTIVE", "ISSUED", "PENDING", "COMPLETE", "RELEASED", "CANCELLED"}
        self.assertTrue(
            lifecycle_names.isdisjoint(
                {item.value for item in StrategicDemandRuntimeState}
            )
        )
        self.assertFalse(hasattr(StrategyRuntimeState, "lifecycle"))

    def test_runtime_evaluator_is_civilization_agnostic(self):
        generic = replace(self.effective, civ_id=CivId(2), civ_name="SyntheticCiv")
        runtime = evaluate_strategy_runtime(
            replace(
                self.profile,
                civ_id=generic.civ_id,
                patch_key=generic.patch.key,
                effective_snapshot_fingerprint=generic.fingerprint,
            ),
            generic,
            self.snapshot(
                facts=(("(current-age >= feudal-age)", True),),
                previous=StrategyPosture.BOOM,
            ),
        )
        self.assertIsNotNone(runtime.fingerprint)

    def test_runtime_compilation_lowers_through_existing_semantic_pipeline(self):
        artifact = compile_strategy_runtime_profile(
            self.profile,
            self.effective,
            self.snapshot(
                facts=(
                    ("(current-age >= feudal-age)", True),
                    ("(building-available castle)", True),
                    ("(can-afford-building castle)", False),
                    ("(can-build castle)", False),
                    ("(current-age >= imperial-age)", False),
                ),
                previous=StrategyPosture.BOOM,
            ),
        )
        self.assertIn("BASILISK GENERATED .PER", artifact)
        self.assertIn("(build castle)", artifact)


if __name__ == "__main__":
    unittest.main()
