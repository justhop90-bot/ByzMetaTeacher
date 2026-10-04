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
            "(set-goal byzantine-bombard-tower-target byzantine-bombard-tower-target-two)",
            self.per,
        )
        self.assertIn(
            "(stone-amount > bt-byzantine-bombard-stone-surplus)",
            self.per,
        )
        self.assertIn(
            "(gold-amount > bt-byzantine-bombard-gold-surplus)",
            self.per,
        )

    def test_bombard_tower_does_not_compete_with_first_castle(self):
        self.assertIn("(building-type-count-total castle >= 1)", self.per)
        self.assertIn("(stone-amount >= bt-byzantine-static-stone-reserve)", self.per)
        self.assertIn("(gold-amount >= bt-byzantine-bombard-gold-reserve)", self.per)

    def test_extreme_surplus_adds_a_final_production_capacity_tier(self):
        # Final throughput tier directly addresses the observed all-resource
        # late-game bank instead of adding more passive static defense.
        self.assertIn(
            "(set-goal byzantine-production-barracks-target 6)",
            self.per,
        )
        self.assertIn(
            "(set-goal byzantine-production-archery-target 5)",
            self.per,
        )
        self.assertIn(
            "(set-goal byzantine-production-stable-target 5)",
            self.per,
        )
        self.assertIn(
            "(set-goal byzantine-production-siege-target 5)",
            self.per,
        )
        self.assertIn(
            "(goal byzantine-production-barracks-target 6)",
            self.per,
        )
        self.assertIn(
            "(goal byzantine-production-archery-target 5)",
            self.per,
        )
        self.assertIn(
            "(goal byzantine-production-stable-target 5)",
            self.per,
        )
        self.assertIn(
            "(goal byzantine-production-siege-target 5)",
            self.per,
        )

    def test_keep_respects_castle_stone_commitment_and_uses_frontier_fallback(self):
        self.assertIn(
            "(not (goal byzantine-production-castle-target 2))",
            self.per,
        )
        self.assertIn(
            "(not (goal byzantine-production-castle-target 3))",
            self.per,
        )
        self.assertIn("(build-forward keep)", self.per)

    def test_bombard_tower_has_a_wall_frontier_fallback(self):
        self.assertIn("(build-forward bombard-tower)", self.per)

    def test_native_choke_scorer_ranks_resource_and_fortified_candidates(self):
        self.assertIn(
            "(defconst byzantine-static-defense-score-state 714)",
            self.per,
        )
        self.assertIn(
            "(defconst byzantine-static-defense-resource-score 716)",
            self.per,
        )
        self.assertIn(
            "(defconst byzantine-static-defense-fortified-score 717)",
            self.per,
        )
        self.assertIn(
            "(defconst byzantine-static-defense-placement-kind 718)",
            self.per,
        )
        self.assertIn(
            "(defconst byzantine-static-defense-score-timer 15)",
            self.per,
        )
        self.assertIn(
            "(up-compare-goal byzantine-static-defense-resource-score g:>=",
            self.per,
        )
        self.assertIn(
            "(set-goal byzantine-static-defense-placement-kind byzantine-static-defense-placement-resource)",
            self.per,
        )
        self.assertIn(
            "(set-goal byzantine-static-defense-placement-kind byzantine-static-defense-placement-fortified)",
            self.per,
        )
        self.assertIn(
            "(goal byzantine-wall-geometry-state byzantine-wall-geometry-armed)",
            self.per,
        )
        self.assertIn(
            "(up-compare-goal byzantine-static-defense-resource-score g:>= byzantine-static-defense-fortified-score)",
            self.per,
        )

    def test_dark_age_second_mill_requires_positive_forage_search_witness(self):
        rules = ["(defrule" + chunk for chunk in self.per.split("(defrule")[1:]]
        search_rule = next(
            rule
            for rule in rules
            if "(current-age == dark-age)" in rule
            and "(up-find-remote c: byzantine-forage-bush c: 40)" in rule
            and "(up-get-search-state byzantine-dark-mill-search-state)" in rule
        )
        build_rule = next(
            rule
            for rule in rules
            if "(current-age == dark-age)" in rule
            and "(up-build place-point 0 c: mill)" in rule
        )
        self.assertIn(
            "(defconst byzantine-dark-mill-search-state 1040)",
            self.per,
        )
        self.assertIn(
            "(defconst byzantine-dark-mill-search-remote-count 1042)",
            self.per,
        )
        self.assertIn(
            "(up-compare-goal byzantine-dark-mill-search-remote-count > 0)",
            build_rule,
        )
        self.assertNotIn(
            "(up-build place-point 0 c: mill)",
            search_rule,
        )

    def test_goal_comparisons_use_up_compare_goal(self):
        # `goal` is exact equality only. Comparator forms belong to
        # `up-compare-goal`; letting `(goal G > 0)` through produces a native
        # parser failure that can misleadingly surface on the operator line.
        invalid = re.findall(
            r"\\(goal\\s+[^\\s()]+\\s+(?:==|!=|<=|>=|<|>)\\s+[^()]+\\)",
            self.per,
        )
        self.assertEqual(
            invalid,
            [],
            f"goal comparator facts must use up-compare-goal: {invalid}",
        )

    def test_keep_and_bombard_build_only_through_scored_geometry(self):
        self.assertIn(
            "(goal byzantine-static-defense-score-state byzantine-static-defense-score-resource-selected)",
            self.per,
        )
        self.assertIn(
            "(goal byzantine-static-defense-score-state byzantine-static-defense-score-fortified-selected)",
            self.per,
        )
        self.assertNotIn("(build 235)", self.per)
        self.assertNotIn("(build 236)", self.per)

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
