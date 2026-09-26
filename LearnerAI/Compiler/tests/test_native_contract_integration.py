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
    ConfidenceBasis,
    ConfidenceLevel,
    EvidenceKind,
    PassFailureMode,
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
