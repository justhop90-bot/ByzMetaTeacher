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
