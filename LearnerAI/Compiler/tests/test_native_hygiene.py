import unittest

from Compiler.primitives.native_hygiene import (
    AIRefProvenance,
    AIRefVersionFamily,
    CitationChangeKind,
    CitationRecord,
    CitationRecordCatalog,
    CitationSemanticScope,
    CitationState,
    ConfidenceBasis,
    ConfidenceLevel,
    EvidenceKind,
    ExcerptKind,
    ExcerptMatchKind,
    LocatorType,
    NativeGoalParameterRangeContract,
    NativeGoalSpanContract,
    NativeGoalStorageContract,
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
    default_native_citation_catalog,
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
    def test_ordinary_goal_storage_stops_at_512(self):
        NativeStorageUse(
            "ordinary-goal-512",
            NativeStorageClass.PERSISTENT_SCALAR,
            NativeStorageKind.GOAL,
            base=512,
            provenance=(provenance(),),
        )
        with self.assertRaises(ValueError):
            NativeStorageUse(
                "ordinary-goal-513",
                NativeStorageClass.PERSISTENT_SCALAR,
                NativeStorageKind.GOAL,
                base=513,
                provenance=(provenance(),),
            )

    def test_point_goal_span_stops_at_15998(self):
        NativeStorageUse(
            "point-span-last",
            NativeStorageClass.GOAL_SPAN,
            NativeStorageKind.POINT_GOAL_SPAN,
            base=15998,
            span_length=2,
            provenance=(provenance(),),
        )
        with self.assertRaises(ValueError):
            NativeStorageUse(
                "point-span-overrun",
                NativeStorageClass.GOAL_SPAN,
                NativeStorageKind.POINT_GOAL_SPAN,
                base=15999,
                span_length=2,
                provenance=(provenance(),),
            )

    def test_goal_citation_domains_are_distinct(self):
        catalog = default_native_citation_catalog()
        storage = catalog.resolve("airef:goal-storage")
        extended = catalog.resolve("airef:extended-goal-span-4")
        parameter = catalog.resolve("airef:goal-id-parameter-range")
        self.assertNotEqual(storage.citation_id, extended.citation_id)
        self.assertNotEqual(storage.citation_id, parameter.citation_id)
        self.assertNotEqual(extended.citation_id, parameter.citation_id)
        self.assertEqual(storage.locator, "Goals: 1 to 512")
        self.assertEqual(extended.locator, "up-get-search-state OutputGoalId: 41 to 15996, 4 consecutive goals")
        self.assertEqual(parameter.locator, "goal GoalId: 1 to 16000")


    def test_citation_catalog_audit_detects_unused_record(self):
        records = (
            CitationRecord(
                "ai:used",
                "https://example.test/source#used",
                "https://example.test/source#used",
                LocatorType.COMMAND,
                "used",
                excerpt=SourceExcerpt.capture("used", ExcerptKind.FACT),
                state=CitationState.VERIFIED,
            ),
            CitationRecord(
                "ai:unused",
                "https://example.test/source#unused",
                "https://example.test/source#unused",
                LocatorType.COMMAND,
                "unused",
                excerpt=SourceExcerpt.capture("unused", ExcerptKind.FACT),
                state=CitationState.VERIFIED,
            ),
        )
        audit = CitationRecordCatalog(records).audit(("ai:used",))
        self.assertEqual(audit.unused, ("ai:unused",))

    def test_citation_catalog_audit_detects_duplicate_location(self):
        records = (
            CitationRecord(
                "ai:first",
                "https://example.test/source#same",
                "https://example.test/source#same",
                LocatorType.COMMAND,
                "same",
                excerpt=SourceExcerpt.capture("same", ExcerptKind.FACT),
                state=CitationState.VERIFIED,
            ),
            CitationRecord(
                "ai:second",
                "https://example.test/source#same",
                "https://example.test/source#same",
                LocatorType.COMMAND,
                "same",
                excerpt=SourceExcerpt.capture("same", ExcerptKind.FACT),
                state=CitationState.VERIFIED,
            ),
        )
        audit = CitationRecordCatalog(records).audit(("ai:first", "ai:second"))
        self.assertEqual(audit.duplicates, (("ai:first", "ai:second"),))

    def test_citation_catalog_audit_detects_stale_record(self):
        record = CitationRecord(
            "ai:stale",
            "https://example.test/source#stale",
            "https://example.test/source#stale",
            LocatorType.COMMAND,
            "stale",
            excerpt=SourceExcerpt.capture("stale", ExcerptKind.FACT),
            state=CitationState.REVIEW_REQUIRED,
        )
        audit = CitationRecordCatalog((record,)).audit(("ai:stale",))
        self.assertEqual(audit.stale, ("ai:stale",))

    def test_citation_catalog_audit_detects_weak_command_locator(self):
        record = CitationRecord(
            "ai:weak",
            "https://example.test/source",
            "https://example.test/source",
            LocatorType.COMMAND,
            "weak-command",
            excerpt=SourceExcerpt.capture("weak command", ExcerptKind.FACT),
            state=CitationState.VERIFIED,
        )
        audit = CitationRecordCatalog((record,)).audit(("ai:weak",))
        self.assertEqual(audit.weak, ("ai:weak",))

    def test_current_default_catalog_has_no_unused_duplicate_stale_or_weak_entries(self):
        from Compiler.primitives.registry import default_native_contract_catalog

        citations = default_native_citation_catalog()
        contracts = default_native_contract_catalog()
        audit = citations.audit(contracts.citation_ids())
        self.assertTrue(audit.clean, audit)

    def test_building_type_count_citation_is_source_specific(self):
        record = default_native_citation_catalog().resolve("airef:building-type-count")
        self.assertEqual(
            record.final_url,
            "https://airef.github.io/commands/commands-details.html#building-type-count",
        )

    def test_unit_type_count_citation_is_source_specific(self):
        record = default_native_citation_catalog().resolve("airef:unit-type-count")
        self.assertEqual(
            record.final_url,
            "https://airef.github.io/commands/commands-details.html#unit-type-count",
        )

    def test_research_completed_citation_is_source_specific(self):
        record = default_native_citation_catalog().resolve("airef:research-completed")
        self.assertEqual(
            record.final_url,
            "https://airef.github.io/commands/commands-details.html#research-completed",
        )

    def test_goal_storage_citation_uses_exact_table_entry(self):
        record = default_native_citation_catalog().resolve("airef:goal-storage")
        self.assertIs(record.locator_type, LocatorType.TABLE_ENTRY)
        self.assertIs(record.semantic_scope, CitationSemanticScope.ORDINARY_PERSISTENT_GOAL_STORAGE)
        self.assertEqual(record.locator, "Goals: 1 to 512")

    def test_extended_goal_span_citations_have_extended_scope(self):
        catalog = default_native_citation_catalog()
        self.assertIs(
            catalog.resolve("airef:extended-goal-span-point").semantic_scope,
            CitationSemanticScope.EXTENDED_GOAL_SPAN,
        )
        self.assertIs(
            catalog.resolve("airef:extended-goal-span-4").semantic_scope,
            CitationSemanticScope.EXTENDED_GOAL_SPAN,
        )

    def test_goal_id_parameter_citation_has_parameter_scope(self):
        record = default_native_citation_catalog().resolve("airef:goal-id-parameter-range")
        self.assertIs(record.semantic_scope, CitationSemanticScope.GOAL_ID_PARAMETER_RANGE)
        self.assertEqual(record.locator, "goal GoalId: 1 to 16000")


    def test_citation_catalog_resolves_native_provenance(self):
        citation = CitationRecord(
            "ai:test-resolved",
            "https://airef.github.io/",
            "https://airef.github.io/",
            LocatorType.COMMAND,
            "test-command",
            excerpt=SourceExcerpt.capture("test command", ExcerptKind.FACT),
            state=CitationState.VERIFIED,
        )
        catalog = CitationRecordCatalog((citation,))
        resolved = catalog.resolve("ai:test-resolved")
        self.assertEqual(resolved.citation_id, "ai:test-resolved")

    def test_citation_catalog_rejects_missing_native_provenance(self):
        citation = CitationRecord(
            "ai:test-resolved",
            "https://airef.github.io/",
            "https://airef.github.io/",
            LocatorType.COMMAND,
            "test-command",
            excerpt=SourceExcerpt.capture("test command", ExcerptKind.FACT),
            state=CitationState.VERIFIED,
        )
        catalog = CitationRecordCatalog((citation,))
        with self.assertRaisesRegex(ValueError, "unresolved citation 'ai:missing'"):
            catalog.validate_provenance(
                (
                    AIRefProvenance(
                        evidence_kind=EvidenceKind.DOCUMENTED_FACT,
                        confidence=ConfidenceLevel.HIGH,
                        confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
                        citation_id="ai:missing",
                    ),
                ),
                require_promotable=True,
            )

    def test_non_promotable_citation_blocks_native_provenance(self):
        citation = CitationRecord(
            "ai:broken",
            "https://airef.github.io/",
            "https://airef.github.io/",
            LocatorType.COMMAND,
            "test-command",
            excerpt=SourceExcerpt.capture("test command", ExcerptKind.FACT),
            state=CitationState.BROKEN,
        )
        catalog = CitationRecordCatalog((citation,))
        with self.assertRaisesRegex(ValueError, "citation 'ai:broken' is not promotable"):
            catalog.validate_provenance(
                (
                    AIRefProvenance(
                        evidence_kind=EvidenceKind.DOCUMENTED_FACT,
                        confidence=ConfidenceLevel.HIGH,
                        confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
                        citation_id="ai:broken",
                    ),
                ),
                require_promotable=True,
            )

    def test_default_native_citation_catalog_is_complete_and_promotable(self):
        catalog = default_native_citation_catalog()
        self.assertEqual(
            {record.citation_id for record in catalog.records},
            {
                "airef:building-type-count",
                "airef:unit-type-count",
                "airef:research-completed",
                "airef:goal-storage",
                "airef:extended-goal-span-point",
                "airef:extended-goal-span-4",
                "airef:goal-id-parameter-range",
                "airef:build-pass-limit",
            },
        )
        self.assertTrue(
            all(
                promotion_state(record, already_promoted=False)
                is PromotionState.ELIGIBLE
                for record in catalog.records
            )
        )

    def test_native_contract_catalog_resolves_all_contract_provenance(self):
        from Compiler.primitives.registry import default_native_contract_catalog

        catalog = default_native_contract_catalog()
        catalog.validate_all_provenance()

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
                contract_id="cost-data-4-goal-span",
                provenance=(provenance(),),
            )

    def test_documented_goal_spans_use_shape_specific_namespace(self):
        NativeStorageUse(
            "high-goal-span",
            NativeStorageClass.GOAL_SPAN,
            NativeStorageKind.SEARCH_STATE_GOAL_SPAN,
            base=15996,
            span_length=4,
            contract_id="extended-4-goal-span",
            provenance=(provenance(),),
        )

    def test_goal_spans_cannot_overlap(self):
        left = NativeStorageUse(
            "cost-data",
            NativeStorageClass.GOAL_SPAN,
            NativeStorageKind.COST_DATA_GOAL_SPAN,
            base=100,
            span_length=4,
            contract_id="cost-data-4-goal-span",
            provenance=(provenance(),),
        )
        right = NativeStorageUse(
            "point",
            NativeStorageClass.GOAL_SPAN,
            NativeStorageKind.POINT_GOAL_SPAN,
            base=103,
            span_length=2,
            contract_id="point-goal-span",
            provenance=(provenance(),),
        )
        with self.assertRaises(ValueError):
            validate_goal_span_non_overlap((left, right))

    def test_goal_storage_contract_is_exactly_1_to_512(self):
        contract = NativeGoalStorageContract(
            "ordinary-persistent-goal-storage",
            1,
            512,
            (provenance(),),
        )
        contract.validate_id(512)
        with self.assertRaises(ValueError):
            contract.validate_id(513)

    def test_goal_span_contract_has_shape_specific_range(self):
        contract = NativeGoalSpanContract(
            "extended-4-goal-span",
            NativeStorageKind.SEARCH_STATE_GOAL_SPAN,
            4,
            41,
            15996,
            (provenance(),),
        )
        contract.validate_shape(15996, 15999)
        with self.assertRaises(ValueError):
            contract.validate_shape(15997, 16000)

    def test_goal_id_parameter_range_is_independent_from_storage_range(self):
        contract = NativeGoalParameterRangeContract(
            "goal-id-parameter-range",
            "GoalId",
            1,
            16000,
            ("goal", "set-goal"),
            (provenance(),),
        )
        contract.validate_value(16000)
        with self.assertRaises(ValueError):
            contract.validate_value(16001)

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
