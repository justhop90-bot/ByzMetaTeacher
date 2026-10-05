from __future__ import annotations

import unittest

from Compiler.diagnostics import DiagnosticSeverity
from Compiler.semantic.strategy_dependency import (
    FeatureEdge,
    FeatureEdgeStatus,
    FeatureNode,
    FeatureNodeStatus,
    FeatureStage,
    FeatureTraceBuilder,
    first_broken_edge,
)


def _node(
    feature_id: str,
    stage: FeatureStage,
    status: FeatureNodeStatus = FeatureNodeStatus.PASS,
    *,
    identity: str | None = None,
) -> FeatureNode:
    return FeatureNode(
        feature_id=feature_id,
        stage=stage,
        identity=identity or feature_id,
        status=status,
    )


def _edge(
    feature_id: str,
    source: FeatureStage,
    target: FeatureStage,
    status: FeatureEdgeStatus,
    *,
    contract: str,
    expected_identity: str,
    observed_identity: str | None = None,
    diagnostic_code: str | None = None,
    message: str | None = None,
) -> FeatureEdge:
    return FeatureEdge(
        feature_id=feature_id,
        source=source,
        target=target,
        contract=contract,
        expected_identity=expected_identity,
        observed_identity=observed_identity,
        status=status,
        diagnostic_code=diagnostic_code,
        message=message,
    )


class FeatureTraceBuilderTests(unittest.TestCase):
    def test_healthy_trace_has_no_broken_edge(self):
        builder = FeatureTraceBuilder("research-pikeman")
        builder.add_node(_node("research-pikeman", FeatureStage.STRATEGY_IR))
        builder.add_node(_node("research-pikeman", FeatureStage.SEMANTIC_IR))
        builder.add_edge(_edge(
            "research-pikeman",
            FeatureStage.STRATEGY_IR,
            FeatureStage.SEMANTIC_IR,
            FeatureEdgeStatus.SATISFIED,
            contract="strategy-ir-semantic-lowering",
            expected_identity="research-pikeman",
            observed_identity="research-pikeman",
        ))

        trace = builder.build(root_stage=FeatureStage.STRATEGY_IR)

        self.assertEqual(trace.status, FeatureNodeStatus.PASS)
        self.assertIsNone(trace.first_broken_edge)
        self.assertEqual(
            tuple(node.stage for node in trace.ordered_nodes),
            (FeatureStage.STRATEGY_IR, FeatureStage.SEMANTIC_IR),
        )

    def test_first_broken_edge_uses_causal_stage_order_not_insertion_order(self):
        builder = FeatureTraceBuilder("research-pikeman")
        builder.add_node(_node("research-pikeman", FeatureStage.STRATEGY_IR))
        builder.add_node(_node("research-pikeman", FeatureStage.SEMANTIC_IR))
        builder.add_node(_node("research-pikeman", FeatureStage.EMISSION))
        builder.add_edge(_edge(
            "research-pikeman",
            FeatureStage.EMISSION,
            FeatureStage.ARTIFACT_ANALYSIS,
            FeatureEdgeStatus.BROKEN,
            contract="artifact-coverage",
            expected_identity="research-pikeman",
            diagnostic_code="BYZ-TRACE-ARTIFACT-001",
            message="feature is absent from artifact",
        ))
        builder.add_edge(_edge(
            "research-pikeman",
            FeatureStage.STRATEGY_IR,
            FeatureStage.SEMANTIC_IR,
            FeatureEdgeStatus.BROKEN,
            contract="strategy-ir-semantic-lowering",
            expected_identity="research-pikeman",
            diagnostic_code="BYZ-TRACE-SEMANTIC-001",
            message="semantic IR evidence is absent",
        ))

        trace = builder.build(root_stage=FeatureStage.STRATEGY_IR)

        broken = first_broken_edge(trace)

        self.assertIsNotNone(broken)
        self.assertEqual(broken.diagnostic_code, "BYZ-TRACE-SEMANTIC-001")
        self.assertEqual(broken.source, FeatureStage.STRATEGY_IR)
        self.assertEqual(broken.target, FeatureStage.SEMANTIC_IR)

    def test_missing_middle_stage_becomes_first_broken_edge(self):
        builder = FeatureTraceBuilder("research-capped-ram")
        builder.add_node(_node("research-capped-ram", FeatureStage.STRATEGY_IR))
        builder.add_edge(_edge(
            "research-capped-ram",
            FeatureStage.STRATEGY_IR,
            FeatureStage.SEMANTIC_IR,
            FeatureEdgeStatus.BROKEN,
            contract="strategy-ir-semantic-lowering",
            expected_identity="research-capped-ram",
            diagnostic_code="BYZ-TRACE-MISSING-001",
            message="semantic IR feature is missing",
        ))

        trace = builder.build(root_stage=FeatureStage.STRATEGY_IR)

        broken = trace.first_broken_edge

        self.assertIsNotNone(broken)
        self.assertEqual(broken.source, FeatureStage.STRATEGY_IR)
        self.assertEqual(broken.target, FeatureStage.SEMANTIC_IR)

    def test_downstream_blocked_edge_is_not_selected_as_new_root_failure(self):
        builder = FeatureTraceBuilder("research-capped-ram")
        builder.add_node(_node("research-capped-ram", FeatureStage.STRATEGY_IR))
        builder.add_node(_node(
            "research-capped-ram",
            FeatureStage.SEMANTIC_IR,
            FeatureNodeStatus.MISSING,
        ))
        builder.add_edge(_edge(
            "research-capped-ram",
            FeatureStage.STRATEGY_IR,
            FeatureStage.SEMANTIC_IR,
            FeatureEdgeStatus.BROKEN,
            contract="strategy-ir-semantic-lowering",
            expected_identity="research-capped-ram",
            diagnostic_code="BYZ-TRACE-MISSING-001",
            message="semantic IR feature is missing",
        ))
        builder.add_edge(_edge(
            "research-capped-ram",
            FeatureStage.SEMANTIC_IR,
            FeatureStage.CAPABILITY_GRAPH,
            FeatureEdgeStatus.BLOCKED,
            contract="semantic-capability-projection",
            expected_identity="research-capped-ram",
            diagnostic_code="BYZ-TRACE-BLOCKED-001",
            message="source stage failed",
        ))

        trace = builder.build(root_stage=FeatureStage.STRATEGY_IR)

        broken = trace.first_broken_edge

        self.assertIsNotNone(broken)
        self.assertEqual(broken.diagnostic_code, "BYZ-TRACE-MISSING-001")

    def test_runtime_promotion_failure_is_not_misreported_as_emission_failure(self):
        builder = FeatureTraceBuilder("research-pikeman")
        builder.add_node(_node("research-pikeman", FeatureStage.EMISSION))
        builder.add_node(_node(
            "research-pikeman",
            FeatureStage.RUNTIME_PROMOTION,
            FeatureNodeStatus.INVALID,
        ))
        builder.add_edge(_edge(
            "research-pikeman",
            FeatureStage.EMISSION,
            FeatureStage.RUNTIME_ASSEMBLY,
            FeatureEdgeStatus.SATISFIED,
            contract="emission-runtime-assembly",
            expected_identity="research-pikeman",
            observed_identity="research-pikeman",
        ))
        builder.add_edge(_edge(
            "research-pikeman",
            FeatureStage.RUNTIME_ASSEMBLY,
            FeatureStage.RUNTIME_PROMOTION,
            FeatureEdgeStatus.BROKEN,
            contract="runtime-promotion",
            expected_identity="research-pikeman",
            diagnostic_code="BYZ-TRACE-PROMOTION-001",
            message="promoted runtime artifact diverges",
        ))

        trace = builder.build(root_stage=FeatureStage.EMISSION)

        broken = trace.first_broken_edge

        self.assertIsNotNone(broken)
        self.assertEqual(broken.source, FeatureStage.RUNTIME_ASSEMBLY)
        self.assertEqual(broken.target, FeatureStage.RUNTIME_PROMOTION)
        self.assertNotEqual(broken.source, FeatureStage.EMISSION)

    def test_unknown_edge_is_not_treated_as_proven_broken(self):
        builder = FeatureTraceBuilder("resource-camp-gold")
        builder.add_node(_node("resource-camp-gold", FeatureStage.CAPABILITY_GRAPH))
        builder.add_edge(_edge(
            "resource-camp-gold",
            FeatureStage.CAPABILITY_GRAPH,
            FeatureStage.OPERATIONAL_PLAN,
            FeatureEdgeStatus.UNKNOWN,
            contract="capability-operationalization",
            expected_identity="resource-camp-gold",
            diagnostic_code="BYZ-TRACE-UNKNOWN-001",
            message="operational evidence is unavailable",
        ))

        trace = builder.build(root_stage=FeatureStage.CAPABILITY_GRAPH)

        self.assertIsNone(first_broken_edge(trace))
        self.assertEqual(trace.status, FeatureNodeStatus.UNKNOWN)

    def test_same_feature_trace_is_deterministic(self):
        builder_a = FeatureTraceBuilder("research-pikeman")
        builder_b = FeatureTraceBuilder("research-pikeman")
        for builder in (builder_a, builder_b):
            builder.add_node(_node("research-pikeman", FeatureStage.EMISSION))
            builder.add_node(_node("research-pikeman", FeatureStage.NATIVE_LOWERING))
            builder.add_edge(_edge(
                "research-pikeman",
                FeatureStage.NATIVE_LOWERING,
                FeatureStage.EMISSION,
                FeatureEdgeStatus.SATISFIED,
                contract="native-emission",
                expected_identity="research-pikeman",
                observed_identity="research-pikeman",
            ))

        self.assertEqual(
            builder_a.build(root_stage=FeatureStage.NATIVE_LOWERING),
            builder_b.build(root_stage=FeatureStage.NATIVE_LOWERING),
        )

    def test_conflicting_duplicate_node_is_rejected(self):
        builder = FeatureTraceBuilder("research-pikeman")
        builder.add_node(_node(
            "research-pikeman",
            FeatureStage.EMISSION,
            FeatureNodeStatus.PASS,
        ))

        with self.assertRaises(ValueError):
            builder.add_node(_node(
                "research-pikeman",
                FeatureStage.EMISSION,
                FeatureNodeStatus.INVALID,
            ))

    def test_diagnostic_severity_for_first_broken_edge_is_error(self):
        builder = FeatureTraceBuilder("research-pikeman")
        builder.add_node(_node("research-pikeman", FeatureStage.EMISSION))
        builder.add_edge(_edge(
            "research-pikeman",
            FeatureStage.EMISSION,
            FeatureStage.ARTIFACT_ANALYSIS,
            FeatureEdgeStatus.BROKEN,
            contract="artifact-coverage",
            expected_identity="research-pikeman",
            diagnostic_code="BYZ-TRACE-ARTIFACT-001",
            message="artifact feature missing",
        ))

        diagnostic = builder.build(root_stage=FeatureStage.EMISSION).diagnostic()

        self.assertIsNotNone(diagnostic)
        self.assertEqual(diagnostic.severity, DiagnosticSeverity.ERROR)
        self.assertEqual(diagnostic.feature_id, "research-pikeman")
        self.assertEqual(diagnostic.stage, FeatureStage.ARTIFACT_ANALYSIS)


if __name__ == "__main__":
    unittest.main()
