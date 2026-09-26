import unittest

from Compiler.primitives.native_hygiene import (
    AIRefProvenance,
    AIRefVersionFamily,
    CitationChangeKind,
    CitationRecord,
    CitationState,
    ConfidenceBasis,
    ConfidenceLevel,
    EvidenceKind,
    ExcerptKind,
    ExcerptMatchKind,
    LocatorType,
    NativeStorageClass,
    NativeStorageKind,
    NativeStorageUse,
    NativeWitness,
    NativeWitnessKind,
    PassConstraintScope,
    PassExecutionConstraint,
    PassFailureMode,
    PerformanceClass,
    PerformanceEvidence,
    PromotionState,
    RevalidationResult,
    SourceContentHash,
    SourceRetrieval,
    SourceExcerpt,
    VersionScope,
    classify_revalidation,
    compare_excerpts,
    next_citation_state,
    promotion_state,
    validate_goal_span_non_overlap,
)


def provenance(
    kind: EvidenceKind = EvidenceKind.DOCUMENTED_FACT,
    basis: ConfidenceBasis = ConfidenceBasis.EXPLICIT_AIREf_TEXT,
) -> AIRefProvenance:
    return AIRefProvenance(
        evidence_kind=kind,
        confidence=ConfidenceLevel.HIGH,
        confidence_basis=basis,
        citation_id="ai:test",
        parent_evidence=("ai:parent",) if kind is EvidenceKind.INFERRED_MAPPING else (),
        derivation="mechanically derived" if kind is EvidenceKind.INFERRED_MAPPING else None,
    )


class NativeHygieneTests(unittest.TestCase):

    def test_native_witness_requires_documented_native_fact(self):
        with self.assertRaises(ValueError):
            NativeWitness(
                "inferred-witness",
                NativeWitnessKind.UNIT_COUNT,
                "unit-type-count",
                subject="spearman",
                comparator=">=",
                value=1,
                provenance=(
                    provenance(
                        EvidenceKind.INFERRED_MAPPING,
                        ConfidenceBasis.MECHANICAL_DERIVATION,
                    ),
                ),
            )

    def test_native_storage_requires_documented_native_fact(self):
        with self.assertRaises(ValueError):
            NativeStorageUse(
                "inferred-storage",
                NativeStorageClass.PERSISTENT_SCALAR,
                NativeStorageKind.GOAL,
                symbolic=True,
                request_purpose="lifecycle",
                provenance=(
                    provenance(
                        EvidenceKind.INFERRED_MAPPING,
                        ConfidenceBasis.MECHANICAL_DERIVATION,
                    ),
                ),
            )

    def test_native_witness_validates_comparator_and_evidence_shape(self):
        with self.assertRaises(ValueError):
            NativeWitness(
                "bad-comparator",
                NativeWitnessKind.UNIT_COUNT,
                "unit-type-count",
                subject="spearman",
                comparator="approximately",
                value=1,
                provenance=(provenance(),),
            )
        with self.assertRaises(ValueError):
            NativeWitness(
                "missing-evidence",
                NativeWitnessKind.UNIT_COUNT,
                "unit-type-count",
                subject="spearman",
                provenance=(provenance(),),
            )

    def test_engine_managed_state_requires_native_state_kind(self):
        with self.assertRaises(ValueError):
            NativeStorageUse(
                "bad-state",
                NativeStorageClass.ENGINE_MANAGED_STATE,
                NativeStorageKind.DUC_LOCAL_LIST,
                provenance=(provenance(),),
            )

    def test_ai_ref_storage_limits_are_enforced(self):
        NativeStorageUse(
            "goal-target",
            NativeStorageClass.PERSISTENT_SCALAR,
            NativeStorageKind.GOAL,
            base=400,
            provenance=(provenance(),),
        )
        NativeStorageUse(
            "duc-local",
            NativeStorageClass.ENGINE_MANAGED_LIST,
            NativeStorageKind.DUC_LOCAL_LIST,
            maximum_cardinality=240,
            provenance=(provenance(),),
        )
        NativeStorageUse(
            "duc-remote",
            NativeStorageClass.ENGINE_MANAGED_LIST,
            NativeStorageKind.DUC_REMOTE_LIST,
            maximum_cardinality=40,
            provenance=(provenance(),),
        )
        with self.assertRaises(ValueError):
            NativeStorageUse(
                "bad-span",
                NativeStorageClass.GOAL_SPAN,
                NativeStorageKind.COST_DATA_GOAL_SPAN,
                base=40,
                span_length=4,
                provenance=(provenance(),),
            )

    def test_documented_goal_spans_use_the_full_goal_namespace(self):
        NativeStorageUse(
            "high-goal-span",
            NativeStorageClass.GOAL_SPAN,
            NativeStorageKind.SEARCH_STATE_GOAL_SPAN,
            base=15996,
            span_length=4,
            provenance=(provenance(),),
        )

    def test_goal_spans_cannot_overlap(self):
        left = NativeStorageUse(
            "cost-data",
            NativeStorageClass.GOAL_SPAN,
            NativeStorageKind.COST_DATA_GOAL_SPAN,
            base=100,
            span_length=4,
            provenance=(provenance(),),
        )
        right = NativeStorageUse(
            "point",
            NativeStorageClass.GOAL_SPAN,
            NativeStorageKind.POINT_GOAL_SPAN,
            base=103,
            span_length=2,
            provenance=(provenance(),),
        )
        with self.assertRaises(ValueError):
            validate_goal_span_non_overlap((left, right))

    def test_witness_keeps_total_pending_and_completion_distinct(self):
        NativeWitness(
            "spears-total",
            NativeWitnessKind.UNIT_COUNT_TOTAL,
            "unit-type-count-total",
            subject="spearman-line",
            comparator=">=",
            value=3,
            provenance=(provenance(),),
        )
        NativeWitness(
            "house-pending",
            NativeWitnessKind.PENDING_OBJECTS,
            "up-pending-objects",
            subject="house",
            comparator=">=",
            value=1,
            provenance=(provenance(),),
        )

    def test_pass_constraint_requires_documented_native_evidence(self):
        PassExecutionConstraint(
            "build-one-per-pass",
            "up-build",
            PassConstraintScope.RULE_PASS,
            maximum_successes=1,
            failure_mode=PassFailureMode.NO_EFFECT,
            provenance=(provenance(),),
        )
        with self.assertRaises(ValueError):
            PassExecutionConstraint(
                "bad",
                "up-build",
                PassConstraintScope.RULE_PASS,
                maximum_successes=1,
                failure_mode=PassFailureMode.NO_EFFECT,
                provenance=(
                    provenance(
                        EvidenceKind.INFERRED_MAPPING,
                        ConfidenceBasis.MECHANICAL_DERIVATION,
                    ),
                ),
            )

    def test_version_scope_rejects_benchmark_provenance(self):
        VersionScope(
            supported_families=(AIRefVersionFamily.DE,),
            provenance=(provenance(),),
        )
        with self.assertRaises(ValueError):
            VersionScope(
                supported_families=(AIRefVersionFamily.DE,),
                provenance=(
                    provenance(
                        EvidenceKind.BENCHMARK_OBSERVATION,
                        ConfidenceBasis.CONTEXTUAL_BENCHMARK,
                    ),
                ),
            )

    def test_performance_evidence_is_benchmark_only(self):
        PerformanceEvidence(
            "duc-local-240",
            "up-find-local",
            PerformanceClass.MEDIUM,
            "240 existing units among 400",
            tested_cardinality=240,
            loops_for_lag=80000,
            lag_fraction=0.5,
            version_context="AIRef benchmark",
            map_context="WK",
            speed_context="fast",
            provenance=(
                provenance(
                    EvidenceKind.BENCHMARK_OBSERVATION,
                    ConfidenceBasis.CONTEXTUAL_BENCHMARK,
                ),
            ),
        )
        with self.assertRaises(ValueError):
            PerformanceEvidence(
                "bad",
                "up-find-local",
                PerformanceClass.MEDIUM,
                "benchmark",
                provenance=(provenance(),),
            )

    def test_excerpt_hash_and_revalidation(self):
        stored = SourceExcerpt.capture(
            "line one\r\nline two\r\n",
            ExcerptKind.FACT,
        )
        self.assertEqual(
            compare_excerpts(stored, "line one\nline two\n"),
            ExcerptMatchKind.NORMALIZED,
        )
        self.assertEqual(
            classify_revalidation(
                url_changed=False,
                locator_changed=False,
                source_hash_changed=True,
                excerpt_match=ExcerptMatchKind.EXACT,
                source_available=True,
            ),
            RevalidationResult.SOURCE_CHANGED_EXCERPT_MATCHED,
        )
        self.assertEqual(
            next_citation_state(
                CitationState.PINNED,
                RevalidationResult.SOURCE_CHANGED_EXCERPT_MATCHED,
            ),
            CitationState.VERIFIED_SOURCE_CHANGED,
        )
        self.assertEqual(
            next_citation_state(
                CitationState.VERIFIED,
                RevalidationResult.EXCERPT_CHANGED,
            ),
            CitationState.REVIEW_REQUIRED,
        )

    def test_promotion_rules_preserve_existing_evidence_on_outage(self):
        citation = CitationRecord(
            "c1",
            "https://airef.github.io/",
            "https://airef.github.io/",
            LocatorType.COMMAND,
            "up-find-local",
            excerpt=SourceExcerpt.capture("text", ExcerptKind.FACT),
            source_hash=SourceContentHash("sha256", "0" * 64, "RAW_BYTES"),
            retrieval=SourceRetrieval(
                retrieved_at_utc="2026-09-26T17:30:00Z",
                canonical_url="https://airef.github.io/",
                final_url="https://airef.github.io/",
                http_status=200,
            ),
            state=CitationState.UNAVAILABLE,
        )
        self.assertEqual(
            promotion_state(citation, already_promoted=True),
            PromotionState.EXISTING_PROMOTION_RETAINED,
        )
        self.assertEqual(
            promotion_state(citation, already_promoted=False),
            PromotionState.NOT_ELIGIBLE,
        )


    def test_provenance_basis_is_strict(self):
        with self.assertRaises(ValueError):
            provenance(
                EvidenceKind.DOCUMENTED_FACT,
                ConfidenceBasis.MECHANICAL_DERIVATION,
            )
        with self.assertRaises(ValueError):
            provenance(
                EvidenceKind.BENCHMARK_OBSERVATION,
                ConfidenceBasis.EXPLICIT_AIREf_TEXT,
            )

    def test_broken_excerpt_transitions_to_broken(self):
        self.assertEqual(
            next_citation_state(
                CitationState.PINNED,
                RevalidationResult.SOURCE_CHANGED_EXCERPT_BROKEN,
            ),
            CitationState.BROKEN,
        )

    def test_reviewed_states_block_revalidation_back_to_verified_without_repair(self):
        with self.assertRaises(ValueError):
            next_citation_state(
                CitationState.REVIEW_REQUIRED,
                RevalidationResult.VERIFIED_UNCHANGED,
            )

    def test_superseded_is_terminal(self):
        with self.assertRaises(ValueError):
            next_citation_state(
                CitationState.SUPERSEDED,
                RevalidationResult.VERIFIED_UNCHANGED,
            )


    def test_pinned_citation_requires_retrieval_metadata(self):
        with self.assertRaises(ValueError):
            CitationRecord(
                "pinned-missing-retrieval",
                "https://airef.github.io/",
                "https://airef.github.io/",
                LocatorType.COMMAND,
                "up-find-local",
                excerpt=SourceExcerpt.capture("text", ExcerptKind.FACT),
                source_hash=SourceContentHash("sha256", "0" * 64, "RAW_BYTES"),
                state=CitationState.PINNED,
            )

    def test_revalidation_event_retains_locations(self):
        from Compiler.primitives.native_hygiene import CitationRevalidationEvent, RevalidationTrigger

        event = CitationRevalidationEvent(
            event_id="evt-1",
            evidence_id="evidence-1",
            trigger=RevalidationTrigger.SCHEDULED,
            previous_citation_id="c1",
            current_citation_id="c2",
            previous_url="https://airef.github.io/old",
            current_url="https://airef.github.io/new",
            previous_locator="old-heading",
            current_locator="new-heading",
            changes=(
                CitationChangeKind.URL_CHANGED,
                CitationChangeKind.LOCATOR_CHANGED,
                CitationChangeKind.SOURCE_HASH_CHANGED,
            ),
            previous_source_hash="0" * 64,
            current_source_hash="1" * 64,
            previous_excerpt_hash="0" * 64,
            current_excerpt_hash="0" * 64,
            excerpt_match=ExcerptMatchKind.EXACT,
            result=RevalidationResult.SOURCE_CHANGED_EXCERPT_MATCHED,
            source_available=True,
        )
        self.assertEqual(event.previous_locator, "old-heading")
        self.assertEqual(event.current_locator, "new-heading")


if __name__ == "__main__":
    unittest.main()
