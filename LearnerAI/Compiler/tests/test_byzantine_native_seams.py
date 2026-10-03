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
        for fragment in (
            "(set-strategic-number sn-target-evaluation-siege-weapon 50)",
            "(set-strategic-number sn-target-evaluation-damage-capability 20)",
            "(set-strategic-number sn-target-evaluation-time-kill-ratio 50)",
            "(set-strategic-number sn-target-evaluation-randomness 0)",
            "(set-strategic-number sn-enable-offensive-priority 1)",
            "(up-set-offense-priority c: castle c: 100)",
            "(up-set-offense-priority c: keep c: 90)",
            "(up-set-offense-priority c: bombard-tower c: 85)",
            "(up-set-offense-priority c: siege-workshop c: 70)",
            "(up-set-defense-priority c: castle c: 5000)",
            "(up-set-defense-priority c: keep c: 5000)",
        ):
            self.assertIn(fragment, self.per)

    def test_target_player_plane_is_distinct_from_focus_player(self):
        self.assertIn("(defconst sn-target-player-number 249)", self.per)
        self.assertIn("(set-strategic-number sn-target-player-number 0)", self.per)
        self.assertIn("(up-modify-sn sn-target-player-number s:= sn-focus-player-number)", self.per)
        self.assertIn("(players-unit-type-count target-player knight >= 3)", self.per)
        self.assertIn("(players-unit-type-count target-player mangonel-line >= 2)", self.per)

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

    def test_deer_controller_tracks_id_distance_and_lure_target(self):
        for fragment in (
            "(defconst byzantine-natural-food-deer-state",
            "(defconst byzantine-natural-food-deer-id",
            "(defconst byzantine-natural-food-deer-distance",
            "(up-find-resource c: deer-class c: 40)",
            "(up-get-object-data object-data-id byzantine-natural-food-current-deer)",
            "(up-set-target-by-id g: byzantine-natural-food-current-deer)",
            "(up-request-hunters c: 1)",
        ):
            self.assertIn(fragment, self.per)

    def test_food_drop_selector_distinguishes_foraged_and_hunted_food(self):
        block_start = self.per.index("; NATIVE FOOD RESOURCE SELECTOR")
        block_end = self.per.index(";---------------------------------------------------------------", block_start)
        block = self.per[block_start:block_end]
        self.assertIn("(up-find-resource c: forage-bush-class c: 16)", block)
        self.assertIn("(up-find-resource c: deer-class c: 16)", block)
        self.assertIn("(set-strategic-number sn-preferred-mill-placement 0)", block)
        self.assertIn("(set-strategic-number sn-preferred-mill-placement 1)", block)


if __name__ == "__main__":
    unittest.main()
