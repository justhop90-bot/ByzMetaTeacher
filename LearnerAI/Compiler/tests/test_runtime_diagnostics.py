from __future__ import annotations

import unittest

from Compiler.diagnostics import DiagnosticSeverity
from Compiler.semantic.runtime_diagnostics import diagnose_runtime_claim
from Compiler.semantic.semantic_manifest import SemanticManifest, SemanticRuleRecord
from Compiler.semantic.strategy_dependency import (
    FeatureEdge,
    FeatureEdgeStatus,
    FeatureNode,
    FeatureNodeStatus,
    FeatureStage,
    FeatureTraceBuilder,
)


def _record(order: int, identity: str) -> SemanticRuleRecord:
    return SemanticRuleRecord(
        rule_order=order, identity=identity, annotation_kind="NATIVE_CONTROL",
        annotation_text=None, source_path="fixture.per", line=order, column=1,
        pass_behavior="RECURRENT", facts=("true",), actions=(),
        fact_heads=("true",), action_heads=(), goal_reads=(), goal_writes=(),
        strategic_number_reads=(), strategic_number_writes=(), timer_reads=(),
        timer_writes=(), operation_heads=(), performance_cost="LOW", element_count=1,
    )


def _manifest(*records: SemanticRuleRecord) -> SemanticManifest:
    return SemanticManifest(
        schema_version=1, source_path="fixture.per", artifact_sha256="a" * 64,
        rule_count=len(records), annotated_rule_count=len(records), max_element_count=1,
        over_32_element_rules=(), annotation_counts=(("NATIVE_CONTROL", len(records)),),
        writers_by_state=(), readers_by_state=(), operation_counts=(),
        high_cost_recurrent_rules=(), rules=records,
    )


class RuntimeDiagnosticTests(unittest.TestCase):
    def test_rejected_runtime_claim_maps_to_first_broken_edge(self):
        builder = FeatureTraceBuilder("castle-age-transition")
        builder.add_node(FeatureNode(
            feature_id="castle-age-transition",
            stage=FeatureStage.NATIVE_LOWERING,
            identity="castle-age-transition",
            status=FeatureNodeStatus.PASS,
            rule_orders=(41,),
        ))
        builder.add_node(FeatureNode(
            feature_id="castle-age-transition",
            stage=FeatureStage.EMISSION,
            identity="castle-age-transition",
            status=FeatureNodeStatus.INVALID,
            rule_orders=(41,),
        ))
        builder.add_edge(FeatureEdge(
            feature_id="castle-age-transition",
            source=FeatureStage.NATIVE_LOWERING, target=FeatureStage.EMISSION,
            contract="native-emission", expected_identity="castle-age-transition",
            observed_identity=None, status=FeatureEdgeStatus.BROKEN,
            diagnostic_code="BYZ-TRACE-CASTLE-001", message="Castle action missing",
        ))
        trace = builder.build(root_stage=FeatureStage.NATIVE_LOWERING)
        claim = {"id":"castle-action","rule_identities":["castle-age-transition"]}
        result = diagnose_runtime_claim("arena-mild-pressure-castle", claim, _manifest(_record(41, "castle-age-transition")), (trace,), rejected=True)
        self.assertEqual(result.status, "COMPILER_EDGE_BROKEN")
        self.assertEqual(result.feature_id, "castle-age-transition")
        self.assertEqual(result.diagnostic_code, "BYZ-TRACE-CASTLE-001")
        self.assertEqual(result.severity, DiagnosticSeverity.ERROR.value)

    def test_runtime_rejection_without_broken_feature_trace_stays_open(self):
        builder = FeatureTraceBuilder("resource-camp-gold")
        builder.add_node(FeatureNode(
            feature_id="resource-camp-gold",
            stage=FeatureStage.RUNTIME,
            identity="resource-camp-gold",
            status=FeatureNodeStatus.PASS,
            rule_orders=(77,),
        ))
        trace = builder.build(root_stage=FeatureStage.RUNTIME)
        claim = {"id":"camp-visible","rule_identities":["resource-camp-gold"]}
        result = diagnose_runtime_claim("resource-camp-placement", claim, _manifest(_record(77, "resource-camp-gold")), (trace,), rejected=True)
        self.assertEqual(result.status, "RUNTIME_EDGE_OPEN")
        self.assertIsNone(result.diagnostic_code)

    def test_missing_rule_identity_stays_unknown(self):
        claim = {"id":"unknown","rule_identities":["missing-rule"]}
        result = diagnose_runtime_claim("fixture", claim, _manifest(_record(2, "known-rule")), (), rejected=True)
        self.assertEqual(result.status, "UNKNOWN")
        self.assertIsNone(result.feature_id)


if __name__ == "__main__":
    unittest.main()
