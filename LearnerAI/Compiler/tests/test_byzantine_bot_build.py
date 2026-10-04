"""Deterministic canonical Byzantine Core v1 build contract tests."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.build_byzantine_bot import NATIVE_PARSER_REVISION, build


class ByzantineBotBuildTests(unittest.TestCase):
    def test_canonical_build_is_byte_deterministic_and_manifest_matches(self):
        with tempfile.TemporaryDirectory() as first_root, tempfile.TemporaryDirectory() as second_root:
            first_artifact, first_manifest = build(Path(first_root))
            second_artifact, second_manifest = build(Path(second_root))

            first_bytes = first_artifact.read_bytes()
            second_bytes = second_artifact.read_bytes()
            self.assertEqual(first_bytes, second_bytes)

            first_data = json.loads(first_manifest.read_text(encoding="utf-8"))
            second_data = json.loads(second_manifest.read_text(encoding="utf-8"))
            self.assertEqual(first_data, second_data)

            expected_sha = hashlib.sha256(first_bytes).hexdigest()
            self.assertEqual(first_data["artifact_sha256"], expected_sha)
            self.assertEqual(first_data["artifact_sha256"], second_data["artifact_sha256"])
            self.assertTrue(first_data["determinism"]["second_compile_equal"])
            self.assertEqual(first_data["native_parser_revision"], NATIVE_PARSER_REVISION)
            self.assertEqual(
                first_data["build_input_identity"]["profile_entrypoint"],
                "ByzantineProfile.for_update_185872",
            )
            self.assertEqual(
                first_data["build_input_identity"]["strategy_entrypoint"],
                "build_byzantine_strategy",
            )
            self.assertEqual(
                first_data["build_input_identity"]["compiler_entrypoint"],
                "compile_strategy_profile",
            )
            self.assertEqual(
                first_data["build_input_identity"]["effective_snapshot_fingerprint"],
                first_data["effective_snapshot_fingerprint"],
            )
            self.assertEqual(
                first_data["build_input_identity"]["profile_id"],
                first_data["profile_id"],
            )
            self.assertEqual(
                first_data["build_input_identity"]["patch_key"],
                first_data["patch_key"],
            )
            self.assertEqual(len(first_data["compiler_source_revision"]), 40)
            self.assertGreater(first_data["artifact_line_count"], 0)
            self.assertGreater(first_data["artifact_rule_count"], 0)
            self.assertGreater(first_data["artifact_byte_length"], 0)


if __name__ == "__main__":
    unittest.main()
