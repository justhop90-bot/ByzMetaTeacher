"""Deterministic canonical Byzantine Core v1 build contract tests."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.build_byzantine_bot import NATIVE_PARSER_REVISION, build


_OBJECTIVE_DISPATCH_IDENTITIES = (
    "byzantine-endgame-objective-dispatch-siege",
    "byzantine-endgame-objective-dispatch-defense",
    "byzantine-endgame-objective-dispatch-production",
    "byzantine-endgame-objective-dispatch-town-center",
)
_OBJECTIVE_ATTACK_DISPATCH = "(up-target-objects 1 action-attack-move -1 -1)"
_ROLE_FORBIDDEN_ACTIONS = (
    "attack-now",
    "attack-groups",
    "action-attack-move",
    "up-target-objects",
    "up-target-point",
    "action-move",
    "(stop",
)


def _role_block(artifact: str) -> str:
    start_markers = (
        "; Native Byzantine role-separation plan",
        "; Byzantine military role separation",
    )
    starts = [artifact.find(marker) for marker in start_markers]
    starts = [offset for offset in starts if offset >= 0]
    if not starts:
        raise ValueError("role block marker not found")
    start = min(starts)
    end = artifact.find("; Native DUC execution plan", start)
    if end < 0:
        end = len(artifact)
    return artifact[start:end]


def _duc_rule_block(artifact: str, identity: str) -> str:
    marker = f"; Native DUC rule: {identity}"
    start = artifact.find(marker)
    if start < 0:
        raise ValueError(f"DUC rule marker not found: {identity}")
    next_rule = artifact.find("\n; Native DUC rule: ", start + len(marker))
    if next_rule < 0:
        next_rule = len(artifact)
    return artifact[start:next_rule]


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

    def test_canonical_dist_artifact_contains_four_objective_attack_dispatches_and_preserves_role_separation(self):
        with tempfile.TemporaryDirectory() as root:
            artifact, _manifest = build(Path(root))

            self.assertEqual(
                artifact.relative_to(Path(root)),
                Path("dist/byzantine/Byzantine.per"),
            )
            rendered = artifact.read_text(encoding="utf-8")

            self.assertEqual(rendered.count(_OBJECTIVE_ATTACK_DISPATCH), 4)
            for identity in _OBJECTIVE_DISPATCH_IDENTITIES:
                rule = _duc_rule_block(rendered, identity)
                self.assertIn(
                    "(up-set-target-object search-remote c: 0)",
                    rule,
                )
                self.assertIn("(up-compare-goal byzantine-army-role-state >= byzantine-army-role-committed)", rule)
                self.assertIn("(up-compare-goal byzantine-army-role-state <= byzantine-army-role-raid-split)", rule)
                self.assertIn("(up-get-object-data id 0)", rule)
                self.assertIn("(up-filter-include cmdid-military -1 -1 -1)", rule)
                self.assertIn("(up-find-local c: -1 c: 240)", rule)
                self.assertIn("(up-remove-objects search-local 19 != 2)", rule)
                self.assertIn("(up-remove-objects search-local 1 == 125)", rule)
                self.assertIn(_OBJECTIVE_ATTACK_DISPATCH, rule)
                self.assertNotIn("(or ", rule)
                self.assertIn(
                    "(up-reset-search 0 0 1 1)",
                    rule,
                )
                for forbidden in (
                    "set-goal",
                    "enable-timer",
                    "disable-timer",
                    "up-modify-sn",
                    "up-get-point",
                ):
                    self.assertNotIn(forbidden, rule)

            role_block = _role_block(rendered)
            for forbidden in _ROLE_FORBIDDEN_ACTIONS:
                self.assertNotIn(forbidden, role_block)


if __name__ == "__main__":
    unittest.main()
