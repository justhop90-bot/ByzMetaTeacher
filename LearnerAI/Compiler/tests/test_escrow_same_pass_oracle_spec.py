from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).parents[2]
CANDIDATE = ROOT.parent / "docs" / "reference" / "oracles" / "candidates" / "escrow-same-pass-research.native.json"
SCHEMA = ROOT.parent / "docs" / "reference" / "oracles" / "escrow-same-pass-research.schema.json"
CHECKLIST = ROOT.parent / "docs" / "plans" / "2026-09-28-native-escrow-same-pass-visibility-checklist.md"


EXPECTED_VARIANTS = (
    "NORMAL_BASELINE",
    "ESCROW_BLOCKED_NO_RELEASE",
    "ESCROW_SAME_PASS_POSITIVE",
    "ESCROW_SAME_PASS_REVERSED",
    "ESCROW_LATER_PASS_CONTROL",
)

EXPECTED_TRANSITIONS = (
    "1->1",
    "1->2",
    "2->2",
    "2->3",
    "3->3",
)

EXPECTED_FAILURE_CLASSES = {
    "NATIVE_ENGINE_ERROR",
    "CONTROL_CONTAMINATION",
    "INVALID_PRECONDITION",
    "NONDETERMINISTIC",
    "STATUS_LIFECYCLE_FAILURE",
    "RESOURCE_CONSUMPTION_FAILURE",
    "ORDERING_FAILURE",
    "SAME_PASS_VISIBILITY_FAILURE",
    "BASELINE_FAILURE",
    "BLOCKED_CONTROL_LEAK",
    "REVERSED_ORDER_ACCEPTED",
    "LATER_PASS_RESEARCH_FAILURE",
    "TIMEOUT",
}

REQUIRED_TRACE_FIELDS = {
    "run_id",
    "fixture_variant",
    "scenario_id",
    "de_build",
    "script_sha256",
    "scenario_sha256",
    "pass_id",
    "tick",
    "rule_index",
    "rule_name",
    "action_index",
    "food_amount",
    "wood_amount",
    "gold_amount",
    "stone_amount",
    "escrow_food",
    "escrow_wood",
    "escrow_gold",
    "escrow_stone",
    "normal_gold_visible",
    "escrow_included_gold_visible",
    "can_research_ri_loom",
    "can_research_with_escrow_ri_loom",
    "research_status_ri_loom",
    "research_pending_ri_loom",
    "research_completed_ri_loom",
    "escrow_test_state",
    "release_escrow_gold_issued",
    "research_ri_loom_issued",
    "gold_delta_since_previous_row",
    "escrow_gold_delta_since_previous_row",
    "world_resource_transaction_observed",
    "world_research_transaction_observed",
}


class EscrowSamePassOracleSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))["fixture"]
        cls.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def test_repository_artifacts_exist(self):
        self.assertTrue(CANDIDATE.is_file())
        self.assertTrue(SCHEMA.is_file())
        self.assertTrue(CHECKLIST.is_file())

    def test_candidate_identity_and_scope_are_unverified(self):
        self.assertEqual(self.candidate["id"], "ESCROW-ORACLE-RESEARCH-SAME-PASS")
        self.assertEqual(self.candidate["kind"], "NATIVE_OBSERVATION")
        self.assertEqual(self.candidate["engine_scope"]["game"], "aoe2de")
        self.assertEqual(self.candidate["engine_scope"]["run_status"], "UNVERIFIED")
        self.assertEqual(self.candidate["promotion"]["status"], "OPEN")
        self.assertIn("2026-09-28-native-escrow-same-pass-visibility-checklist.md",
                      self.candidate["experiment_reference"])

    def test_five_variants_are_unique_and_complete(self):
        variants = self.candidate["variants"]
        self.assertEqual(tuple(v["id"] for v in variants), EXPECTED_VARIANTS)
        self.assertEqual(len({v["id"] for v in variants}), 5)
        self.assertTrue(all(v["expected_terminal_result"] == "PASS" for v in variants))
        self.assertTrue(all(v["runtime_runs_required"] == 10 for v in variants))

    def test_action_order_is_exact_for_disputed_variants(self):
        by_id = {v["id"]: v for v in self.candidate["variants"]}
        self.assertEqual(
            by_id["ESCROW_SAME_PASS_POSITIVE"]["action_order"],
            ["release-escrow gold", "research ri-loom"],
        )
        self.assertEqual(
            by_id["ESCROW_SAME_PASS_REVERSED"]["action_order"],
            [
                "research ri-loom",
                "release-escrow gold",
                "later-pass rescue: research ri-loom",
            ],
        )
        self.assertEqual(
            by_id["ESCROW_LATER_PASS_CONTROL"]["action_order"],
            [
                "pass N: release-escrow gold",
                "pass N+1: research ri-loom",
            ],
        )

    def test_status_model_is_exact(self):
        status = self.candidate["status_model"]
        self.assertEqual(
            tuple(status["allowed_transitions"]),
            EXPECTED_TRANSITIONS,
        )
        self.assertEqual(
            (status["unavailable"], status["available"],
             status["pending"], status["complete"]),
            (0, 1, 2, 3),
        )
        self.assertIn("1->3", status["forbidden_transitions"])
        self.assertIn("2->1", status["forbidden_transitions"])
        self.assertIn("3->2", status["forbidden_transitions"])

    def test_trace_schema_contains_every_required_observation(self):
        self.assertTrue(REQUIRED_TRACE_FIELDS.issubset(
            set(self.candidate["trace_fields"])
        ))

    def test_promotion_gate_has_exact_variants_and_run_count(self):
        promotion = self.candidate["promotion"]
        self.assertEqual(tuple(promotion["required_variant_ids"]), EXPECTED_VARIANTS)
        self.assertEqual(promotion["required_runs_per_variant"], 10)
        self.assertEqual(promotion["status"], "OPEN")
        self.assertEqual(
            tuple(self.candidate["terminal_precedence"][-1:]),
            ("PASS",),
        )

    def test_variant_failure_classes_are_present(self):
        failure_classes = set(self.candidate["failure_classes"])
        self.assertIn("SAME_PASS_VISIBILITY_FAILURE", failure_classes)
        self.assertIn("REVERSED_ORDER_ACCEPTED", failure_classes)
        self.assertIn("LATER_PASS_RESEARCH_FAILURE", failure_classes)
        self.assertIn("INVALID_PRECONDITION", self.candidate["terminal_precedence"])

    def test_schema_declares_all_required_top_level_contracts(self):
        fixture_schema = self.schema["$defs"]["fixture"]
        self.assertEqual(
            tuple(fixture_schema["required"]),
            (
                "id",
                "kind",
                "command_under_test",
                "experiment_reference",
                "engine_scope",
                "status_model",
                "trace_fields",
                "variants",
                "promotion",
                "terminal_precedence",
                "failure_classes",
            ),
        )
        self.assertEqual(
            self.schema["$defs"]["statusModel"]["properties"]["allowed_transitions"]["const"],
            list(EXPECTED_TRANSITIONS),
        )
        self.assertEqual(
            self.schema["$defs"]["promotion"]["properties"]["status"]["const"],
            "OPEN",
        )

    def test_all_failure_classifications_are_represented(self):
        terminal_enum = set(self.schema["$defs"]["terminalResult"]["enum"])
        self.assertTrue(EXPECTED_FAILURE_CLASSES.issubset(terminal_enum))

    def test_checklist_keeps_runtime_explicitly_user_owned(self):
        checklist = CHECKLIST.read_text(encoding="utf-8")
        self.assertIn("User-owned DE runtime gate", checklist)
        self.assertIn("No compiler test claims actual DE same-pass timing.", checklist)
        self.assertIn("NATIVE_ESCROW_SAME_PASS_VISIBILITY = OPEN", checklist)


if __name__ == "__main__":
    unittest.main()
