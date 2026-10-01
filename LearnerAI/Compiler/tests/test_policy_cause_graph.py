import unittest

from Compiler.diagnostics import DiagnosticSeverity
from Compiler.semantic.policy_cause_graph import (
    PolicyCauseGraph,
    PolicyCauseGraphCausalCycleError,
    PolicyCauseGraphContradictionCanonicalizationError,
    PolicyCauseGraphDuplicateEdgeError,
    PolicyCauseGraphPhaseOrderError,
    PolicyCauseGraphPriorityViolationError,
    PolicyCauseGraphSubjectMismatchError,
    PolicyCauseGraphUnknownNodeError,
    PolicyCauseGraphWitnessMismatchError,
    PolicyCauseRelation,
    PolicyDiagnostic,
    PolicyDiagnosticKey,
    PolicyDiagnosticPhase,
    PolicyDiagnosticRef,
    PolicyDiagnosticSubject,
    PolicyCauseWitness,
    PolicyCauseEdgeContext,
    PolicyCauseGraphErrorCode,
    PolicyCauseGraphIllegalRelationError,
    PolicyCauseGraphInvalidCauseDirectionError,
    PolicyCauseGraphInvalidRelationEndpointError,
    PolicyCauseGraphInvalidRootReferenceError,
    PolicyCauseGraphSuppressionWithoutCauseError,
    PolicySuppressionRef,
    PolicySuppressionReason,
    validate_cause_direction,
    select_root_cause,
    validate_policy_cause_graph,
)


def diag(code, policy='raid-1', recipe='STRICT_RAID', field='attack-retarget', related=None, phase=PolicyDiagnosticPhase.RESOLUTION, priority=None):
    key = PolicyDiagnosticKey(code, policy, recipe, field, related, None)
    subject = PolicyDiagnosticSubject(policy, recipe, field, related, None)
    return PolicyDiagnostic(
        key=key,
        severity=DiagnosticSeverity.ERROR if code not in {'POL-011', 'POL-012', 'POL-006', 'POL-007'} else DiagnosticSeverity.WARNING,
        phase=phase,
        priority=priority if priority is not None else 100,
        subject=subject,
        message=code,
    )


class PolicyCauseGraphTests(unittest.TestCase):
    def test_valid_invalidation_graph(self):
        root = diag('POL-001', field='objective-discipline', related='attack-retarget', priority=50)
        child = diag('POL-006', priority=90, phase=PolicyDiagnosticPhase.APPLICABILITY)
        graph = PolicyCauseGraph.from_nodes((root, child)).with_invalidation(root.key, child.key)
        validate_policy_cause_graph(graph)
        self.assertEqual(len(graph.edges), 1)

    def test_missing_endpoint_is_rejected(self):
        root = diag('POL-001')
        child = diag('POL-006')
        graph = PolicyCauseGraph.from_nodes((root,))
        with self.assertRaises(PolicyCauseGraphUnknownNodeError):
            graph.with_invalidation(root.key, child.key)

    def test_self_edge_is_rejected(self):
        root = diag('POL-001')
        graph = PolicyCauseGraph.from_nodes((root,))
        with self.assertRaisesRegex(ValueError, 'PCG-002'):
            graph.with_invalidation(root.key, root.key)

    def test_duplicate_edge_is_rejected(self):
        root = diag('POL-001')
        child = diag('POL-006', phase=PolicyDiagnosticPhase.APPLICABILITY, priority=90)
        graph = PolicyCauseGraph.from_nodes((root, child)).with_invalidation(root.key, child.key)
        with self.assertRaises(PolicyCauseGraphDuplicateEdgeError):
            graph.with_invalidation(root.key, child.key)

    def test_phase_order_is_rejected(self):
        root = diag('POL-001', phase=PolicyDiagnosticPhase.APPLICABILITY)
        child = diag('POL-006', phase=PolicyDiagnosticPhase.RESOLUTION)
        graph = PolicyCauseGraph.from_nodes((root, child))
        with self.assertRaises(PolicyCauseGraphPhaseOrderError):
            graph.with_invalidation(root.key, child.key)

    def test_subject_mismatch_is_rejected(self):
        root = diag('POL-001', policy='raid-1')
        child = diag('POL-006', policy='deer-push')
        graph = PolicyCauseGraph.from_nodes((root, child))
        with self.assertRaises(PolicyCauseGraphSubjectMismatchError):
            graph.with_invalidation(root.key, child.key)

    def test_supersession_requires_stronger_precedence(self):
        root = diag('POL-002', priority=60)
        child = diag('POL-012', priority=80, phase=PolicyDiagnosticPhase.APPLICABILITY)
        graph = PolicyCauseGraph.from_nodes((root, child)).with_supersession(root.key, child.key)
        validate_policy_cause_graph(graph)

        weaker = diag('POL-012', priority=80)
        stronger = diag('POL-002', priority=60)
        graph = PolicyCauseGraph.from_nodes((weaker, stronger))
        with self.assertRaises(PolicyCauseGraphPriorityViolationError):
            graph.with_supersession(weaker.key, stronger.key)

    def test_contradiction_is_canonical_and_not_duplicate_by_reverse_edge(self):
        left = diag('POL-A', field='objective-discipline', related='attack-retarget', priority=10)
        right = diag('POL-B', field='attack-retarget', related='objective-discipline', priority=20)
        graph = PolicyCauseGraph.from_nodes((left, right)).with_contradiction(left.key, right.key)
        self.assertEqual(graph.edges[0].key.source.key, min(left.key, right.key))
        with self.assertRaises(PolicyCauseGraphContradictionCanonicalizationError):
            graph.add_raw_edge(
                PolicyDiagnosticRef(right.key),
                PolicyDiagnosticRef(left.key),
                PolicyCauseRelation.CONTRADICTS,
                witness=PolicyCauseWitness(policy_identity='raid-1'),
            )

    def test_causal_cycle_is_rejected(self):
        a = diag('POL-A', field='objective-discipline', related='attack-retarget', priority=10)
        b = diag('POL-B', field='attack-retarget', related='objective-discipline', priority=20, phase=PolicyDiagnosticPhase.RESOLUTION)
        graph = PolicyCauseGraph.from_nodes((a, b)).with_invalidation(a.key, b.key)
        with self.assertRaises(PolicyCauseGraphCausalCycleError):
            graph.with_invalidation(b.key, a.key)

    def test_witness_mismatch_is_rejected(self):
        root = diag('POL-001', policy='raid-1', field='objective-discipline', related='attack-retarget')
        child = diag('POL-006', policy='raid-1')
        graph = PolicyCauseGraph.from_nodes((root, child))
        with self.assertRaises(PolicyCauseGraphWitnessMismatchError):
            graph.add_raw_edge(
                PolicyDiagnosticRef(root.key),
                PolicyDiagnosticRef(child.key),
                PolicyCauseRelation.INVALIDATES,
                witness=PolicyCauseWitness(policy_identity='deer-push'),
            )

    def test_root_cause_precedence_prefers_invalidation_over_derivation(self):
        root = diag('POL-001', field='objective-discipline', related='attack-retarget', priority=50)
        mid = diag('POL-006', priority=90, phase=PolicyDiagnosticPhase.APPLICABILITY)
        leaf = diag('POL-007', field='attack-retarget', related='patrol', priority=100, phase=PolicyDiagnosticPhase.APPLICABILITY)
        graph = (
            PolicyCauseGraph.from_nodes((root, mid, leaf))
            .with_invalidation(root.key, mid.key)
            .with_derivation(mid.key, leaf.key)
            .with_invalidation(root.key, leaf.key)
        )
        selected = select_root_cause(graph, leaf.key)
        self.assertEqual(selected, root.key)

    def test_graph_validation_is_deterministic(self):
        root = diag('POL-001', field='objective-discipline', related='attack-retarget', priority=50)
        child = diag('POL-006', priority=90, phase=PolicyDiagnosticPhase.APPLICABILITY)
        graph_a = PolicyCauseGraph.from_nodes((root, child)).with_invalidation(root.key, child.key)
        graph_b = PolicyCauseGraph.from_nodes((root, child)).with_invalidation(root.key, child.key)
        self.assertEqual(graph_a, graph_b)
        validate_policy_cause_graph(graph_a)
        validate_policy_cause_graph(graph_b)

    def test_illegal_relation_is_rejected(self):
        root = diag('POL-001')
        child = diag('POL-006', phase=PolicyDiagnosticPhase.APPLICABILITY, priority=90)
        graph = PolicyCauseGraph.from_nodes((root, child))
        with self.assertRaises(PolicyCauseGraphIllegalRelationError) as raised:
            graph.add_raw_edge(root.key, child.key, 'not-a-relation', witness=PolicyCauseWitness(policy_identity='raid-1'))
        self.assertEqual(raised.exception.code, PolicyCauseGraphErrorCode.ILLEGAL_RELATION)

    def test_invalid_cause_direction_is_rejected(self):
        root = PolicyDiagnosticRef(diag('POL-001').key)
        child = PolicyDiagnosticRef(diag('POL-006').key)
        edge = PolicyCauseEdgeContext(child, root, PolicyCauseRelation.INVALIDATES)
        with self.assertRaises(PolicyCauseGraphInvalidCauseDirectionError):
            validate_cause_direction(edge, expected_source=root, expected_target=child)

    def test_suppression_requires_causal_edge(self):
        root = diag('POL-001', field='objective-discipline', related='attack-retarget', priority=50)
        child = diag('POL-006', priority=90, phase=PolicyDiagnosticPhase.APPLICABILITY)
        graph = PolicyCauseGraph.from_nodes((root, child))
        suppression = PolicySuppressionRef(
            suppressed=PolicyDiagnosticRef(child.key), root_cause=PolicyDiagnosticRef(root.key), via_edge=None
        )
        with self.assertRaises(PolicyCauseGraphSuppressionWithoutCauseError):
            graph.validate_suppression(suppression)

    def test_suppression_root_must_match_canonical_root(self):
        root = diag('POL-001', field='objective-discipline', related='attack-retarget', priority=50)
        mid = diag('POL-006', priority=90, phase=PolicyDiagnosticPhase.APPLICABILITY)
        leaf = diag('POL-007', field='attack-retarget', related='patrol', priority=100, phase=PolicyDiagnosticPhase.APPLICABILITY)
        graph = (
            PolicyCauseGraph.from_nodes((root, mid, leaf))
            .with_invalidation(root.key, mid.key)
            .with_derivation(mid.key, leaf.key)
        )
        via = next(edge.key for edge in graph.edges if edge.key.target == PolicyDiagnosticRef(leaf.key))
        suppression = PolicySuppressionRef(
            suppressed=PolicyDiagnosticRef(leaf.key), root_cause=PolicyDiagnosticRef(mid.key), via_edge=via
        )
        with self.assertRaises(PolicyCauseGraphInvalidRootReferenceError):
            graph.validate_suppression(suppression)

    def test_invalid_relation_endpoint_is_rejected_for_supersession(self):
        root = diag('POL-002', field='stance', priority=10)
        child = diag('POL-012', field='attack-retarget', related='stance', priority=80, phase=PolicyDiagnosticPhase.APPLICABILITY)
        graph = PolicyCauseGraph.from_nodes((root, child))
        with self.assertRaises(PolicyCauseGraphInvalidRelationEndpointError):
            graph.with_supersession(root.key, child.key)


if __name__ == '__main__':
    unittest.main()
