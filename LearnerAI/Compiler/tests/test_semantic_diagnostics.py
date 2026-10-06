"""Focused tests for provenance and semantic performance diagnostics."""
import tempfile
import unittest
from pathlib import Path

from Compiler import semantic
from Compiler.semantic.community_engine import (
    EvidenceLineage,
    PerformanceCostClass,
    classify_evidence_source,
    default_community_engine_registry,
    performance_cost_for_head,
    practice_evidence_convergence,
)


class SemanticDiagnosticsTests(unittest.TestCase):
    def test_source_lineage_classification_is_explicit_and_conservative(self):
        self.assertEqual(classify_evidence_source("https://airef.github.io/"), EvidenceLineage.AIREF)
        self.assertEqual(
            classify_evidence_source("https://userpatch.aiscripters.net/reference.html"),
            EvidenceLineage.USERPATCH,
        )
        self.assertEqual(
            classify_evidence_source("https://github.com/lewisc64/aoe2ai"),
            EvidenceLineage.COMMUNITY_TOOLING,
        )
        self.assertEqual(
            classify_evidence_source("https://forums.ageofempires.com/t/example"),
            EvidenceLineage.COMMUNITY_FORUM,
        )
        self.assertEqual(
            classify_evidence_source("https://www.ageofempires.com/news/example"),
            EvidenceLineage.OFFICIAL,
        )
        self.assertEqual(
            classify_evidence_source("repo://AiByz/example.md"),
            EvidenceLineage.REPO_ARCHAEOLOGY,
        )
        self.assertEqual(classify_evidence_source("opaque://unknown"), EvidenceLineage.UNKNOWN)

    def test_performance_cost_classes_keep_expensive_heads_advisory(self):
        self.assertEqual(performance_cost_for_head("up-get-distance"), PerformanceCostClass.HIGH)
        self.assertEqual(performance_cost_for_head("up-find-local"), PerformanceCostClass.MODERATE)
        self.assertEqual(performance_cost_for_head("up-find-remote"), PerformanceCostClass.MODERATE)
        self.assertEqual(performance_cost_for_head("move"), PerformanceCostClass.MODERATE)
        self.assertEqual(performance_cost_for_head("true"), PerformanceCostClass.LOW)

    def test_registry_reports_source_family_convergence_without_calling_it_engine_fact(self):
        registry = default_community_engine_registry()
        convergence = practice_evidence_convergence(registry.practice("state.goal.persistent"))
        self.assertGreaterEqual(convergence.source_count, 1)
        self.assertEqual(convergence.independent_source_family_count, len(convergence.source_families))
        self.assertIn(convergence.status, {"SINGLE_FAMILY", "MULTI_FAMILY", "UNKNOWN_LINEAGE"})

    def test_manifest_exposes_operation_heads_and_high_cost_recurrent_rules(self):
        source = """; Native control rule: cost-fixture
(defrule
 (true)
 (timer-triggered 1)
=>
 (up-get-distance 1 2)
 (move 1 2)
)
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.per"
            path.write_text(source, encoding="utf-8")
            manifest = semantic.build_semantic_manifest(path)

        rule = manifest.rules[0]
        self.assertIn("up-get-distance", rule.operation_heads)
        self.assertIn("move", rule.operation_heads)
        self.assertEqual(rule.performance_cost, "HIGH")
        self.assertEqual(manifest.high_cost_recurrent_rules, (1,))
        self.assertIn("up-get-distance", dict(manifest.operation_counts))


if __name__ == "__main__":
    unittest.main()
