import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PER_PATH = REPO_ROOT / "Byzantine.per"


class ByzantinePlaytestOpeningTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.per = PER_PATH.read_text(encoding="utf-8")

    def _rule_block(self, marker):
        start = self.per.index(marker)
        rule_start = self.per.find("(defrule", start + len(marker))
        if rule_start < 0:
            return self.per[start:]
        next_rule = self.per.find("(defrule", rule_start + len("(defrule"))
        return self.per[start:] if next_rule < 0 else self.per[start:next_rule]

    def _section(self, marker, end_marker):
        start = self.per.index(marker)
        end = self.per.index(end_marker, start)
        return self.per[start:end]

    def test_safe_arabia_opening_selects_defensive_standard(self):
        block = self._rule_block("; Native control rule: opening-selector-defensive-standard-arabia")
        self.assertIn("(map-type arabia)", block)
        self.assertIn("(set-goal opening-plan 1)", block)

    def test_arena_opening_selects_fast_castle(self):
        block = self._rule_block("; Native control rule: opening-selector-fast-castle")
        self.assertIn("(map-type arena)", block)
        self.assertIn("(set-goal opening-plan 3)", block)

    def test_dark_age_does_not_spend_on_barracks_or_farms(self):
        barracks = self._rule_block("; Action issuance: economy-barracks-floor-1")
        self.assertIn("(current-age >= feudal-age)", barracks)

        farm4 = self._rule_block("; Action issuance: economy-farm-floor-feudal-4")
        farm8 = self._rule_block("; Action issuance: economy-farm-floor-feudal-8")
        self.assertIn("(current-age >= feudal-age)", farm4)
        self.assertIn("(current-age >= feudal-age)", farm8)
        self.assertIn("(unit-type-count-total villager >= 24)", farm8)
        self.assertIn("(food-amount < 800)", farm8)
        self.assertIn("(food-amount < 650)", farm4)

    def test_stone_is_not_an_opening_resource(self):
        self.assertNotIn(
            "(and (current-age >= feudal-age) (resource-found stone))",
            self.per,
        )
        self.assertIn(
            "(and (current-age >= castle-age) (and (stone-amount < 650) (resource-found stone)))",
            self.per,
        )

    def test_arena_fast_imperial_economy_mode_uses_posture_9(self):
        block = self._rule_block("; Native control rule: economy-controller-select-fast-imperial")
        self.assertIn("(map-type arena)", block)
        self.assertIn("(set-goal economy-posture 9)", block)
        writer = self._rule_block(
            "; Native control rule: economy-controller-write-fast_imperial-sn-gold-gatherer-percentage"
        )
        self.assertIn("(goal economy-posture 9)", writer)
        self.assertIn("(set-strategic-number sn-gold-gatherer-percentage 38)", writer)

    def test_castle_attack_ready_uses_assembled_backbone_not_fixed_monk_siege_package(self):
        block = self._rule_block("; ATTACK THRESHOLDS AND REINFORCEMENT")
        self.assertIn("(attack-soldier-count >= 8)", block)
        self.assertIn("(goal counter-package-infantry_pressure_castle 1)", block)
        self.assertIn("(unit-type-count-total knight-line >= 2)", block)
        self.assertNotIn("(unit-type-count-total monk >= bt-castle-monk-floor)", block)

    def test_castle_monastery_and_monk_keep_two_monk_relic_healing_baseline(self):
        monastery = self._rule_block("; Action issuance: castle-monastery-capability | ACTIVE -> ISSUED")
        monks = self._rule_block("; Action issuance: castle-monk-floor | ACTIVE -> ISSUED")
        relic = self._rule_block("; Acquisition: preserve one healer while one Monk handles relic collection.")

        self.assertIn("(current-age >= castle-age)", monastery)
        self.assertNotIn("(town-under-attack)", monastery)
        self.assertIn("(current-age >= castle-age)", monks)
        self.assertNotIn("(town-under-attack)", monks)
        self.assertNotIn("(unit-type-count-total monk < 4)", monks)
        self.assertIn("(unit-type-count-total monk < bt-castle-monk-floor)", monks)

        self.assertIn("(unit-type-count-total monk >= 2)", relic)
        self.assertIn("(up-find-local c: monk c: 1)", relic)
    def test_defensive_monk_expansion_is_four_not_unconditional(self):
        self.assertIn("(defconst bt-byzantine-defense-monk-floor 4)", self.per)
        block = self._rule_block("; Conditional four-Monk floor.")
        self.assertIn("(goal byzantine-monk-defense-state byzantine-monk-defense-active)", block)
        self.assertIn("(unit-type-count-total monk < bt-byzantine-defense-monk-floor)", block)
        self.assertNotIn("(set-goal demand-castle-monk-floor 1)", block)

    def test_premium_castle_demands_invalidate_when_infantry_pressure_clears(self):
        cat = self._rule_block(
            "; Strategic invalidation: Castle Cataphract demand is only persistent while infantry pressure is real."
        )
        var = self._rule_block(
            "; Strategic invalidation: Castle Varangian demand clears when infantry pressure clears."
        )
        self.assertIn("(goal demand-castle-cataphract-floor 1)", cat)
        self.assertIn("(not (players-unit-type-count any-enemy militia-line >= 5))", cat)
        self.assertIn("(goal demand-castle-varangian-guard-floor 1)", var)
        self.assertIn("(not (players-unit-type-count any-enemy militia-line >= 5))", var)

    def test_castle_attack_groups_are_enabled_for_boom(self):
        block = self._rule_block("; Native control rule: sn-mode-attack-groups-castle-008")
        self.assertIn("(goal strategy-posture 3)", block)
        self.assertIn("(goal strategy-posture 4)", block)



    def test_native_combat_meta_controls_are_explicitly_enabled(self):
        self.assertIn("(defconst sn-attack-intelligence 103)", self.per)
        self.assertIn("(defconst sn-enable-offensive-priority 254)", self.per)
        self.assertIn("(defconst sn-local-targeting-mode 286)", self.per)
        self.assertIn("(defconst sn-zero-priority-distance 34)", self.per)
        self.assertIn("(set-strategic-number sn-attack-intelligence 1)", self.per)
        self.assertIn("(set-strategic-number sn-local-targeting-mode 1)", self.per)
        self.assertIn("(set-strategic-number sn-enable-offensive-priority 1)", self.per)
        self.assertIn("(set-strategic-number sn-zero-priority-distance 255)", self.per)

    def test_castle_muster_holding_loss_witness_matches_mangonel_admission_group(self):
        block = self._rule_block(
            "; Holding remains a world-state witness, never a timer-only state."
        )
        self.assertIn(
            "(up-group-size c: byzantine-siege-muster-mangonel-group >= bt-castle-mangonel-floor)",
            block,
        )
        self.assertNotIn(
            "(up-group-size c: byzantine-siege-muster-trebuchet-group >= bt-castle-mangonel-floor)",
            block,
        )

    def test_imperial_attack_ready_uses_any_sufficient_siege_anchor(self):
        start = self.per.index(
            "(defrule\n"
            "    (current-age >= imperial-age)\n"
            "    (goal byzantine-army-plan-phase 2)\n"
            "    (goal byzantine-army-attack-ready 0)"
        )
        end = self.per.index("\n\n(defrule", start)
        block = self.per[start:end]
        self.assertIn("(attack-soldier-count >= 12)", block)
        self.assertIn("(unit-type-count-total 359 >= bt-imperial-halberdier-floor)", block)
        self.assertIn("(unit-type-count-total trebuchet >= 1)", block)
        self.assertIn("(unit-type-count-total bombard-cannon >= 1)", block)
        self.assertIn("(unit-type-count-total battering-ram-line >= 1)", block)
        self.assertIn("(unit-type-count-total mangonel-line >= 2)", block)
        self.assertNotIn(
            "(unit-type-count-total trebuchet >= bt-imperial-trebuchet-target)",
            block,
        )

    def test_counter_package_selection_uses_focus_player_context(self):
        start = self.per.index(
            "; Native control rule: counter-package-selection-reset-000"
        )
        end = self.per.index(
            ";---------------------------------------------------------------",
            start,
        )
        block = self.per[start:end]
        for fragment in (
            "(players-unit-type-count target-player militia-line >= 5)",
            "(players-unit-type-count target-player knight >= 3)",
            "(players-unit-type-count target-player knight >= 1)",
            "(players-unit-type-count focus-player scout-cavalry-line >= 3)",
            "(players-unit-type-count target-player archer-line >= 3)",
            "(players-unit-type-count target-player mangonel-line >= 2)",
        ):
            self.assertIn(fragment, block)

    def test_fast_castle_economy_keeps_wood_and_gold_funded(self):
        block = self.per[
            self.per.index("; Native control rule: economy-controller-write-fast_castle-sn-food-gatherer-percentage"):
            self.per.index("; Native control rule: economy-controller-write-water_economy-sn-food-gatherer-percentage")
        ]
        self.assertIn("(set-strategic-number sn-food-gatherer-percentage 50)", block)
        self.assertIn("(set-strategic-number sn-wood-gatherer-percentage 25)", block)
        self.assertIn("(set-strategic-number sn-gold-gatherer-percentage 25)", block)

    def test_second_mill_is_a_feudal_forage_transition(self):
        block = self._section(
            "; FEUDAL SECOND MILL: FORAGE / BERRY TRANSITION",
            "; Pending diagnostics: economy-market-floor-1",
        )
        self.assertIn("(current-age == feudal-age)", block)
        self.assertIn("(set-strategic-number sn-preferred-mill-placement 0)", block)
        self.assertIn("(build mill)", block)
        self.assertIn("(up-pending-placement c: 68)", block)

    def test_feudal_eco_research_uses_feudal_guard_and_castle_bank_floor(self):
        expected = {
            "double-bit-axe": ("900", "250"),
            "horse-collar": ("900", "250"),
            "wheelbarrow": ("1000", "250"),
            "gold-mining": ("900", "250"),
        }
        for tech, (food_floor, gold_floor) in expected.items():
            block = self._rule_block(f"; Action issuance: research-{tech} | ACTIVE -> ISSUED")
            self.assertIn("(current-age >= feudal-age)", block)
            self.assertNotIn("(current-age >= castle-age)", block)
            self.assertIn(f"(food-amount >= {food_floor})", block)
            self.assertIn(f"(gold-amount >= {gold_floor})", block)


if __name__ == "__main__":
    unittest.main()
