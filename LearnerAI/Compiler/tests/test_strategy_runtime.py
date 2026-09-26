import unittest
from dataclasses import replace

from LearnerAI.Compiler.compiler import compile_strategy_runtime_profile
from LearnerAI.Compiler.ir.civ_profile import ByzantineProfile, resolve_effective_civ
from LearnerAI.Compiler.ir.game_data import BuildingId, CivId
from LearnerAI.Compiler.ir.strategy import (
    CapabilityIntent,
    CapabilityIntentKind,
    PostureTransition,
    StrategicCapabilityObservation,
    StrategicEnemyCompositionObservation,
    StrategicEvidence,
    StrategicEvidenceKind,
    StrategicEvidenceSource,
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
    bind_strategic_capability_observation,
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

    def test_meta_observation_preserves_source_and_provenance(self):
        evidence = self.profile.demand("castle-commitment").reason[0]
        binding = bind_strategic_evidence(evidence, self.effective)
        observation = binding.observations[0]
        self.assertEqual(observation.evidence_source, StrategicEvidenceSource.COMMUNITY_META)
        self.assertEqual(observation.provenance, evidence.provenance)

    def test_community_meta_evidence_requires_explicit_community_attribution(self):
        evidence = StrategicEvidence(
            StrategicEvidenceKind.PERSISTENT,
            "(current-age >= feudal-age)",
            "community-meta",
            source=StrategicEvidenceSource.COMMUNITY_META,
        )
        with self.assertRaisesRegex(ValueError, "COMMUNITY_REFERENCE"):
            bind_strategic_evidence(evidence, self.effective)

    def test_byzantine_unique_unit_capabilities_bind_through_native_unit_capability_family(self):
        observations = {item.identity: item for item in self.profile.capability_observations}
        self.assertEqual(
            set(observations),
            {
                "cataphract-capability",
                "varangian-guard-capability",
                "elite-varangian-guard-capability",
            },
        )
        self.assertEqual(
            {
                item.capability.entity_id
                for item in observations.values()
            },
            {40, 2703, 2704},
        )
        for item in observations.values():
            binding = bind_strategic_capability_observation(item, self.effective)
            self.assertEqual(
                binding.observations[0].semantic_type,
                StrategicObservationType.UNIT_CAPABILITY,
            )
        runtime = evaluate_strategy_runtime(
            self.profile,
            self.effective,
            self.snapshot(
                facts=tuple((item.expression, True) for item in observations.values()),
                previous=StrategyPosture.CASTLE_POWER,
            ),
        )
        self.assertEqual(
            dict(runtime.evaluated_capability_observations),
            {identity: EvidenceTruth.TRUE for identity in observations},
        )

    def test_unknown_unique_unit_capability_fails_closed(self):
        unknown = StrategicCapabilityObservation(
            identity="unknown-unique-unit",
            capability=self.profile.capability_observations[0].capability.__class__(
                self.profile.capability_observations[0].capability.kind,
                "unit",
                999999,
                self.profile.capability_observations[0].capability.provider_building,
            ),
            expression="(can-train-with-escrow cataphract)",
        )
        profile = replace(
            self.profile,
            capability_observations=(unknown,),
        )
        with self.assertRaisesRegex(ValueError, "status is UNKNOWN"):
            evaluate_strategy_runtime(profile, self.effective, self.snapshot())

    def test_community_meta_cannot_define_factual_capability(self):
        base = self.profile.capability_observations[0]
        meta = replace(
            base,
            source=StrategicEvidenceSource.COMMUNITY_META,
            provenance=self.profile.demand("castle-commitment").reason[0].provenance,
        )
        profile = replace(self.profile, capability_observations=(meta,))
        with self.assertRaisesRegex(ValueError, "community meta cannot define factual capability"):
            evaluate_strategy_runtime(profile, self.effective, self.snapshot())

    def test_byzantine_enemy_composition_observation_binds_to_enemy_unit_family(self):
        observation = self.profile.enemy_composition_observations[0]
        self.assertEqual(observation.unit_id, 38)
        binding = bind_strategic_evidence(
            StrategicEvidence(
                StrategicEvidenceKind.PERSISTENT,
                observation.expression,
                observation.identity,
            ),
            self.effective,
        )
        self.assertEqual(
            binding.observations[0].semantic_type,
            StrategicObservationType.ENEMY_UNIT_COUNT,
        )

    def test_unknown_enemy_composition_unit_fails_closed(self):
        bad = StrategicEnemyCompositionObservation(
            identity="unknown-enemy-unit",
            unit_id=999999,
            expression="(players-unit-type-count any-enemy 999999 >= 1)",
            provenance=(),
        )
        with self.assertRaisesRegex(ValueError, "status is UNKNOWN"):
            evaluate_strategy_runtime(
                replace(self.profile, enemy_composition_observations=(bad,)),
                self.effective,
                self.snapshot(),
            )

    def test_community_meta_cannot_define_enemy_composition_observation(self):
        base = self.profile.enemy_composition_observations[0]
        meta = replace(
            base,
            source=StrategicEvidenceSource.COMMUNITY_META,
            provenance=self.profile.demand("castle-commitment").reason[0].provenance,
        )
        with self.assertRaisesRegex(ValueError, "community meta cannot define factual enemy observation"):
            evaluate_strategy_runtime(
                replace(self.profile, enemy_composition_observations=(meta,)),
                self.effective,
                self.snapshot(),
            )

    def test_runtime_state_records_enemy_composition_observation_truth(self):
        observation = self.profile.enemy_composition_observations[0]
        runtime = evaluate_strategy_runtime(
            self.profile,
            self.effective,
            self.snapshot(
                facts=((observation.expression, True),),
                previous=StrategyPosture.BOOM,
            ),
        )
        self.assertEqual(
            dict(runtime.evaluated_enemy_composition_observations),
            {observation.identity: EvidenceTruth.TRUE},
        )

    def test_byzantine_meta_scope_covers_counter_defense_and_castle_transitions(self):
        labels = {item.label for item in self.profile.community_meta_evidence}
        self.assertIn("Maintain a minimum cheap defensive military floor", labels)
        self.assertIn(
            "Castle commitment is obsolete once Imperial Age is reached without the strategic Castle path",
            labels,
        )
        self.assertIn("Castle completion materially changes the strategic posture", labels)

    def test_byzantine_strategy_contains_explicitly_attributed_meta_evidence(self):
        meta = self.profile.demand("castle-commitment").reason[0]
        self.assertEqual(meta.source, StrategicEvidenceSource.COMMUNITY_META)
        self.assertTrue(meta.provenance)
        self.assertTrue(
            any(ref.kind.value == "COMMUNITY_REFERENCE" for ref in meta.provenance)
        )

    def test_runtime_state_preserves_attributed_meta_evidence_evaluation(self):
        runtime = evaluate_strategy_runtime(
            self.profile,
            self.effective,
            self.snapshot(
                facts=(("(current-age >= feudal-age)", True),),
                previous=StrategyPosture.BOOM,
            ),
        )
        self.assertTrue(runtime.evaluated_meta_evidence)
        self.assertTrue(
            any(provenance for _, _, provenance in runtime.evaluated_meta_evidence)
        )

    def test_meta_provenance_does_not_satisfy_factual_coverage(self):
        castle = self.profile.demand("castle-commitment")
        unverified = replace(
            castle,
            identity="unverified-meta-capability",
            capability_intent=CapabilityIntent(
                CapabilityIntentKind.TRAIN,
                "unit",
                550,
                BuildingId(49),
            ),
        )
        profile = replace(
            self.profile,
            demands=(
                unverified,
                *(item for item in self.profile.demands if item.identity != "castle-commitment"),
            ),
        )
        with self.assertRaisesRegex(ValueError, "factual coverage"):
            evaluate_strategy_runtime(profile, self.effective, self.snapshot())

    def test_meta_provenance_changes_binding_identity(self):
        base = StrategicEvidence(
            StrategicEvidenceKind.PERSISTENT,
            "(current-age >= feudal-age)",
            "binding",
        )
        meta = replace(
            base,
            source=StrategicEvidenceSource.COMMUNITY_META,
            provenance=self.profile.demand("castle-commitment").reason[0].provenance,
        )
        self.assertNotEqual(
            bind_strategic_evidence(base, self.effective).fingerprint,
            bind_strategic_evidence(meta, self.effective).fingerprint,
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
