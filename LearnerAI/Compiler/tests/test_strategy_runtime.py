import unittest
from dataclasses import replace

from LearnerAI.Compiler.clients.basilisk import compile_strategy_runtime_profile
from LearnerAI.Compiler.ir.civ_profile import resolve_effective_civ
from LearnerAI.Compiler.ir.game_data import BuildingId, CivId
from LearnerAI.Compiler.semantic.community_engine import CapabilityTransition

from LearnerAI.Compiler.clients.basilisk import (
    ByzantineProfile,
    CapabilityIntent,
    CapabilityIntentKind,
    CapabilityRecoveryContract,
    PostureTransition,
    StrategicCapabilityObservation,
    StrategicCapabilityObservationKind,
    StrategicTargetKind,
    StrategicEvidence,
    StrategicEvidenceKind,
    StrategicEvidenceSource,
    StrategyPosture,
    StrategyProfile,
    build_byzantine_castle_strategy,
)
from LearnerAI.Compiler.clients.basilisk import (
    EvidenceTruth,
    OpportunityCostRuntimeState,
    ReassessmentReason,
    RuntimeObservationSnapshot,
    StrategicDemandRuntimeState,
    StrategicObservationType,
    StrategyRuntimeState,
    bind_observation_reference,
    bind_strategic_capability_observation,
    bind_strategic_evidence,
    evaluate_binding,
    evaluate_strategy_runtime,
)


class StrategyRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        self.profile = build_byzantine_castle_strategy(self.effective)

    def snapshot(
        self,
        facts=(),
        completed=(),
        previous=None,
        signals=(),
        previous_capabilities=(),
    ):
        return RuntimeObservationSnapshot(
            fact_results=tuple(facts),
            completed_demands=frozenset(completed),
            previous_posture=previous,
            previous_capability_observations=tuple(previous_capabilities),
            reassessment_signals=frozenset(signals),
        )

    def test_up_compare_sn_binds_to_persistent_control_state_observation(self):
        evidence = StrategicEvidence(
            StrategicEvidenceKind.PERSISTENT,
            "(up-compare-sn 264 >= 1)",
            "persistent-sn-state",
        )
        binding = bind_strategic_evidence(evidence, self.effective)
        self.assertEqual(
            binding.observations[0].semantic_type,
            StrategicObservationType.PERSISTENT_CONTROL_STATE,
        )
        self.assertEqual(binding.observations[0].primitive, "up-compare-sn")
        self.assertEqual(
            evaluate_binding(
                binding,
                self.snapshot(facts=(("(up-compare-sn 264 >= 1)", True),)),
            ),
            EvidenceTruth.TRUE,
        )

    def test_sn264_binds_to_production_queue_capacity_control_observation(self):
        evidence = StrategicEvidence(
            StrategicEvidenceKind.PERSISTENT,
            "(up-compare-sn 264 == 3)",
            "training-queue-capacity",
        )
        binding = bind_strategic_evidence(evidence, self.effective)
        self.assertEqual(
            binding.observations[0].semantic_type,
            StrategicObservationType.PRODUCTION_QUEUE_CAPACITY_CONTROL,
        )
        self.assertEqual(binding.observations[0].primitive, "up-compare-sn")

    def test_sn264_rejects_value_outside_documented_control_range(self):
        evidence = StrategicEvidence(
            StrategicEvidenceKind.PERSISTENT,
            "(up-compare-sn 264 == 16)",
            "bad-training-queue-capacity",
        )
        with self.assertRaisesRegex(ValueError, "0..15"):
            bind_strategic_evidence(evidence, self.effective)

    def test_up_compare_sn_rejects_out_of_range_strategic_number_id(self):
        evidence = StrategicEvidence(
            StrategicEvidenceKind.PERSISTENT,
            "(up-compare-sn 512 >= 1)",
            "bad-persistent-sn",
        )
        with self.assertRaisesRegex(ValueError, "0..511"):
            bind_strategic_evidence(evidence, self.effective)

    def test_up_can_search_binds_to_duc_search_observation_type(self):
        evidence = StrategicEvidence(
            StrategicEvidenceKind.EXECUTION,
            "(up-can-search search-local)",
            "duc-search-availability",
        )
        binding = bind_strategic_evidence(evidence, self.effective)
        self.assertEqual(
            binding.observations[0].semantic_type,
            StrategicObservationType.DUC_SEARCH_AVAILABILITY,
        )
        self.assertEqual(binding.observations[0].primitive, "up-can-search")

    def test_escrow_capability_binds_to_escrow_observation_type(self):
        evidence = StrategicEvidence(
            StrategicEvidenceKind.EXECUTION,
            "(can-build-with-escrow castle)",
            "castle-escrow-feasibility",
        )
        binding = bind_strategic_evidence(evidence, self.effective)
        self.assertEqual(
            binding.observations[0].semantic_type,
            StrategicObservationType.ESCROW_CAPABILITY,
        )
        self.assertEqual(
            binding.observations[0].primitive,
            "can-build-with-escrow",
        )

    def test_attack_action_remains_closed_to_strategic_observation(self):
        evidence = StrategicEvidence(
            StrategicEvidenceKind.EXECUTION,
            "(attack-now)",
            "attack-action-is-not-observation",
        )
        with self.assertRaisesRegex(
            ValueError,
            "unsupported strategic native primitive 'attack-now'",
        ):
            bind_strategic_evidence(evidence, self.effective)

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
                            None,
                            "timer-only",
                            observation_ref="current-feudal-age",
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
                        None,
                        "a",
                        observation_ref="current-feudal-age",
                    ),),
                    label="a",
                ),
                PostureTransition(
                    from_postures=(StrategyPosture.BOOM,),
                    to_posture=StrategyPosture.RUSH,
                    priority=50,
                    evidence=(StrategicEvidence(
                        StrategicEvidenceKind.PERSISTENT,
                        None,
                        "b",
                        observation_ref="current-feudal-age",
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
                        None,
                        "rush",
                        observation_ref="current-feudal-age",
                    ),),
                    label="rush",
                ),
                PostureTransition(
                    from_postures=(StrategyPosture.BOOM,),
                    to_posture=StrategyPosture.FLUSH,
                    priority=20,
                    evidence=(StrategicEvidence(
                        StrategicEvidenceKind.PERSISTENT,
                        None,
                        "flush",
                        observation_ref="current-feudal-age",
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
        binding = bind_observation_reference(evidence, self.profile, self.effective)
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

    def test_observation_reference_binding_preserves_native_expression_and_provenance(self):
        evidence = StrategicEvidence(
            StrategicEvidenceKind.PERSISTENT,
            None,
            "enemy-knights-reference",
            observation_ref="enemy-knight-pressure",
        )
        binding = bind_observation_reference(
            evidence,
            self.profile,
            self.effective,
        )
        observation = self.profile.observation("enemy-knight-pressure")
        self.assertIsNotNone(binding.observation_reference)
        self.assertEqual(
            binding.observation_reference.reference,
            "enemy-knight-pressure",
        )
        self.assertEqual(
            binding.observation_reference.observation.expression,
            observation.expression,
        )
        self.assertEqual(
            binding.observation_reference.observation.provenance,
            observation.provenance,
        )
        self.assertEqual(
            binding.observations[0].expression.source,
            observation.expression,
        )

    def test_unknown_observation_reference_is_rejected(self):
        evidence = StrategicEvidence(
            StrategicEvidenceKind.PERSISTENT,
            None,
            "unknown-reference",
            observation_ref="does-not-exist",
        )
        with self.assertRaisesRegex(ValueError, "unknown strategic observation reference"):
            bind_observation_reference(
                evidence,
                self.profile,
                self.effective,
            )

    def test_community_evidence_cannot_define_observation_object(self):
        base = self.profile.observation("enemy-knight-pressure")
        bad = replace(
            base,
            source=StrategicEvidenceSource.COMMUNITY_META,
            provenance=self.profile.demand("castle-commitment").reason[0].provenance,
        )
        profile = replace(self.profile, observations=(bad,))
        with self.assertRaisesRegex(ValueError, "community meta cannot define native observation"):
            evaluate_strategy_runtime(
                profile,
                self.effective,
                self.snapshot(),
            )

    def test_posture_and_demand_evidence_use_observation_references(self):
        castle = self.profile.demand("castle-commitment")
        transition = next(
            item for item in self.profile.transitions
            if item.label == "enemy-mounted-pressure"
        )
        self.assertTrue(all(item.observation_ref for item in castle.reason))
        self.assertTrue(all(item.observation_ref for item in transition.evidence))

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
        self.assertIn("AOE2 .PER GENERATED BY COMPILER", artifact)
        self.assertIn("(build castle)", artifact)


    def test_strategy_demands_carry_explicit_capability_recovery_contract(self):
        demand = self.profile.demand("castle-commitment")
        self.assertIsInstance(demand.recovery, CapabilityRecoveryContract)
        self.assertTrue(demand.recovery.preserve_strategic_demand)
        self.assertTrue(demand.recovery.preserve_opportunity_cost)
        self.assertTrue(demand.recovery.reopen_on_recovery)

    def test_capability_recovery_contract_rejects_intent_destroying_policy(self):
        with self.assertRaisesRegex(
            ValueError,
            "must preserve the original strategic demand",
        ):
            CapabilityRecoveryContract(
                preserve_strategic_demand=False,
            )


    def test_capability_loss_preserves_same_demand_and_enters_blocked_state(self):
        base_capability = self.profile.capability_observations[0]
        capability = replace(
            base_capability,
            observation_kind=StrategicCapabilityObservationKind.PROVIDER_WORLD_STATE,
            expression="(building-type-count castle > 0)",
        )
        base = self.profile.demand("early-defensive-spears")
        recovery_demand = replace(
            base,
            identity="cataphract-recovery-demand",
            capability_intent=capability.capability,
            target=base.target.__class__(
                StrategicTargetKind.EXACT,
                "unit-line",
                "cataphract-line",
            ),
            execution=replace(
                base.execution,
                requirements=(
                    "(current-age >= feudal-age)",
                    "(can-train-with-escrow cataphract)",
                ),
                action="(train cataphract)",
                witness="(unit-type-count cataphract >= 1)",
                release="(unit-type-count cataphract >= 1)",
            ),
        )
        profile = replace(
            self.profile,
            capability_observations=(capability,),
            demands=(
                recovery_demand,
                *(item for item in self.profile.demands if item.identity != base.identity),
            ),
        )
        runtime = evaluate_strategy_runtime(
            profile,
            self.effective,
            self.snapshot(
                facts=(
                    ("(current-age >= feudal-age)", True),
                    (capability.expression, False),
                ),
                previous=StrategyPosture.BOOM,
                previous_capabilities=((capability.identity, True),),
            ),
        )
        self.assertEqual(
            runtime.demand_state("cataphract-recovery-demand"),
            StrategicDemandRuntimeState.STRATEGIC_ACTIVE_BLOCKED,
        )
        self.assertNotIn(
            "cataphract-recovery-demand",
            runtime.strategically_invalidated_demands,
        )
        self.assertIn(
            ReassessmentReason.CAPABILITY_LOSS,
            runtime.reassessment_reasons,
        )
        self.assertEqual(
            runtime.strategic_owner("cataphract-recovery-demand"),
            base.owner,
        )

    def test_capability_recovery_reopens_same_demand(self):
        capability = self.profile.capability_observations[0]
        base_capability = self.profile.capability_observations[0]
        capability = replace(
            base_capability,
            observation_kind=StrategicCapabilityObservationKind.PROVIDER_WORLD_STATE,
            expression="(building-type-count castle > 0)",
        )
        base = self.profile.demand("early-defensive-spears")
        recovery_demand = replace(
            base,
            identity="cataphract-recovery-demand",
            capability_intent=capability.capability,
            target=base.target.__class__(
                StrategicTargetKind.EXACT,
                "unit-line",
                "cataphract-line",
            ),
            execution=replace(
                base.execution,
                requirements=(
                    "(current-age >= feudal-age)",
                    "(can-train-with-escrow cataphract)",
                ),
                action="(train cataphract)",
                witness="(unit-type-count cataphract >= 1)",
                release="(unit-type-count cataphract >= 1)",
            ),
        )
        profile = replace(
            self.profile,
            capability_observations=(capability,),
            demands=(
                recovery_demand,
                *(item for item in self.profile.demands if item.identity != base.identity),
            ),
        )
        runtime = evaluate_strategy_runtime(
            profile,
            self.effective,
            self.snapshot(
                facts=(
                    ("(current-age >= feudal-age)", True),
                    (capability.expression, True),
                    ("(can-train-with-escrow cataphract)", True),
                ),
                previous=StrategyPosture.BOOM,
                previous_capabilities=((capability.identity, False),),
            ),
        )
        self.assertEqual(
            runtime.demand_state("cataphract-recovery-demand"),
            StrategicDemandRuntimeState.STRATEGIC_ACTIVE_EXECUTABLE,
        )
        self.assertIn(
            ReassessmentReason.CAPABILITY_RECOVERY,
            runtime.reassessment_reasons,
        )
        self.assertIn(
            "cataphract-recovery-demand",
            runtime.active_strategic_demands,
        )

    def test_capability_recovery_contract_rejects_opportunity_cost_release_on_loss(self):
        demand = self.profile.demand("castle-commitment")
        bad = replace(
            demand,
            recovery=CapabilityRecoveryContract(
                preserve_opportunity_cost=False,
            ),
        )
        profile = replace(
            self.profile,
            demands=(
                bad,
                *(item for item in self.profile.demands if item.identity != bad.identity),
            ),
        )
        with self.assertRaisesRegex(
            ValueError,
            "cannot release opportunity-cost protection",
        ):
            evaluate_strategy_runtime(
                profile,
                self.effective,
                self.snapshot(
                    facts=(("(current-age >= feudal-age)", True),),
                    previous=StrategyPosture.BOOM,
                ),
            )

    def test_feasibility_false_is_not_capability_loss(self):
        observation = self.profile.capability_observations[0]
        runtime = evaluate_strategy_runtime(
            self.profile,
            self.effective,
            self.snapshot(
                facts=(
                    ("(current-age >= feudal-age)", True),
                    (observation.expression, False),
                ),
                previous=StrategyPosture.BOOM,
                previous_capabilities=((observation.identity, True),),
            ),
        )
        self.assertEqual(runtime.capability_transitions, ())

    def test_provider_loss_is_detected_from_previous_world_state(self):
        base = self.profile.capability_observations[0]
        provider = replace(
            base,
            observation_kind=StrategicCapabilityObservationKind.PROVIDER_WORLD_STATE,
            expression="(building-type-count castle > 0)",
        )
        profile = replace(self.profile, capability_observations=(provider,))
        runtime = evaluate_strategy_runtime(
            profile,
            self.effective,
            self.snapshot(
                facts=(
                    ("(current-age >= feudal-age)", True),
                    ("(building-type-count castle > 0)", False),
                ),
                previous=StrategyPosture.BOOM,
                previous_capabilities=((provider.identity, True),),
            ),
        )
        self.assertEqual(
            runtime.capability_transitions,
            ((provider.identity, CapabilityTransition.LOST),),
        )

    def test_provider_recovery_is_detected_without_creating_new_demand_identity(self):
        base = self.profile.capability_observations[0]
        provider = replace(
            base,
            observation_kind=StrategicCapabilityObservationKind.PROVIDER_WORLD_STATE,
            expression="(building-type-count castle > 0)",
        )
        profile = replace(self.profile, capability_observations=(provider,))
        runtime = evaluate_strategy_runtime(
            profile,
            self.effective,
            self.snapshot(
                facts=(
                    ("(current-age >= feudal-age)", True),
                    ("(building-type-count castle > 0)", True),
                ),
                previous=StrategyPosture.BOOM,
                previous_capabilities=((provider.identity, False),),
            ),
        )
        self.assertEqual(
            runtime.capability_transitions,
            ((provider.identity, CapabilityTransition.RECOVERED),),
        )
        self.assertEqual(runtime.demand_states, tuple(sorted(runtime.demand_states)))
        self.assertIn(
            "castle-commitment",
            runtime.active_or_blocked_demands,
        )


if __name__ == "__main__":
    unittest.main()
