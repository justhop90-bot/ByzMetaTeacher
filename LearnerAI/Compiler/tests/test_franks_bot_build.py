from __future__ import annotations

import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path

from tools.build_franks_bot import SOURCE, build


class FranksBotBuildTests(unittest.TestCase):
    def test_package_is_byte_identical_to_canonical_source(self):
        with tempfile.TemporaryDirectory() as temp:
            artifact, manifest_path = build(Path(temp))
            source = SOURCE.read_bytes()
            self.assertEqual(artifact.read_bytes(), source)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(
                manifest["artifact_sha256"],
                hashlib.sha256(source).hexdigest(),
            )
            self.assertEqual(manifest["artifact_sha256"], manifest["source_sha256"])
            self.assertEqual(manifest["runtime_status"], "NOT_YET_RUNTIME_TESTED")
            self.assertEqual(manifest["game_patch"], "AOE2DE:185872:2026-09-22")

    def test_repeated_builds_have_equal_artifact_and_manifest(self):
        with tempfile.TemporaryDirectory() as first_temp, tempfile.TemporaryDirectory() as second_temp:
            first_artifact, first_manifest = build(Path(first_temp))
            second_artifact, second_manifest = build(Path(second_temp))
            self.assertEqual(first_artifact.read_bytes(), second_artifact.read_bytes())
            self.assertEqual(
                json.loads(first_manifest.read_text(encoding="utf-8")),
                json.loads(second_manifest.read_text(encoding="utf-8")),
            )

    def test_strategy_contains_full_match_milestones_and_patch_specific_units(self):
        source = SOURCE.read_text(encoding="utf-8")
        expected = (
            "(research feudal-age)",
            "(research castle-age)",
            "(research imperial-age)",
            "(train scout-cavalry)",
            "(train knight-line)",
            "(train frank-throwing-axeman)",
            "(train frank-mounted-crossbowman)",
            "(research ri-ordonnance-companies)",
            "(research ri-horse-collar)",
            "(research ri-heavy-plow)",
            "(research ri-crop-rotation)",
            "(research ri-cranequins)",
            "(train battering-ram-line)",
            "(train trebuchet)",
            "(attack-now)",
            "(up-find-player enemy find-closest frank-target-player-goal)",
            "(dropsite-min-distance wood > 8)",
            "(dropsite-min-distance gold > 8)",
            "(dropsite-min-distance stone > 8)",
            "(up-pending-objects c: frank-c-house == 0)",
            "(unit-type-count villager >= 25)",
        )
        for fragment in expected:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)
        self.assertGreaterEqual(source.count("(defrule"), 80)

    def test_goal_comparisons_use_native_comparison_primitive(self):
        source = SOURCE.read_text(encoding="utf-8")
        invalid = re.findall(
            r"\\(goal\\s+[^\\s()]+\\s+(?:==|!=|<=|>=|<|>)\\s+[^()]+\\)",
            source,
        )
        self.assertEqual(
            invalid,
            [],
            "goal is equality-only; ordered and inequality comparisons must use up-compare-goal",
        )
        self.assertIn(
            "(up-compare-goal frank-target-player-goal >= 1)",
            source,
        )

    def test_no_byzantine_or_removed_frankish_strategy_leaks_into_bot(self):
        source = SOURCE.read_text(encoding="utf-8").lower()
        for forbidden in ("cataphract", "varangian-guard", "ri-bearded-axe", "cavalry-archer-line"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
