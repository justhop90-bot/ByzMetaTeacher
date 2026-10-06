import tempfile
import unittest
from pathlib import Path

from Compiler import semantic


class SemanticManifestTests(unittest.TestCase):
    def test_semantic_manifest_builder_is_public(self):
        builder = getattr(semantic, "build_semantic_manifest", None)
        self.assertIsNotNone(
            builder,
            "semantic manifest builder must be exposed through Compiler.semantic",
        )

    def test_manifest_records_rule_annotation_state_operands_and_element_budget(self):
        builder = semantic.build_semantic_manifest
        source = """; Native control rule: economy-controller-select-counter-pressure
(defrule
 (and (current-age >= feudal-age) (goal opening-plan 3))
 (not (goal opening-plan 6))
=>
 (set-goal economy-posture 2)
)
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.per"
            path.write_text(source, encoding="utf-8")
            manifest = builder(path)

        rule = manifest.rules[0]
        self.assertEqual(rule.identity, "economy-controller-select-counter-pressure")
        self.assertEqual(rule.annotation_kind, "NATIVE_CONTROL")
        self.assertIn("goal:opening-plan", rule.goal_reads)
        self.assertIn("goal:economy-posture", rule.goal_writes)
        self.assertEqual(rule.pass_behavior, "RECURRENT")
        self.assertLessEqual(rule.element_count, 32)

    def test_checked_in_byzantine_artifact_has_semantic_shadow_for_arena_pressure_rule(self):
        builder = semantic.build_semantic_manifest
        root = Path(__file__).resolve().parents[3]
        artifact = root / "Byzantine.per"
        manifest = builder(artifact)

        self.assertGreater(manifest.rule_count, 1000)
        rule = next(
            item
            for item in manifest.rules
            if item.identity == "economy-controller-select-counter-pressure"
        )
        self.assertIn("(not (map-type arena))", rule.facts)
        self.assertIn("goal:economy-posture", rule.goal_writes)
        self.assertEqual(rule.annotation_kind, "NATIVE_CONTROL")

    def test_manifest_json_is_deterministic(self):
        manifest = semantic.build_semantic_manifest(Path("Byzantine.per"))
        self.assertEqual(manifest.to_json(), manifest.to_json())


    def test_manifest_exposes_shared_goal_writer_ownership(self):
        manifest = semantic.build_semantic_manifest(Path("Byzantine.per"))
        writers = dict(manifest.writers_by_state)
        self.assertIn("goal:opening-plan", writers)
        self.assertGreaterEqual(len(writers["goal:opening-plan"]), 2)



if __name__ == "__main__":
    unittest.main()
