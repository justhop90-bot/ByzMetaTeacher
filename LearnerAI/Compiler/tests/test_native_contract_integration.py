import unittest
from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.compiler import compile_source
from Compiler.errors import CompileError
from Compiler.primitives import (
    NativeContractCatalog,
    NativeStorageClass,
    NativeStorageKind,
    NativeStorageUse,
    default_de_registry,
    default_native_contract_catalog,
)
from Compiler.primitives.engine_semantics import default_engine_semantic_mapping_registry
from Compiler.primitives.native_hygiene import (
    AIRefProvenance,
    CitationRecord,
    CitationRecordCatalog,
    CitationState,
    ConfidenceBasis,
    ConfidenceLevel,
    EvidenceKind,
    ExcerptKind,
    LocatorType,
    PassFailureMode,
    SourceExcerpt,
)
from Compiler.primitives.native_schema import load_default_native_schema
from Compiler.primitives.registry import NativeSupportState, PrimitiveRegistry


SOURCE = """
demand castle {
    require (can-build castle)
    action (build castle)
    witness (building-type-count castle > 0)
    release (building-type-count castle > 0)
}
"""


def build_registry(catalog):
    base = default_de_registry()
    primitives = tuple(
        base.require(name) for name in base.names()
    )
    return PrimitiveRegistry(
        primitives,
        native_registry=load_default_native_schema(),
        semantic_mappings=default_engine_semantic_mapping_registry(),
        native_contracts=catalog,
    )


def fact_provenance():
    return (
        AIRefProvenance(
            evidence_kind=EvidenceKind.DOCUMENTED_FACT,
            confidence=ConfidenceLevel.HIGH,
            confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
            citation_id="airef:building-type-count",
        ),
    )


class NativeContractIntegrationTests(unittest.TestCase):
    def test_default_goal_contracts_remain_distinct(self):
        catalog = default_native_contract_catalog()
        goal = catalog.goal_storage_contract("ordinary-persistent-goal-storage")
        span = catalog.goal_span_contract("extended-4-goal-span")
        parameter = catalog.parameter_range("goal-id-parameter-range")
        self.assertEqual((goal.minimum_id, goal.maximum_id), (1, 512))
        self.assertEqual((span.width, span.minimum_start, span.maximum_start), (4, 41, 15996))
        self.assertEqual((parameter.minimum, parameter.maximum), (1, 16000))
        self.assertEqual(catalog.parameter_ranges_for("goal", "GoalId"), (parameter,))
        self.assertEqual(catalog.parameter_ranges_for("set-goal", "GoalId"), (parameter,))

    def test_shared_catalog_exposes_duc_contracts_and_evidence_ids(self):
        catalog = default_native_contract_catalog()

        search = catalog.duc_search("up-find-local")
        remote_search = catalog.duc_search("up-find-remote")
        for contract in (search, remote_search):
            self.assertTrue(contract.supports_fact)
            self.assertEqual(contract.cursor_model, "SCAN_FRONTIER")
            self.assertTrue(contract.returns_false_on_zero_results)
            self.assertTrue(contract.stops_on_capacity)
        mutation = catalog.duc_mutation("up-remove-objects")
        for command, relation, writes_goal in (
            ("up-object-data", "SELECTED_OBJECT", False),
            ("up-get-object-data", "SELECTED_OBJECT", True),
            ("up-object-target-data", "SELECTED_OBJECT_TARGET", False),
            ("up-get-object-target-data", "SELECTED_OBJECT_TARGET", True),
        ):
            contract = catalog.duc_target_data_contract(command)
            self.assertIsNotNone(contract)
            self.assertEqual(contract.relation, relation)
            self.assertEqual(contract.writes_goal, writes_goal)
            if writes_goal:
                self.assertEqual(contract.output_width, 1)
                self.assertEqual((contract.output_goal_min, contract.output_goal_max), (1, 16000))

        consumer = catalog.duc_target_consumer("up-target-objects")
        self.assertIsNotNone(consumer)
        self.assertEqual((consumer.option_min, consumer.option_max), (0, 1))
        self.assertTrue(consumer.option_zero_requires_local_list)
        self.assertTrue(consumer.option_one_requires_object_target)
        self.assertEqual(consumer.evidence_ids, ("airef:duc:target-objects",))

        direct_target = catalog.duc_target("up-set-target-by-id")
        self.assertIsNotNone(direct_target)
        self.assertEqual(direct_target.identity_kind, "NATIVE_ID")
        self.assertEqual(direct_target.evidence_ids, ("airef:duc:set-target-by-id",))

        target = catalog.duc_target("up-set-target-object")

        self.assertIsNotNone(search)
        self.assertEqual(search.list_kind, "LOCAL")
        self.assertEqual(search.capacity, 240)
        self.assertEqual(search.evidence_ids, ("airef:duc:find-local",))

        self.assertIsNotNone(mutation)
        self.assertEqual(mutation.evidence_ids, ("airef:duc:remove-objects",))

        self.assertIsNotNone(target)
        self.assertEqual(target.evidence_ids, ("airef:duc:set-target-object",))

        citation_ids = set(catalog.citation_ids())
        self.assertIn("airef:duc:find-local", citation_ids)
        self.assertIn("airef:duc:remove-objects", citation_ids)
        self.assertIn("airef:duc:set-target-by-id", citation_ids)
        self.assertIn("airef:duc:target-objects", citation_ids)
        self.assertIn("airef:duc:set-target-object", citation_ids)
        self.assertIn("airef:duc:object-data", citation_ids)
        self.assertIn("airef:duc:get-object-data", citation_ids)
        self.assertIn("airef:duc:object-target-data", citation_ids)
        self.assertIn("airef:duc:get-object-target-data", citation_ids)
        self.assertIn("airef:duc:get-search-state", citation_ids)

    def test_shared_catalog_exposes_first_class_duc_group_contracts(self):
        catalog = default_native_contract_catalog()

        create = catalog.duc_group("up-create-group")
        reset = catalog.duc_group("up-reset-group")
        set_group = catalog.duc_group("up-set-group")
        size = catalog.duc_group("up-group-size")
        get_size = catalog.duc_group("up-get-group-size")
        flag = catalog.duc_group("up-modify-group-flag")

        self.assertEqual((create.group_id_min, create.group_id_max), (0, 19))
        self.assertEqual(create.capacity, 40)
        self.assertEqual(create.list_kinds, ("LOCAL",))
        self.assertEqual(reset.operation, "RESET")
        self.assertEqual(set_group.list_kinds, ("LOCAL", "REMOTE"))
        self.assertTrue(set_group.replaces_search_list)
        self.assertTrue(set_group.requires_group)
        self.assertEqual(size.operation, "SIZE_FACT")
        self.assertEqual(get_size.operation, "SIZE_OUTPUT")
        self.assertEqual(flag.operation, "MODIFY_FLAG")

        for citation_id in (
            "airef:duc:create-group",
            "airef:duc:reset-group",
            "airef:duc:set-group",
            "airef:duc:group-size",
            "airef:duc:get-group-size",
            "airef:duc:modify-group-flag",
        ):
            self.assertIn(citation_id, set(catalog.citation_ids()))

    def test_group_size_contract_has_concrete_goal_output_span_shape(self):
        catalog = default_native_contract_catalog()
        group_size = catalog.duc_group("up-get-group-size")

        self.assertEqual(group_size.output_width, 1)
        self.assertEqual((group_size.output_goal_min, group_size.output_goal_max), (1, 16000))
        self.assertEqual(group_size.output_contract_id, "up-get-group-size.output-goal")
        self.assertEqual(group_size.output_evidence_ids, ("airef:duc:get-group-size",))

    def test_missing_duc_evidence_blocks_shared_native_catalog(self):
        base = default_native_contract_catalog()
        bad_search = replace(
            base.duc_search("up-find-local"),
            evidence_ids=("airef:duc:missing",),
        )
        with self.assertRaisesRegex(
            ValueError,
            "unresolved citation 'airef:duc:missing'",
        ):
            NativeContractCatalog(
                duc_searches=(
                    bad_search,
                    *(item for item in base.duc_searches if item.command != "up-find-local"),
                ),
            )

    def test_wrong_scope_duc_evidence_blocks_shared_native_catalog(self):
        base = default_native_contract_catalog()
        bad_search = replace(
            base.duc_search("up-find-local"),
            evidence_ids=("airef:goal-storage",),
        )
        with self.assertRaisesRegex(
            ValueError,
            "expected GENERAL_NATIVE_FACT",
        ):
            NativeContractCatalog(
                duc_searches=(
                    bad_search,
                    *(item for item in base.duc_searches if item.command != "up-find-local"),
                ),
            )

    def test_missing_duc_output_evidence_blocks_shared_native_catalog(self):
        base = default_native_contract_catalog()
        with self.assertRaisesRegex(
            ValueError,
            "unresolved citation 'airef:duc:missing-output'",
        ):
            NativeContractCatalog(
                duc_output_evidence_ids=("airef:duc:missing-output",),
            )

    def test_broken_duc_evidence_blocks_shared_native_catalog(self):
        base = default_native_contract_catalog()
        broken = CitationRecord(
            "airef:duc:find-local",
            "https://airef.github.io/commands/commands-details.html#up-find-local",
            "https://airef.github.io/commands/commands-details.html#up-find-local",
            LocatorType.COMMAND,
            "up-find-local",
            semantic_scope=base.citation_catalog.resolve("airef:duc:find-local").semantic_scope,
            excerpt=SourceExcerpt.capture(
                "(up-find-local <typeOp> <UnitId> <typeOp> <Value>)",
                ExcerptKind.FACT,
            ),
            state=CitationState.BROKEN,
        )
        citation_catalog = CitationRecordCatalog(
            (
                broken,
                *(
                    item
                    for item in base.citation_catalog.records
                    if item.citation_id != "airef:duc:find-local"
                ),
            )
        )
        with self.assertRaisesRegex(
            ValueError,
            "citation 'airef:duc:find-local' is not promotable",
        ):
            NativeContractCatalog(
                duc_searches=base.duc_searches,
                citation_catalog=citation_catalog,
            )

    def test_goal_storage_citation_cannot_back_goal_span_contract(self):
        base = default_native_contract_catalog()
        bad_span = replace(
            base.goal_span_contract("extended-4-goal-span"),
            provenance=(
                AIRefProvenance(
                    evidence_kind=EvidenceKind.DOCUMENTED_FACT,
                    confidence=ConfidenceLevel.HIGH,
                    confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
                    citation_id="airef:goal-storage",
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "expected EXTENDED_GOAL_SPAN"):
            NativeContractCatalog(
                witnesses=base.witnesses,
                storage_uses=base.storage_uses,
                pass_constraints=base.pass_constraints,
                goal_storage_contracts=base.goal_storage_contracts,
                goal_span_contracts=(
                    bad_span,
                    *(
                        item
                        for item in base.goal_span_contracts
                        if item.identity != "extended-4-goal-span"
                    ),
                ),
                parameter_ranges=base.parameter_ranges,
            )

    def test_goal_parameter_citation_cannot_back_ordinary_goal_storage_contract(self):
        base = default_native_contract_catalog()
        bad_goal = replace(
            base.goal_storage_contract("ordinary-persistent-goal-storage"),
            provenance=(
                AIRefProvenance(
                    evidence_kind=EvidenceKind.DOCUMENTED_FACT,
                    confidence=ConfidenceLevel.HIGH,
                    confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
                    citation_id="airef:goal-id-parameter-range",
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "expected ORDINARY_PERSISTENT_GOAL_STORAGE"):
            NativeContractCatalog(
                witnesses=base.witnesses,
                storage_uses=base.storage_uses,
                pass_constraints=base.pass_constraints,
                goal_storage_contracts=(bad_goal,),
                goal_span_contracts=base.goal_span_contracts,
                parameter_ranges=base.parameter_ranges,
            )

    def test_goal_storage_citation_cannot_back_goal_id_parameter_contract(self):
        base = default_native_contract_catalog()
        bad_storage = replace(
            base.goal_storage_contract("ordinary-persistent-goal-storage"),
            provenance=(
                AIRefProvenance(
                    evidence_kind=EvidenceKind.DOCUMENTED_FACT,
                    confidence=ConfidenceLevel.HIGH,
                    confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
                    citation_id="airef:goal-id-parameter-range",
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "expected ORDINARY_PERSISTENT_GOAL_STORAGE"):
            NativeContractCatalog(
                witnesses=base.witnesses,
                storage_uses=base.storage_uses,
                pass_constraints=base.pass_constraints,
                goal_storage_contracts=(bad_storage,),
                goal_span_contracts=base.goal_span_contracts,
                parameter_ranges=base.parameter_ranges,
            )

    def test_missing_citation_record_blocks_native_contract_catalog(self):
        base = default_native_contract_catalog()
        witness = replace(
            base.witness("build-completion-witness"),
            provenance=(
                AIRefProvenance(
                    evidence_kind=EvidenceKind.DOCUMENTED_FACT,
                    confidence=ConfidenceLevel.HIGH,
                    confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
                    citation_id="airef:missing",
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "unresolved citation 'airef:missing'"):
            NativeContractCatalog(
                witnesses=(
                    witness,
                    *(
                        item
                        for item in base.witnesses
                        if item.identity != "build-completion-witness"
                    ),
                ),
                storage_uses=base.storage_uses,
                pass_constraints=base.pass_constraints,
            )

    def test_non_promotable_citation_blocks_native_contract_catalog(self):
        base = default_native_contract_catalog()
        broken = CitationRecord(
            "airef:building-type-count",
            "https://airef.github.io/commands/commands-details.html",
            "https://airef.github.io/commands/commands-details.html",
            LocatorType.COMMAND,
            "building-type-count",
            excerpt=SourceExcerpt.capture(
                "(building-type-count <BuildingId> <compareOp> <Value>)",
                ExcerptKind.FACT,
            ),
            state=CitationState.BROKEN,
        )
        citation_catalog = CitationRecordCatalog(
            (
                broken,
                *(
                    item
                    for item in base.citation_catalog.records
                    if item.citation_id != "airef:building-type-count"
                ),
            )
        )
        with self.assertRaisesRegex(
            ValueError,
            "citation 'airef:building-type-count' is not promotable",
        ):
            NativeContractCatalog(
                witnesses=base.witnesses,
                storage_uses=base.storage_uses,
                pass_constraints=base.pass_constraints,
                citation_catalog=citation_catalog,
            )

    def test_default_compile_resolves_every_native_contract_citation(self):
        registry = default_de_registry()
        registry.native_contracts.validate_all_provenance()
        output = compile_source(SOURCE)
        self.assertIn("(build castle)", output)

    def test_missing_native_witness_blocks_primitive_promotion(self):
        base = default_native_contract_catalog()
        catalog = NativeContractCatalog(
            witnesses=tuple(
                witness
                for witness in base.witnesses
                if witness.identity != "build-completion-witness"
            ),
            storage_uses=base.storage_uses,
            pass_constraints=base.pass_constraints,
        )
        registry = build_registry(catalog)

        assessment = registry.assess_support("build")

        self.assertEqual(assessment.state, NativeSupportState.UNSUPPORTED)
        self.assertIn("no native witness", assessment.message)

    def test_native_storage_use_is_checked_against_actual_bound_goal_slot(self):
        base = default_native_contract_catalog()
        wrong_storage = NativeStorageUse(
            identity="wrong-lifecycle-storage",
            storage_class=NativeStorageClass.ENGINE_MANAGED_LIST,
            kind=NativeStorageKind.DUC_LOCAL_LIST,
            request_purpose="lifecycle",
            symbolic=True,
            provenance=fact_provenance(),
        )
        catalog = NativeContractCatalog(
            witnesses=base.witnesses,
            storage_uses=(wrong_storage, base.storage("build-action-claim-storage")),
            pass_constraints=base.pass_constraints,
        )
        default_registry = default_de_registry()
        build = replace(
            default_registry.require("build"),
            native_storage_use_ids=(
                "wrong-lifecycle-storage",
                "build-action-claim-storage",
            ),
        )
        registry = PrimitiveRegistry(
            tuple(
                build if name == "build" else default_registry.require(name)
                for name in default_registry.names()
            ),
            native_registry=load_default_native_schema(),
            semantic_mappings=default_engine_semantic_mapping_registry(),
            native_contracts=catalog,
        )

        with self.assertRaisesRegex(
            CompileError,
            r"NATIVE-CONTRACT-LOWERING: native storage use 'wrong-lifecycle-storage' "
            r"requires DUC_LOCAL_LIST, got GOAL_SLOT",
        ):
            compile_source(SOURCE, registry=registry)

    def test_pass_constraint_requires_native_arbitration_at_lowering(self):
        base = default_de_registry()
        primitive = replace(
            base.require("build"),
            conflict_class=None,
            native_storage_use_ids=("lifecycle-goal-storage",),
        )
        registry = PrimitiveRegistry(
            tuple(
                primitive if name == "build" else base.require(name)
                for name in base.names()
            ),
            native_registry=load_default_native_schema(),
            semantic_mappings=default_engine_semantic_mapping_registry(),
            native_contracts=default_native_contract_catalog(),
        )

        with self.assertRaisesRegex(
            CompileError,
            r"EMITTER-NATIVE-PASS-CONSTRAINT: action 'build' requires a transient arbitration owner",
        ):
            compile_source(SOURCE, registry=registry)

    def test_unsupported_pass_failure_mode_is_not_promoted(self):
        base = default_native_contract_catalog()
        constraint = replace(
            base.pass_constraint("build-pass-singleton"),
            failure_mode=PassFailureMode.REJECTED,
        )
        catalog = NativeContractCatalog(
            witnesses=base.witnesses,
            storage_uses=base.storage_uses,
            pass_constraints=(constraint,),
        )
        registry = build_registry(catalog)

        assessment = registry.assess_support("build")

        self.assertEqual(assessment.state, NativeSupportState.UNSUPPORTED)
        self.assertIn("failure mode", assessment.message)

    def test_next_pass_constraint_is_not_lowered_silently(self):
        base = default_native_contract_catalog()
        constraint = replace(
            base.pass_constraint("build-pass-singleton"),
            requires_next_pass=True,
        )
        catalog = NativeContractCatalog(
            witnesses=base.witnesses,
            storage_uses=base.storage_uses,
            pass_constraints=(constraint,),
        )
        registry = build_registry(catalog)

        assessment = registry.assess_support("build")

        self.assertEqual(assessment.state, NativeSupportState.UNSUPPORTED)
        self.assertIn("next-pass", assessment.message)

    def test_default_build_lowering_records_and_enforces_pass_constraint(self):
        output = compile_source(SOURCE)

        self.assertIn(
            "; NATIVE-PASS-CONSTRAINT build maximum-successes=1",
            output,
        )
        action_start = output.index("; Action issuance: castle | ACTIVE -> ISSUED")
        action_end = output.find("; Pending diagnostics:", action_start)
        action_block = output[action_start:action_end]
        self.assertIn("(goal action-claim-build-pass-singleton 0)", action_block)


if __name__ == "__main__":
    unittest.main()
