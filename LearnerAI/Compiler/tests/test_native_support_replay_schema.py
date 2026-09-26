from __future__ import annotations

import copy
import unittest

from native_support_replay_schema import (
    FIXTURE_NAMES,
    SnapshotSchemaError,
    validate_snapshot,
)


def valid_snapshot():
    diagnostic = {
        "id": "a" * 64,
        "source": "LearnerAI",
        "code": "NATIVE-SUPPORT-005",
        "severity": "error",
        "confidence": None,
        "message": "unsupported native command",
        "suggestion": None,
        "path": "native-support/test.basilisk",
        "line": 1,
        "column": 1,
        "end_line": 1,
        "end_column": 1,
        "references": [],
    }
    support = {
        "command": "fixture-command",
        "state": "unsupported",
        "code": "NATIVE-SUPPORT-005",
        "severity": "error",
        "message": "native command is not present in the checked-in native schema",
    }
    return {
        "schema_version": 1,
        "python": "3.12.7",
        "platform": "linux",
        "fixtures": {
            name: {
                "diagnostics": [copy.deepcopy(diagnostic)],
                "support_diagnostics": [copy.deepcopy(support)],
                "support_state_sequence": ["unsupported"],
                "artifact_sha256": "b" * 64,
            }
            for name in FIXTURE_NAMES
        },
    }


class NativeSupportReplaySchemaTests(unittest.TestCase):
    def test_valid_snapshot_is_accepted(self):
        validate_snapshot(valid_snapshot())

    def test_missing_top_level_field_is_rejected(self):
        snapshot = valid_snapshot()
        del snapshot["platform"]

        with self.assertRaisesRegex(SnapshotSchemaError, "missing fields: platform"):
            validate_snapshot(snapshot)

    def test_extra_top_level_field_is_rejected(self):
        snapshot = valid_snapshot()
        snapshot["unexpected"] = True

        with self.assertRaisesRegex(SnapshotSchemaError, "extra fields: unexpected"):
            validate_snapshot(snapshot)

    def test_missing_diagnostic_field_is_rejected(self):
        snapshot = valid_snapshot()
        del snapshot["fixtures"]["unsupported"]["diagnostics"][0]["message"]

        with self.assertRaisesRegex(
            SnapshotSchemaError,
            "diagnostics\\[0\\].*missing fields: message",
        ):
            validate_snapshot(snapshot)

    def test_extra_diagnostic_field_is_rejected(self):
        snapshot = valid_snapshot()
        snapshot["fixtures"]["unsupported"]["diagnostics"][0]["unexpected"] = "x"

        with self.assertRaisesRegex(
            SnapshotSchemaError,
            "diagnostics\\[0\\].*extra fields: unexpected",
        ):
            validate_snapshot(snapshot)

    def test_malformed_diagnostic_payload_is_rejected(self):
        snapshot = valid_snapshot()
        snapshot["fixtures"]["unsupported"]["diagnostics"][0]["references"] = "not-an-array"

        with self.assertRaisesRegex(
            SnapshotSchemaError,
            "references: expected array",
        ):
            validate_snapshot(snapshot)

    def test_support_state_sequence_must_match_support_payload(self):
        snapshot = valid_snapshot()
        snapshot["fixtures"]["unsupported"]["support_state_sequence"] = [
            "native-known"
        ]

        with self.assertRaisesRegex(
            SnapshotSchemaError,
            "support_state_sequence must exactly match",
        ):
            validate_snapshot(snapshot)

    def test_invalid_artifact_hash_is_rejected(self):
        snapshot = valid_snapshot()
        snapshot["fixtures"]["unsupported"]["artifact_sha256"] = "not-a-hash"

        with self.assertRaisesRegex(
            SnapshotSchemaError,
            "artifact_sha256.*64-character",
        ):
            validate_snapshot(snapshot)


if __name__ == "__main__":
    unittest.main()
