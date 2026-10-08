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
            "(goal opening-plan -1)\n"
            "    (not (map-type islands))\n"
            "    (not (map-type arena))\n"
            "    (not (or (players-unit-type-count any-enemy knight >= 3) "
            "(or (players-unit-type-count any-enemy archer-line >= 4) "
            "(players-unit-type-count any-enemy militia-line >= 5))))",
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

    def test_dark_age_lumber_then_first_mill_liveness_valve_is_present(self):
        marker = "; Dark Age first-mill continuity safety valve"
        self.assertIn(marker, self.artifact)

        start = self.artifact.index(marker)
        end = self.artifact.find("\n; Narrow Dark Age second-mill rule:", start)
        self.assertGreaterEqual(end, start)
        valve = self.artifact[start:end]

        for required in (
            "(goal demand-economy-food-mill-boom 1)",
            "(current-age == dark-age)",
            "(building-type-count-total lumber-camp >= 1)",
            "(building-type-count-total mill == 0)",
            "(up-pending-objects c: 68 == 0)",
            "(not (up-pending-placement c: 68))",
            "(goal action-claim-build-pass-singleton 0)",
            "(resource-found food)",
            "(wood-amount >= 50)",
            "(unit-type-count-total villager >= 18)",
            "(can-build mill)",
            "(build mill)",
            "(set-goal demand-economy-food-mill-boom 71)",
        ):
            self.assertIn(required, valve)

    def test_each_gold_camp_build_selects_an_indexed_active_resource(self):
        for floor in range(1, 6):
            search_marker = (
                f"; Native DUC rule: byzantine-camp-placement-gold-{floor}-search"
            )
            place_marker = (
                f"; Native DUC rule: byzantine-camp-placement-gold-{floor}-place"
            )
            start = self.artifact.index(search_marker)
            place_start = self.artifact.index(place_marker, start)
            next_rule = self.artifact.find("\n; Native DUC rule:", place_start + 1)
            if next_rule < 0:
                next_rule = self.artifact.index(
                    f"; Native placement execution: economy-gold-camp-floor-{floor}"
                )
            search_section = self.artifact[start:place_start]
            place_section = self.artifact[place_start:next_rule]

            self.assertIn("(up-filter-status c: status-resource c: list-active)", search_section)
            expected_results = 1 if floor == 1 else 40
            self.assertIn(
                f"(up-find-resource c: gold c: {expected_results})",
                search_section,
            )

            expected_index = 0 if floor <= 2 else floor - 2
            self.assertIn(
                "(up-compare-goal ",
                place_section,
            )
            self.assertIn(
                f"(up-set-target-object search-remote c: {expected_index})",
                place_section,
            )
            self.assertIn("(up-get-point position-object", place_section)
            self.assertIn("(up-set-target-point", place_section)

            execution_start = self.artifact.index(
                f"; Native placement execution: economy-gold-camp-floor-{floor}"
            )
            execution_end = self.artifact.find("\n; ", execution_start + 10)
            execution = (
                self.artifact[execution_start:]
                if execution_end < 0
                else self.artifact[execution_start:execution_end]
            )
            self.assertIn("(up-build place-point 0 c:", execution)

            if floor >= 2:
                self.assertNotIn(
                    "(dropsite-min-distance gold",
                    search_section + place_section,
                    "higher gold floors must not be gated by global dropsite distance",
                )


if __name__ == "__main__":
    unittest.main()
