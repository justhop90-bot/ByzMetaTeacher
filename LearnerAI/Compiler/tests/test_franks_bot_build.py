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

    def test_initialization_is_staged_below_native_rule_size_budget(self):
        source = SOURCE.read_text(encoding="utf-8")
        start = source.index("; Initialize all Frankish strategic state in bounded, one-shot stages.")
        end = source.index("; Acquire a valid enemy player", start)
        initialization = source[start:end]
        rules = re.findall(r"\(defrule\b(.*?)\n\)", initialization, flags=re.S)

        self.assertEqual(len(rules), 3)
        form_counts = [
            sum(bool(re.match(r"^ {4}\(", line)) for line in rule.splitlines())
            for rule in rules
        ]
        self.assertLessEqual(
            max(form_counts),
            16,
            f"initialization stage exceeds conservative native rule budget: {form_counts}",
        )
        self.assertIn("(goal frank-init-stage-goal 0)", rules[0])
        self.assertIn("(goal frank-init-stage-goal 1)", rules[1])
        self.assertIn("(goal frank-init-stage-goal 2)", rules[2])
        self.assertNotIn("(set-goal frank-initialized-goal 1)", rules[0])
        self.assertNotIn("(set-goal frank-initialized-goal 1)", rules[1])
        self.assertIn("(set-goal frank-initialized-goal 1)", rules[2])

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
            "(research 1451)",
            "(research ri-ordonnance-companies)",
            "(research ri-pikeman)",
            "(research ri-halberdier)",
            "(research ri-elite-skirmisher)",
            "(research ri-fletching)",
            "(research ri-bodkin-arrow)",
            "(research ri-ballistics)",
            "(research ri-capped-ram)",
            "(up-reset-attack-now)",
            "(research ri-horse-collar)",
            "(research ri-heavy-plow)",
            "(research ri-crop-rotation)",
            "(research ri-cranequins)",
            "(train battering-ram-line)",
            "(train trebuchet)",
            "(attack-now)",
            "(up-find-player enemy find-closest frank-target-player-goal)",
            "(dropsite-min-distance wood > 10)",
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
            r"\(goal\s+[^\s()]+\s+(?:==|!=|<=|>=|<|>)\s+[^()]+\)",
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


    def test_no_franks_unavailable_research_endpoints_are_requested(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("(research ri-siege-ram)", source)
        self.assertNotIn("(research ri-two-man-saw)", source)
        self.assertIn("(research ri-capped-ram)", source)
        self.assertIn("(defconst frank-c-capped-ram-tech 96)", source)

    def test_dark_age_has_second_building_fallback_without_distance_deadlock(self):
        source = SOURCE.read_text(encoding="utf-8")
        lumber_start = source.index("; Build the first lumber camp")
        mill_start = source.index("; Build a mill on a real forage resource")
        fallback_start = source.index("; If forage is absent, a resource-adjacent Mining Camp")
        gold_start = source.index("; Build a gold camp only when Gold")
        lumber = source[lumber_start:mill_start]
        mill = source[mill_start:fallback_start]
        fallback = source[fallback_start:gold_start]
        self.assertNotIn("(dropsite-min-distance wood > 8)", lumber)
        self.assertNotIn("(dropsite-min-distance forage > 7)", mill)
        self.assertIn("(not (resource-found forage))", fallback)
        self.assertIn("(can-build mining-camp)", fallback)

    def test_age_up_prerequisites_do_not_depend_on_market_or_elephant_response(self):
        source = SOURCE.read_text(encoding="utf-8")
        castle_start = source.index("; Commit Castle Age once")
        imperial_start = source.index("; Commit Imperial Age")
        villager_start = source.index("; Keep Town Centers producing villagers")
        castle_rule = source[castle_start:imperial_start]
        imperial_rule = source[imperial_start:villager_start]
        self.assertIn("(building-type-count stable >= 1)", castle_rule)
        self.assertIn("(building-type-count blacksmith >= 1)", castle_rule)
        self.assertNotIn("(building-type-count market >= 1)", castle_rule)
        self.assertIn("(can-research-with-escrow imperial-age)", imperial_rule)
        self.assertNotIn("(building-type-count market >= 1)", imperial_rule)
        self.assertIn("(building-type-count-total university < 1)", source)
        self.assertIn("(not (can-build castle))", source)
        self.assertIn("(building-type-count siege-workshop >= 1)", source)

    def test_counter_upgrades_and_new_mounted_crossbow_upgrade_have_witnesses(self):
        source = SOURCE.read_text(encoding="utf-8")
        expected = (
            "(research ri-pikeman)",
            "(research ri-halberdier)",
            "(research ri-elite-skirmisher)",
            "(up-research-status c: frank-c-heavy-mounted-crossbowman-tech < research-pending)",
            "(can-research-with-escrow 1451)",
            "(research 1451)",
            "(up-research-status c: frank-c-heavy-mounted-crossbowman-tech == research-complete)",
            "(research ri-cranequins)",
        )
        for fragment in expected:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)


    def test_late_infantry_counter_can_activate_in_imperial_age(self):
        source = SOURCE.read_text(encoding="utf-8")
        elite_start = source.index("; Research Elite Throwing Axeman before adding more base units")
        base_start = source.index("; Base Throwing Axemen may enter in Imperial Age", elite_start)
        mounted_start = source.index("; Add Mounted Crossbowmen to support Knights", base_start)
        elite_rule = source[elite_start:base_start]
        base_rule = source[base_start:mounted_start]
        self.assertIn("(current-age >= imperial-age)", elite_rule)
        self.assertIn("(unit-type-count frank-throwing-axeman >= 6)", elite_rule)
        self.assertIn("(current-age >= castle-age)", base_rule)
        self.assertIn("(up-research-status c: frank-c-elite-throwing-axeman-tech < research-pending)", base_rule)
        self.assertLess(elite_start, base_start)

    def test_mounted_ranged_techs_are_guarded_by_package_and_resource_reserves(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("(research ri-fletching)", source)
        self.assertIn("(research ri-bodkin-arrow)", source)
        self.assertIn("(research ri-ballistics)", source)
        for reserve in ("(food-amount >= 1100)", "(gold-amount >= 850)",
                        "(food-amount >= 1200)", "(gold-amount >= 900)",
                        "(food-amount >= 1300)", "(gold-amount >= 975)"):
            with self.subTest(reserve=reserve):
                self.assertIn(reserve, source)
        self.assertIn("(building-type-count university >= 1)", source)

    def test_attack_cycle_resets_native_attack_loop(self):
        source = SOURCE.read_text(encoding="utf-8")
        start = source.index("; Complete the timed attack cycle")
        end = source.index("; Reassess attack readiness", start)
        attack_reset_rule = source[start:end]
        self.assertIn("(up-reset-attack-now)", attack_reset_rule)
        self.assertLess(
            attack_reset_rule.index("(up-reset-attack-now)"),
            attack_reset_rule.index("(enable-timer frank-attack-cooldown-timer 45)"),
        )

    def test_economy_recovery_modes_are_exclusive_and_recover(self):
        source = SOURCE.read_text(encoding="utf-8")
        for mode in (1, 2, 3):
            with self.subTest(mode=mode):
                self.assertIn(f"(set-goal frank-economy-recovery-goal {mode})", source)
                self.assertIn(f"(goal frank-economy-recovery-goal {mode})", source)
        self.assertIn("(food-amount >= 400)", source)
        self.assertIn("(gold-amount >= 400)", source)
        self.assertIn("(wood-amount >= 300)", source)
        self.assertNotIn("; Protect food production during a food crisis.", source)

    def test_no_byzantine_or_removed_frankish_strategy_leaks_into_bot(self):
        source = SOURCE.read_text(encoding="utf-8").lower()
        for forbidden in ("cataphract", "varangian-guard", "ri-bearded-axe", "cavalry-archer-line"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
