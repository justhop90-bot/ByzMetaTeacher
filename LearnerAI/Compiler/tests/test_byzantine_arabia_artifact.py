from pathlib import Path
import re
import unittest


class ByzantineArabiaArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[3]
        cls.artifact = (cls.root / "Byzantine.per").read_text(encoding="utf-8")

    def test_arabia_standard_opening_selector_is_emitted(self):
        self.assertIn(
            "(goal opening-plan -1) (and (not (map-type islands)) "
            "(and (not (map-type arena)) "
            "(not (players-unit-type-count any-enemy militia-line >= 5))))",
            self.artifact,
        )
        self.assertIn("(set-goal opening-plan 1)", self.artifact)

    def test_dark_age_stone_camp_demands_start_inactive(self):
        section = self.artifact.split("; Demand initialization", 1)[1]
        section = section.split("; Persistent TC2-complete state", 1)[0]
        for floor in range(1, 6):
            self.assertIn(
                f"(set-goal demand-economy-stone-camp-floor-{floor} 0)",
                section,
            )
            self.assertNotIn(
                f"(set-goal demand-economy-stone-camp-floor-{floor} 1)",
                section,
            )

    def test_each_gold_camp_build_requires_a_positive_remote_search_witness(self):
        for floor in range(1, 6):
            start = self.artifact.index(f"; economy-gold-camp-floor-{floor}")
            end_marker = (
                f"; economy-gold-camp-floor-{floor + 1}"
                if floor < 5
                else "; economy-stone-camp-floor-1"
            )
            end = self.artifact.index(end_marker, start)
            section = self.artifact[start:end]

            base = 1020 + (floor - 1) * 4
            self.assertIn(
                f"(up-get-search-state byzantine-dark-gold-camp-search-state-{floor})",
                section,
            )
            witness = (
                f"(up-compare-goal "
                f"byzantine-dark-gold-camp-search-remote-count-{floor} > 0)"
            )
            self.assertIn(witness, section)

            witness_pos = section.index(witness)
            build_pos = section.index("(up-build place-point 0 c: mining-camp)")
            self.assertLess(witness_pos, build_pos)

            # The witness is the third goal in the four-goal search-state span:
            # local search count, local list count, remote search count, remote list count.
            self.assertIn(
                f"(defconst byzantine-dark-gold-camp-search-state-{floor} {base})",
                self.artifact,
            )


if __name__ == "__main__":
    unittest.main()
