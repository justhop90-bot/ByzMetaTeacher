import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PER_PATH = REPO_ROOT / "Byzantine.per"


class ByzantineNativeSeamTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.per = PER_PATH.read_text(encoding="utf-8")

    def _rules(self):
        return re.findall(r"(?ms)^\(defrule\n.*?(?=^\(defrule\n|\Z)", self.per)

    def test_native_target_evaluation_and_priority_plane_is_explicit(self):
        target_evaluation = (
            "siege-weapon 50",
            "damage-capability 20",
            "in-progress 0",
            "distance 0",
            "hitpoints 0",
            "range 0",
            "rof 0",
            "time-kill-ratio 50",
            "attack-attempts 0",
            "ally-proximity 0",
            "randomness 0",
            "boat 0",
            "continent 0",
            "kills 0",
        )
        for suffix in target_evaluation:
            self.assertIn(
                f"(set-strategic-number sn-target-evaluation-{suffix})",
                self.per,
            )
        for fragment in (
            "(set-strategic-number sn-enable-offensive-priority 1)",
            "(set-strategic-number sn-local-targeting-mode 1)",
            "(up-set-offense-priority c: castle c: 100)",
            "(up-set-offense-priority c: keep c: 90)",
            "(up-set-offense-priority c: bombard-tower c: 85)",
            "(up-set-offense-priority c: siege-workshop c: 70)",
            "(up-set-defense-priority c: castle c: 5000)",
            "(up-set-defense-priority c: keep c: 5000)",
        ):
            self.assertIn(fragment, self.per)

    def test_target_player_plane_is_distinct_and_wired_into_attack_execution(self):
        for fragment in (
            "(defconst sn-target-player-number 249)",
            "(defconst byzantine-target-player-lock 744)",
            "(set-strategic-number sn-target-player-number 0)",
            "(up-modify-sn sn-target-player-number s:= sn-focus-player-number)",
            "(goal byzantine-target-player-lock 0)",
            "(goal byzantine-target-player-lock 1)",
            "(players-unit-type-count target-player knight >= 3)",
            "(players-unit-type-count target-player mangonel-line >= 2)",
        ):
            self.assertIn(fragment, self.per)

        attack_rules = [rule for rule in self._rules() if "(attack-now)" in rule]
        self.assertGreaterEqual(len(attack_rules), 2)
        for rule in attack_rules:
            self.assertIn(
                "(strategic-number sn-target-player-number >= 1)",
                rule,
                "Every attack issuance must have a valid target-player identity.",
            )
            self.assertIn(
                "(player-in-game target-player)",
                rule,
                "Every attack issuance must validate the target player before issuance.",
            )

    def test_focus_fact_profile_is_materialized_and_consumed(self):
        for fragment in (
            "(up-get-focus-fact military-population 0 byzantine-focus-military-pop)",
            "(up-get-focus-fact civilian-population 0 byzantine-focus-civilian-pop)",
            "(up-get-focus-fact building-type-count stable byzantine-focus-stables)",
            "(up-get-focus-fact building-type-count archery-range byzantine-focus-ranges)",
            "(up-get-focus-fact building-type-count siege-workshop byzantine-focus-siege-workshops)",
            "(goal byzantine-focus-military-pop >= 6)",
        ):
            self.assertIn(fragment, self.per)

    def test_every_production_feasibility_gate_has_provider_readiness(self):
        for rule in self._rules():
            if "(can-train " not in rule and "(can-train-with-escrow " not in rule:
                continue
            self.assertIn(
                "(up-train-site-ready c:",
                rule,
                "Every production admission must also require the concrete training provider-readiness fact.",
            )

    def test_deer_controller_tracks_id_distance_and_actually_retasks_food_workers(self):
        for fragment in (
            "(defconst byzantine-natural-food-deer-state",
            "(defconst byzantine-natural-food-deer-id",
            "(defconst byzantine-natural-food-deer-distance",
            "(up-find-resource c: deer-class c: 40)",
            "(up-get-object-data object-data-id byzantine-natural-food-deer-id)",
            "(up-set-target-by-id g: byzantine-natural-food-deer-id)",
            "(up-set-target-point byzantine-natural-food-deer-point)",
            "(up-find-local c: villager-class g: villager-count)",
            "(up-target-objects 1 action-default -1 -1)",
        ):
            self.assertIn(fragment, self.per)

        deer_start = self.per.index("; NATIVE NATURAL-FOOD DEER CONTROLLER")
        deer_end = self.per.index("; NATIVE FOOD RESOURCE SELECTOR", deer_start)
        deer_block = self.per[deer_start:deer_end]
        self.assertNotIn(
            "(up-request-hunters c: 1)",
            deer_block,
            "The new deer controller must not rely on the evidence-only hunter shortcut.",
        )

    def test_food_drop_selector_is_separate_from_mill_demand_lifecycle(self):
        block_start = self.per.index("; NATIVE FOOD RESOURCE SELECTOR")
        block_end = self.per.index(";---------------------------------------------------------------", block_start)
        block = self.per[block_start:block_end]
        self.assertIn(
            "(defconst byzantine-food-source-selector 745)",
            self.per,
        )
        for fragment in (
            "(goal byzantine-food-source-selector 0)",
            "(up-find-resource c: forage-bush-class c: 16)",
            "(up-find-resource c: deer-class c: 16)",
            "(set-strategic-number sn-preferred-mill-placement 0)",
            "(set-strategic-number sn-preferred-mill-placement 1)",
        ):
            self.assertIn(fragment, block)

        mill_rule = next(
            rule
            for rule in self._rules()
            if "(build mill)" in rule and "demand-economy-food-mill-feudal-berries" in rule
        )
        self.assertIn(
            "(goal byzantine-food-source-selector 0)",
            mill_rule,
        )

    def test_native_hunt_and_mill_strategic_number_constants_are_unique(self):
        for name in (
            "sn-maximum-hunt-drop-distance",
            "sn-preferred-mill-placement",
            "byzantine-target-player-lock",
            "byzantine-food-source-selector",
        ):
            self.assertEqual(
                self.per.count(f"(defconst {name} "),
                1,
                f"{name} must have exactly one definition.",
            )

    def test_escrow_boundary_remains_explicitly_fail_closed(self):
        self.assertIn("(can-research-with-escrow", self.per)
        self.assertIn("(release-escrow ", self.per)
        self.assertNotIn("(up-modify-escrow ", self.per)
        self.assertNotIn("(up-release-escrow ", self.per)
        self.assertNotIn("(set-escrow-percentage ", self.per)


if __name__ == "__main__":
    unittest.main()