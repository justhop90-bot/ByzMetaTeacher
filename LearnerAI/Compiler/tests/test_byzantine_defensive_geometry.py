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

    def test_castle_reinforcement_can_raise_second_production_lane_without_villager_gate(self):
        expected = (
            "(goal byzantine-army-reinforcement 1)",
            "(population-headroom > 8)",
            "(wood-amount > 400)",
        )
        for fact in expected:
            self.assertIn(fact, self.per)

        self.assertIn(
            "(set-goal byzantine-production-barracks-target 2)",
            self.per,
        )
        self.assertIn(
            "(set-goal byzantine-production-archery-target 2)",
            self.per,
        )
        self.assertIn(
            "(set-goal byzantine-production-stable-target 2)",
            self.per,
        )
        self.assertIn(
            "(set-goal byzantine-production-siege-target 2)",
            self.per,
        )

    def test_offensive_production_tier_has_exposed_villager_fallback(self):
        production_start = self.per.index(
            "; production objective search, with candidate order preserved by the retained DUC list."
        )
        town_center_start = self.per.index(
            "; town-center objective search, with candidate order preserved by the retained DUC list."
        )
        production_section = self.per[production_start:town_center_start]
        self.assertIn("(up-find-remote c: monastery c: 1)", production_section)
        self.assertIn("(up-find-remote c: 83 c: 1)", production_section)

        witness_start = self.per.index(
            "(goal byzantine-offensive-objective-state byzantine-offensive-objective-state-witness)"
        )
        witness_production_class = self.per.index(
            "(goal byzantine-offensive-objective-class byzantine-offensive-objective-class-production)",
            witness_start,
        )
        witness_production_start = self.per.rfind(
            "(goal byzantine-offensive-objective-state byzantine-offensive-objective-state-witness)",
            witness_start,
            witness_production_class,
        )
        witness_town_class = self.per.index(
            "(goal byzantine-offensive-objective-class byzantine-offensive-objective-class-town-center)",
            witness_production_class,
        )
        witness_town_start = self.per.rfind(
            "(goal byzantine-offensive-objective-state byzantine-offensive-objective-state-witness)",
            witness_production_class,
            witness_town_class,
        )
        witness_production = self.per[witness_production_start:witness_town_start]
        self.assertIn("(up-find-remote c: 83 c: 1)", witness_production)

    def test_offensive_actor_radius_exceeds_target_locality(self):
        self.assertIn("(defconst bt-offensive-objective-radius 40)", self.per)
        self.assertIn("(defconst bt-offensive-objective-actor-radius 60)", self.per)

        objective_start = self.per.index("; LATE-GAME OBJECTIVE SEQUENCE")
        objective_end = self.per.index(
            "; A newly observed fortification supersedes an unfinished open-ground objective.",
            objective_start,
        )
        objective = self.per[objective_start:objective_end]
        markers = (
            "; siege objective search,",
            "; defense objective search,",
            "; production objective search,",
            "; town-center objective search,",
        )
        for index, marker in enumerate(markers):
            start_marker = objective.index(marker)
            end_marker = (
                objective.index(markers[index + 1], start_marker)
                if index + 1 < len(markers)
                else len(objective)
            )
            block = objective[start_marker:end_marker]
            actor_radius = "(up-filter-distance c: 0 c: bt-offensive-objective-actor-radius)"
            target_radius = "(up-filter-distance c: 0 c: bt-offensive-objective-radius)"
            self.assertIn(actor_radius, block)
            self.assertIn(target_radius, block)
            self.assertIn("(up-find-remote", block)
            self.assertLess(
                block.index(actor_radius),
                block.index("(up-find-local c: cavalry-class c: 1)"),
            )
            self.assertLess(
                block.index("(up-find-local c: trebuchet c: 1)"),
                block.rindex(target_radius),
            )

    def test_active_attack_reassesses_when_enemy_military_overmatches_coarsely(self):
        self.assertIn("(defconst byzantine-army-overmatch-state 357)", self.per)
        self.assertIn("(defconst byzantine-army-overmatch-none 0)", self.per)
        self.assertIn("(defconst byzantine-army-overmatch-triggered 1)", self.per)

        reassess_start = self.per.index("; COMMUNITY MILITARY-OVERMATCH REASSESSMENT")
        reposition_start = self.per.index("; ARMY REPOSITION / WITHDRAWAL CONTROLLER", reassess_start)
        section = self.per[reassess_start:reposition_start]

        buckets = (
            ("(players-military-population any-enemy > 5)", "(military-population < 2)"),
            ("(players-military-population any-enemy > 10)", "(military-population < 6)"),
            ("(players-military-population any-enemy > 15)", "(military-population < 10)"),
            ("(players-military-population any-enemy > 20)", "(military-population < 15)"),
            ("(players-military-population any-enemy > 25)", "(military-population < 20)"),
        )
        for enemy_fact, own_fact in buckets:
            self.assertIn(enemy_fact, section)
            self.assertIn(own_fact, section)

        self.assertIn("(up-reset-attack-now)", section)
        self.assertIn("(set-goal byzantine-army-reinforcement 1)", section)
        self.assertIn(
            "(set-goal byzantine-army-reposition-state byzantine-army-reposition-withdraw)",
            section,
        )
        self.assertIn(
            "(set-goal byzantine-siege-approach byzantine-siege-approach-normal)",
            section,
        )

    def test_minimum_viable_attack_admission_does_not_require_monks_or_ideal_mass(self):
        start = self.per.index("; MINIMUM-VIABLE CASTLE ATTACK ADMISSION")
        end = self.per.index("; FULL CASTLE ATTACK PACKAGE", start)
        section = self.per[start:end]

        self.assertIn("(defconst bt-castle-timing-cataphract-floor 3)", self.per)
        self.assertIn("(defconst bt-castle-timing-skirmisher-floor 2)", self.per)
        self.assertIn("(defconst bt-castle-timing-siege-floor 1)", self.per)
        self.assertIn("(defconst bt-imperial-timing-backbone-floor 4)", self.per)
        self.assertIn("(defconst bt-imperial-timing-halberdier-floor 4)", self.per)
        self.assertIn("(defconst bt-imperial-timing-siege-floor 1)", self.per)

        self.assertIn(
            "(unit-type-count-total cataphract-line >= bt-castle-timing-cataphract-floor)",
            section,
        )
        self.assertIn(
            "(unit-type-count-total skirmisher-line >= bt-castle-timing-skirmisher-floor)",
            section,
        )
        self.assertIn(
            "(unit-type-count-total mangonel-line >= bt-castle-timing-siege-floor)",
            section,
        )
        self.assertIn(
            "(unit-type-count-total battering-ram-line >= bt-castle-timing-siege-floor)",
            section,
        )
        self.assertNotIn("(unit-type-count-total monk", section)

        imperial_start = self.per.index("; MINIMUM-VIABLE IMPERIAL ATTACK ADMISSION")
        imperial_section = self.per[imperial_start:self.per.index("; FULL IMPERIAL ATTACK PACKAGE", imperial_start)]
        self.assertIn(
            "(unit-type-count-total cataphract-line >= bt-imperial-timing-backbone-floor)",
            imperial_section,
        )
        self.assertIn(
            "(unit-type-count-total 359 >= bt-imperial-timing-halberdier-floor)",
            imperial_section,
        )
        self.assertIn(
            "(unit-type-count-total trebuchet >= bt-imperial-timing-siege-floor)",
            imperial_section,
        )
        self.assertIn(
            "(unit-type-count-total bombard-cannon >= bt-imperial-timing-siege-floor)",
            imperial_section,
        )

    def test_attack_recovery_uses_minimum_viable_package_after_a_small_push(self):
        start = self.per.index("; Package loss during a fortified approach")
        end = self.per.index("; Bounded stale-army recovery", start)
        section = self.per[start:end]

        self.assertIn(
            "(unit-type-count-total cataphract-line < bt-castle-timing-cataphract-floor)",
            section,
        )
        self.assertIn(
            "(unit-type-count-total skirmisher-line < bt-castle-timing-skirmisher-floor)",
            section,
        )
        self.assertIn(
            "(unit-type-count-total mangonel-line < bt-castle-timing-siege-floor)",
            section,
        )
        self.assertNotIn(
            "(unit-type-count-total monk < bt-castle-monk-floor)",
            section,
        )
        self.assertIn(
            "(unit-type-count-total 359 < bt-imperial-timing-halberdier-floor)",
            section,
        )
        self.assertIn(
            "(unit-type-count-total trebuchet < bt-imperial-timing-siege-floor)",
            section,
        )

    def test_objective_execution_revalidates_attack_admission(self):
        objective_classes = (
            "byzantine-offensive-objective-class-siege",
            "byzantine-offensive-objective-class-defense",
            "byzantine-offensive-objective-class-production",
            "byzantine-offensive-objective-class-town-center",
        )
        for objective_class in objective_classes:
            state = (
                "(goal byzantine-offensive-objective-state "
                "byzantine-offensive-objective-state-"
            )
            if objective_class.endswith("siege"):
                state += "siege)"
            elif objective_class.endswith("defense"):
                state += "defense)"
            elif objective_class.endswith("production"):
                state += "production)"
            else:
                state += "town-center)"
            class_marker = f"    {state}\n    (goal {objective_class})"
            start = self.per.index(class_marker)
            end = self.per.index("\n\n(defrule", start + len(class_marker))
            section = self.per[start:end]
            self.assertIn("(goal byzantine-army-attack-ready 1)", section)
            self.assertIn(
                "(up-target-objects 1 action-attack-move -1 -1)",
                section,
            )

    def test_fortified_breach_preserves_attack_reserve(self):
        start = self.per.index(
            "(goal byzantine-siege-approach byzantine-siege-approach-breach)"
        )
        end = self.per.index(
            "; Breach truth is world-state truth, not action issuance.",
            start,
        )
        section = self.per[start:end]
        self.assertIn("(set-strategic-number sn-percent-attack-soldiers 75)", section)
        self.assertNotIn("(set-strategic-number sn-percent-attack-soldiers 100)", section)

    def test_fortified_siege_commitment_revalidates_before_breach(self):
        start = self.per.index(
            "(goal byzantine-siege-approach byzantine-siege-approach-escorted)"
        )
        end = self.per.index("; Guarded breach admission.", start)
        section = self.per[start:end]

        self.assertIn(
            "(unit-type-count-total mangonel-line < bt-castle-timing-siege-floor)",
            section,
        )
        self.assertIn(
            "(unit-type-count-total battering-ram-line < bt-castle-timing-siege-floor)",
            section,
        )
        self.assertIn(
            "(unit-type-count-total trebuchet < bt-imperial-timing-siege-floor)",
            section,
        )
        self.assertIn(
            "(unit-type-count-total bombard-cannon < bt-imperial-timing-siege-floor)",
            section,
        )
        self.assertIn(
            "(unit-type-count-total battering-ram-line < bt-imperial-timing-siege-floor)",
            section,
        )
        self.assertIn(
            "(set-goal byzantine-army-attack-ready 0)",
            section,
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

    def test_native_perimeter_rearms_after_breach(self):
        gate_release = self.per.index(
            "(goal byzantine-wall-native-state byzantine-wall-native-gate-armed)"
        )
        gate_release_end = self.per.index(
            "; Native perimeter completion is independent of action issuance.",
            gate_release,
        )
        gate_release_rule = self.per[gate_release:gate_release_end]
        self.assertIn(
            "(wall-completed-percentage byzantine-wall-native-perimeter >= 42)",
            gate_release_rule,
        )

        breach_start = self.per.index(
            "; Breach witness: a gated perimeter below the build threshold is no longer"
        )
        breach_end = self.per.index(
            "; Native perimeter completion is independent of action issuance.",
            breach_start,
        )
        breach_rule = self.per[breach_start:breach_end]
        self.assertIn(
            "(wall-completed-percentage byzantine-wall-native-perimeter < 42)",
            breach_rule,
        )
        self.assertIn("(set-goal demand-adaptive-stone-wall 1)", breach_rule)
        self.assertIn(
            "(set-goal byzantine-wall-native-state byzantine-wall-native-idle)",
            breach_rule,
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
