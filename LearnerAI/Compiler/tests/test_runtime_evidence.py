"""Focused tests for deterministic runtime-witness assessment."""
import unittest

from Compiler.semantic.runtime_evidence import (
    RuntimeClaimStatus,
    RuntimeEvidenceStatus,
    assess_runtime_witness,
)


class RuntimeEvidenceTests(unittest.TestCase):
    def _scenario(self, checkpoints=()):
        return {
            "record_type": "SCENARIO",
            "scenario_id": "arena-mild-pressure-castle",
            "status": "OPEN",
            "artifact": {
                "path": "Byzantine.per",
                "sha256": "a" * 64,
                "sha256_required_at_capture": True,
            },
            "claims": [
                {
                    "id": "pressure-arbitration",
                    "lifecycle_edge": "ARBITRATION -> EXECUTION",
                    "evidence_class": "COMPILER POLICY",
                    "rule_identities": ["economy-controller-select-counter-pressure"],
                    "expected": {"counter_pressure_selected": False},
                },
                {
                    "id": "castle-completion",
                    "lifecycle_edge": "ACTION -> WORLD-STATE WITNESS",
                    "evidence_class": "OPEN / UNKNOWN",
                    "rule_identities": ["castle-age-transition"],
                    "expected": {"world_state": "current-age >= castle-age"},
                },
            ],
            "checkpoint": list(checkpoints),
        }

    def test_open_scenario_has_no_first_broken_edge(self):
        result = assess_runtime_witness(self._scenario())
        self.assertEqual(result.status, RuntimeEvidenceStatus.OPEN)
        self.assertIsNone(result.first_broken_edge)
        self.assertEqual(result.open_claims, ("pressure-arbitration", "castle-completion"))

    def test_first_failed_claim_wins_over_later_failures(self):
        result = assess_runtime_witness(
            self._scenario(
                (
                    {
                        "claim_id": "pressure-arbitration",
                        "assessment": "CONFIRMED",
                        "game_time_seconds": 480,
                        "lifecycle_edge": "ARBITRATION -> EXECUTION",
                        "evidence_class": "COMPILER POLICY",
                        "observed_facts": ["counter-pressure action not issued"],
                        "world_witness": [],
                        "rule_identities": ["economy-controller-select-counter-pressure"],
                    },
                    {
                        "claim_id": "castle-completion",
                        "assessment": "FAILED",
                        "game_time_seconds": 900,
                        "lifecycle_edge": "ACTION -> WORLD-STATE WITNESS",
                        "evidence_class": "OPEN / UNKNOWN",
                        "observed_facts": ["Castle Age not reached"],
                        "world_witness": [],
                        "rule_identities": ["castle-age-transition"],
                    },
                )
            )
        )
        self.assertEqual(result.status, RuntimeEvidenceStatus.FAILED)
        self.assertEqual(result.first_broken_edge.claim_id, "castle-completion")
        self.assertEqual(result.first_broken_edge.lifecycle_edge, "ACTION -> WORLD-STATE WITNESS")
        self.assertEqual(result.first_broken_edge.rule_identities, ("castle-age-transition",))

    def test_all_claims_confirmed_promotes_runtime_record(self):
        result = assess_runtime_witness(
            self._scenario(
                (
                    {
                        "claim_id": "pressure-arbitration",
                        "assessment": "CONFIRMED",
                        "game_time_seconds": 480,
                        "lifecycle_edge": "ARBITRATION -> EXECUTION",
                        "evidence_class": "COMPILER POLICY",
                        "observed_facts": ["counter-pressure action not issued"],
                        "world_witness": [],
                        "rule_identities": ["economy-controller-select-counter-pressure"],
                    },
                    {
                        "claim_id": "castle-completion",
                        "assessment": "CONFIRMED",
                        "game_time_seconds": 900,
                        "lifecycle_edge": "ACTION -> WORLD-STATE WITNESS",
                        "evidence_class": "OPEN / UNKNOWN",
                        "observed_facts": ["Castle Age reached"],
                        "world_witness": ["current-age >= castle-age"],
                        "rule_identities": ["castle-age-transition"],
                    },
                )
            )
        )
        self.assertEqual(result.status, RuntimeEvidenceStatus.CONFIRMED)
        self.assertEqual(result.confirmed_claims, ("pressure-arbitration", "castle-completion"))
        self.assertEqual(result.artifact_sha256, "a" * 64)

    def test_checked_in_arena_scenario_remains_open_until_live_checkpoint(self):
        from pathlib import Path
        import json

        root = Path(__file__).resolve().parents[3]
        record = json.loads(
            (root / "docs" / "runtime" / "scenarios" / "arena-mild-pressure-castle.json")
            .read_text(encoding="utf-8")
        )
        result = assess_runtime_witness(record)
        self.assertEqual(result.status, RuntimeEvidenceStatus.OPEN)
        self.assertIsNone(result.first_broken_edge)



    def test_claim_status_enum_is_exported(self):
        self.assertEqual(RuntimeClaimStatus.CONFIRMED.value, "CONFIRMED")


if __name__ == "__main__":
    unittest.main()
