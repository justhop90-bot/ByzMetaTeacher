from pathlib import Path
import re
import unittest


class ByzantineArabiaArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[3]
        cls.artifact = (cls.root / "Byzantine.per").read_text(encoding="utf-8")

    def test_arabia_standard_opening_selector_is_emitted(self):
        self.assertIn("(goal opening-plan -1)", self.artifact)
        self.assertIn("    (not (map-type arena))", self.artifact)
        self.assertIn(
            "    (not (or (players-unit-type-count any-enemy knight >= 3) "
            "(or (players-unit-type-count any-enemy archer-line >= 4) "
            "(players-unit-type-count any-enemy militia-line >= 5))))",
            self.artifact,
        )
        self.assertTrue(
            "    (not (map-type islands))" in self.artifact
            or "    (not (or (map-type islands) (map-type pacific-islands)))" in self.artifact
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

    def test_each_gold_camp_build_selects_an_indexed_active_resource(self):
        for floor in range(1, 6):
            start = self.artifact.index(f"; economy-gold-camp-floor-{floor}")
            end_marker = (
                f"; economy-gold-camp-floor-{floor + 1}"
                if floor < 5
                else "; economy-stone-camp-floor-1"
            )
            end = self.artifact.index(end_marker, start)
            section = self.artifact[start:end]

            state_name = f"byzantine-dark-gold-camp-search-state-{floor}"
            remote_name = f"byzantine-dark-gold-camp-search-remote-count-{floor}"
            point_name = "byzantine-dark-gold-camp-point"

            self.assertIn(f"(up-get-search-state {state_name})", section)
            self.assertIn("(up-filter-status c: status-resource c: list-active)", section)

            expected_results = 1 if floor == 1 else 40
            self.assertIn(f"(up-find-resource c: gold c: {expected_results})", section)

            witness = f"(up-compare-goal {remote_name} > {floor - 1})"
            self.assertIn(witness, section)
            self.assertIn(
                f"(up-set-target-object search-remote c: {floor - 1})",
                section,
            )
            self.assertIn(f"(up-get-point position-object {point_name})", section)
            self.assertIn(f"(up-set-target-point {point_name})", section)
            self.assertIn("(up-build place-point 0 c: mining-camp)", section)

            if floor >= 2:
                self.assertNotIn(
                    "(dropsite-min-distance gold",
                    section,
                    "higher gold floors must not be gated by the global nearest-gold dropsite distance",
                )

            state_match = re.search(
                rf"\(defconst {re.escape(state_name)} (\d+)\)",
                self.artifact,
            )
            remote_match = re.search(
                rf"\(defconst {re.escape(remote_name)} (\d+)\)",
                self.artifact,
            )
            point_match = re.search(
                rf"\(defconst {re.escape(point_name)} (\d+)\)",
                self.artifact,
            )
            self.assertIsNotNone(state_match)
            self.assertIsNotNone(remote_match)
            self.assertIsNotNone(point_match)
            assert state_match is not None
            assert remote_match is not None
            assert point_match is not None
            self.assertTrue(41 <= int(state_match.group(1)) <= 15996)
            self.assertTrue(1 <= int(remote_match.group(1)) <= 16000)
            self.assertTrue(41 <= int(point_match.group(1)) <= 15998)


if __name__ == "__main__":
    unittest.main()
