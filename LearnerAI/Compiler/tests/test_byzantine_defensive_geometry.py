import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PER_PATH = REPO_ROOT / "Byzantine.per"


class ByzantineDefensiveGeometryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.per = PER_PATH.read_text(encoding="utf-8")

    def test_tower_geometry_prefers_elevation_and_point_placement(self):
        self.assertIn(
            "(set-strategic-number sn-ignore-tower-elevation 0)",
            self.per,
        )
        self.assertIn("(defconst byzantine-defensive-build-point 710)", self.per)
        self.assertIn("(up-build place-point 0 c: watch-tower)", self.per)
        self.assertIn("(up-build place-point 0 c: keep)", self.per)
        self.assertIn("(up-build place-point 0 c: bombard-tower)", self.per)

    def test_static_defense_has_a_single_stone_spend_channel(self):
        self.assertIn(
            "(defconst byzantine-bombard-tower-target 713)",
            self.per,
        )
        self.assertIn(
            "(set-goal byzantine-bombard-tower-target 2)",
            self.per,
        )
        self.assertRegex(
            self.per,
            re.compile(
                r"\(goal byzantine-bombard-tower-target 1\)"
                r"[\s\S]{0,1600}"
                r"\(stone-amount > 900\)"
                r"[\s\S]{0,600}"
                r"\(gold-amount > 2500\)"
            ),
        )

    def test_bombard_tower_does_not_compete_with_first_castle(self):
        action_start = self.per.index(
            "; Action issuance: imperial-bombard-tower-floor | ACTIVE -> ISSUED"
        )
        action_block = self.per[action_start : self.per.index(
            "; Pending diagnostics: research-wheelbarrow",
            action_start,
        )]
        self.assertIn("(building-type-count-total castle >= 1)", action_block)
        self.assertIn("(stone-amount >= 250)", action_block)
        self.assertIn("(gold-amount >= 1000)", action_block)

    def test_greek_fire_land_trigger_requires_actual_artillery(self):
        marker = "(set-goal demand-water-greek-fire 1)"
        start = self.per.index(marker) - 2200
        trigger = self.per[start : start + 2500]
        self.assertTrue(
            "(building-type-count-total bombard-tower >= 1)" in trigger
            or "(building-type-count-total bombard-cannon >= 1)" in trigger,
            "Greek Fire must be tied to an actual artillery witness on land",
        )


if __name__ == "__main__":
    unittest.main()
