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

    def _rules(self):
        return ["(defrule" + rule for rule in self.per.split("(defrule")[1:]]

    def _find_rule(self, *fragments):
        for rule in self._rules():
            if all(fragment in rule for fragment in fragments):
                return rule
        self.fail("No defrule matched fragments: " + repr(fragments))

    def test_standard_arabia_selector_owns_quiet_land_and_generic_fallback_excludes_arabia(self):
        standard = self._rule_block("; Native control rule: opening-selector-defensive-standard-arabia")
        fallback = self._rule_block("; Native control rule: opening-selector-fast-castle-standard-land")
        self.assertIn("(map-type arabia)", standard)
        self.assertIn("(set-goal opening-plan 1)", standard)
        self.assertIn("(not (map-type arabia))", fallback)

    def test_standard_arabia_can_escalate_once_on_real_dark_age_pressure(self):
        block = self._rule_block(
            "; Native control rule: opening-escalate-standard-arabia-to-counter-feudal"
        )
        self.assertIn("(goal opening-plan 1)", block)
        self.assertIn("(current-age == dark-age)", block)
        self.assertIn("(players-unit-type-count any-enemy militia-line >= 3)", block)
        self.assertIn("(players-unit-type-count any-enemy scout-cavalry-line >= 3)", block)
        self.assertIn("(players-unit-type-count any-enemy archer-line >= 3)", block)
        self.assertIn("(players-building-type-count any-enemy barracks >= 1)", block)
        self.assertIn("(players-military-population any-enemy >= 3)", block)
        self.assertIn("(set-goal opening-plan 2)", block)

    def test_standard_arabia_starts_with_first_wood_and_gold_camps_only(self):
        block = self._section(
            "; Demand initialization",
            "; Persistent TC2-complete state starts false",
        )
        self.assertIn("(set-goal demand-economy-lumber-camp-floor-1 1)", block)
        self.assertIn("(set-goal demand-economy-gold-camp-floor-1 1)", block)
        for fragment in (
            "(set-goal demand-economy-lumber-camp-floor-2 0)",
            "(set-goal demand-economy-wood-camp-floor-3 0)",
            "(set-goal demand-economy-gold-camp-floor-2 0)",
            "(set-goal demand-economy-gold-camp-floor-3 0)",
            "(set-goal demand-economy-stone-camp-floor-1 0)",
            "(set-goal demand-economy-food-mill-boom 0)",
            "(set-goal demand-economy-food-mill-feudal-berries 0)",
        ):
            self.assertIn(fragment, block)

    def test_standard_arabia_dark_age_prefers_gold_over_second_wood_after_12_villagers(self):
        wood = self._rule_block(
            "; Prepare a nearest-real-resource placement plan. Existing action-claim singleton"
        )
        self.assertIn(
            "(unit-type-count-total villager >= 12)",
            wood,
        )
        gold_start = self.per.index(
            "; Prepare a nearest-real-resource placement plan. Existing action-claim singleton"
        )
        gold = self.per[gold_start:self.per.index(
            "(defrule\n    (goal byzantine-resource-camp-state byzantine-resource-camp-state-acquire-origin)",
            gold_start,
        )]
        self.assertIn(
            "(goal opening-plan 1)", gold
        )
        self.assertIn(
            "(current-age == dark-age)", gold
        )
        self.assertIn(
            "(unit-type-count-total villager >= 12)", gold
        )

    def test_standard_arabia_feudal_sequence_uses_19_villagers_and_range_before_blacksmith(self):
        age = self._rule_block("; Action issuance: feudal-transition | ACTIVE -> ISSUED")
        self.assertIn("(unit-type-count-total villager >= 20)", age)
        self.assertIn("(goal opening-plan 1)", age)
        self.assertIn("(map-type arabia)", age)
        self.assertIn("(unit-type-count-total villager >= 19)", age)
        self.assertNotIn("(unit-type-count-total villager >= 21)", age)

        blacksmith = self._rule_block(
            "; Action issuance: feudal-infrastructure | ACTIVE -> ISSUED"
        )
        self.assertIn("(goal opening-plan 1)", blacksmith)
        self.assertIn("(map-type arabia)", blacksmith)
        self.assertIn("(building-type-count archery-range >= 1)", blacksmith)

    def test_standard_arabia_does_not_build_first_mill_in_dark_age(self):
        mill = self._find_rule(
            "(goal demand-economy-food-mill-boom 1)",
            "(build mill)",
        )
        self.assertIn("(not (map-type arabia))", mill)
        self.assertIn("(current-age >= feudal-age)", mill)

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

    def test_castle_recovery_loss_uses_selected_backbone_and_fortified_siege_only(self):
        common = (
            "(current-age == castle-age)",
            "(goal byzantine-army-attack-ready 2)",
            "(set-goal byzantine-siege-approach byzantine-siege-approach-recover)",
        )

        cataphract = self._find_rule(
            *common,
            "(goal counter-package-infantry_pressure_castle 1)",
            "(unit-type-count-total cataphract-line < bt-castle-cataphract-floor)",
        )
        self.assertNotIn("(unit-type-count-total monk < bt-castle-monk-floor)", cataphract)

        ranged_backbone = self._find_rule(
            *common,
            "(not (goal counter-package-infantry_pressure_castle 1))",
            "(not",
            "(unit-type-count-total knight-line >= 2)",
            "(unit-type-count-total skirmisher-line >= bt-castle-skirmisher-floor)",
        )
        self.assertNotIn("(unit-type-count-total monk < bt-castle-monk-floor)", ranged_backbone)

        siege = self._find_rule(
            *common,
            "(goal byzantine-siege-approach byzantine-siege-approach-fortified)",
            "(unit-type-count-total mangonel-line < bt-castle-mangonel-floor)",
        )
        self.assertNotIn("(unit-type-count-total monk < bt-castle-monk-floor)", siege)

    def test_castle_normal_attack_loss_does_not_use_monk_as_attack_backbone(self):
        cataphract = self._find_rule(
            "(current-age == castle-age)",
            "(goal byzantine-army-attack-ready 2)",
            "(goal byzantine-siege-approach byzantine-siege-approach-normal)",
            "(goal counter-package-infantry_pressure_castle 1)",
            "(set-goal byzantine-army-reinforcement 1)",
            "(unit-type-count-total cataphract-line < bt-castle-cataphract-floor)",
        )
        self.assertNotIn("(unit-type-count-total monk < bt-castle-monk-floor)", cataphract)

        backbone = self._find_rule(
            "(current-age == castle-age)",
            "(goal byzantine-army-attack-ready 2)",
            "(goal byzantine-siege-approach byzantine-siege-approach-normal)",
            "(not (goal counter-package-infantry_pressure_castle 1))",
            "(set-goal byzantine-army-reinforcement 1)",
            "(unit-type-count-total knight-line >= 2)",
        )
        self.assertIn(
            "(unit-type-count-total skirmisher-line >= bt-castle-skirmisher-floor)",
            backbone,
        )
        self.assertNotIn("(unit-type-count-total monk < bt-castle-monk-floor)", backbone)

    def test_castle_rearm_release_mirrors_backbone_and_fortified_siege_contract(self):
        block = self._find_rule(
            "(goal byzantine-army-reinforcement 1)",
            "(goal byzantine-army-reinforcement-target-validation 1)",
            "(goal byzantine-army-reinforcement-admission 1)",
            "(goal byzantine-target-player-lock 1)",
            "(current-age == castle-age)",
            "(set-goal byzantine-army-reinforcement 0)",
        )
        self.assertIn(
            "(goal counter-package-infantry_pressure_castle 1)",
            block,
        )
        self.assertIn(
            "(unit-type-count-total cataphract-line >= bt-castle-cataphract-floor)",
            block,
        )
        self.assertIn(
            "(not (goal counter-package-infantry_pressure_castle 1))",
            block,
        )
        self.assertIn("(unit-type-count-total knight-line >= 2)", block)
        self.assertIn(
            "(unit-type-count-total skirmisher-line >= bt-castle-skirmisher-floor)",
            block,
        )
        self.assertIn(
            "(not (goal byzantine-siege-approach byzantine-siege-approach-fortified))",
            block,
        )
        self.assertIn(
            "(unit-type-count-total mangonel-line >= bt-castle-mangonel-floor)",
            block,
        )
        self.assertNotIn(
            "(unit-type-count-total monk >= bt-castle-monk-floor)",
            block,
        )

    def test_imperial_fortified_package_loss_preserves_all_siege_approach_states(self):
        block = self._find_rule(
            "(current-age >= imperial-age)",
            "(goal byzantine-army-attack-ready 2)",
            "(set-goal byzantine-siege-approach byzantine-siege-approach-recover)",
            "(set-goal byzantine-siege-breach-witness 0)",
            "(unit-type-count-total 359 < bt-imperial-halberdier-floor)",
        )
        for state in (
            "byzantine-siege-approach-staging",
            "byzantine-siege-approach-escorted",
            "byzantine-siege-approach-breach",
            "byzantine-siege-approach-assault",
            "byzantine-siege-approach-recover",
        ):
            self.assertIn(
                f"(goal byzantine-siege-approach {state})",
                block,
            )

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
    def test_lost_relic_monk_recovery_has_one_shot_cooldown(self):
        recovery = self._rule_block("; Recovery: castle-monk-floor | LOST MONK -> ACTIVE")
        self.assertIn("(up-timer-status byzantine-monk-recovery-timer c:== timer-disabled)", recovery)
        self.assertIn("(enable-timer byzantine-monk-recovery-timer bt-byzantine-monk-recovery-seconds)", recovery)
        self.assertNotIn("timer-triggered)", recovery)
        self.assertIn("(defconst byzantine-monk-recovery-timer 5)", self.per)
        self.assertIn("(defconst bt-byzantine-monk-recovery-seconds 15)", self.per)
        self.assertIn(
            "; Recovery cooldown expiry: re-arm only after the short cadence window.",
            self.per,
        )

    def test_lost_relic_monk_recovers_only_to_two_monk_baseline(self):
        recovery = self._rule_block("; Recovery: castle-monk-floor | LOST MONK -> ACTIVE")
        self.assertIn("(current-age >= castle-age)", recovery)
        self.assertIn("(building-type-count-total monastery >= 1)", recovery)
        self.assertIn("(not (unit-type-count-total monk >= bt-castle-monk-floor))", recovery)
        self.assertIn("(set-goal demand-castle-monk-floor 1)", recovery)
        self.assertNotIn("demand-castle-monk-defense-floor", recovery)
        self.assertIn("(defconst bt-castle-monk-floor 2)", self.per)

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
        block = self._find_rule(
            "(current-age >= imperial-age)",
            "(goal byzantine-army-plan-phase 2)",
            "(goal byzantine-army-reinforcement 0)",
            "(goal byzantine-army-attack-ready 0)",
        )
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

    def test_reinforcement_cannot_bypass_admission_or_reuse_dropped_target_lock(self):
        all_rules = self._rules()
        attack_ready_writers = [
            rule for rule in all_rules
            if "set-goal byzantine-army-attack-ready 1" in rule
        ]
        self.assertEqual(len(attack_ready_writers), 8)

        normal_writers = [
            rule for rule in attack_ready_writers
            if "(goal byzantine-army-reinforcement 1)" not in rule
        ]
        rearm_writers = [
            rule for rule in attack_ready_writers
            if "(goal byzantine-army-reinforcement 1)" in rule
        ]

        self.assertEqual(len(normal_writers), 4)
        self.assertEqual(len(rearm_writers), 4)

        for rule in normal_writers:
            self.assertIn("(goal byzantine-army-reinforcement 0)", rule)

        for rule in rearm_writers:
            for fragment in (
                "(goal byzantine-army-reinforcement-target-validation 1)",
                "(goal byzantine-army-reinforcement-admission 1)",
                "(goal byzantine-target-player-lock 1)",
            ):
                self.assertIn(fragment, rule)

        target_drop_rules = [
            rule for rule in all_rules
            if "(set-goal byzantine-target-player-lock 0)" in rule
            and "(goal byzantine-target-player-lock 1)" in rule
        ]
        self.assertGreaterEqual(len(target_drop_rules), 1)
        for rule in target_drop_rules:
            self.assertIn(
                "(set-goal byzantine-army-reinforcement-target-validation 0)",
                rule,
            )
            self.assertIn(
                "(set-goal byzantine-army-reinforcement-admission 0)",
                rule,
            )

        reinforcement_entry_rules = [
            rule for rule in all_rules
            if "(set-goal byzantine-army-reinforcement 1)" in rule
            and "(set-goal byzantine-target-player-lock 0)" in rule
        ]
        self.assertGreaterEqual(len(reinforcement_entry_rules), 4)
        for rule in reinforcement_entry_rules:
            self.assertIn(
                "(set-goal byzantine-army-reinforcement-target-validation 0)",
                rule,
            )
            self.assertIn(
                "(set-goal byzantine-army-reinforcement-admission 0)",
                rule,
            )

    def test_reinforcement_rearm_requires_fresh_target_validation_and_opponent_admission(self):
        self.assertIn(
            "(defconst byzantine-army-reinforcement-target-validation 303)",
            self.per,
        )
        self.assertIn(
            "(defconst byzantine-army-reinforcement-admission 305)",
            self.per,
        )

        rearm_rules = [
            rule for rule in self._rules()
            if "(goal byzantine-army-reinforcement 1)" in rule
            and "set-goal byzantine-army-attack-ready 1" in rule
        ]
        self.assertEqual(len(rearm_rules), 4)

        for rule in rearm_rules:
            for fragment in (
                "(goal byzantine-army-reinforcement-target-validation 1)",
                "(goal byzantine-army-reinforcement-admission 1)",
                "(goal byzantine-target-player-lock 1)",
            ):
                self.assertIn(fragment, rule)

    def test_counter_arbitration_yields_focus_writers_after_target_lock(self):
        section = self._section(
            "; TARGET PLAYER + FOCUS PROFILE PLANE",
            "; NATIVE NATURAL-FOOD DEER CONTROLLER",
        )
        for fragment in (
            "(goal byzantine-target-player-lock 0)",
            "(up-compare-goal byzantine-focus-stables g:>= 2)",
            "(up-compare-goal byzantine-focus-ranges g:>= 2)",
            "(up-compare-goal byzantine-focus-siege-workshops g:>= 1)",
            "(goal byzantine-target-player-lock 1)",
            "(set-goal counter-package-mounted_pressure_castle 0)",
            "(set-goal counter-package-ranged_pressure_feudal 0)",
            "(set-goal counter-package-infantry_pressure_castle 0)",
            "(set-goal counter-package-siege_pressure_castle 0)",
            "(players-unit-type-count target-player knight >= 3)",
            "(players-unit-type-count target-player mangonel-line >= 2)",
            "(players-military-population target-player >= 6)",
        ):
            self.assertIn(fragment, section)

        for rule in section.split("(defrule")[1:]:
            if "(set-goal counter-package-" not in rule:
                continue
            action = rule.split("=>", 1)[-1]
            if "counter-package-" in action:
                self.assertIn(
                    "(goal byzantine-target-player-lock ",
                    rule,
                    "counter-package writers must declare lock ownership",
                )

    def test_imperial_composition_preserves_global_defense_and_locks_offense_to_target(self):
        section = self._section(
            "; IMPERIAL MILITARY COMPOSITION ARBITRATION",
            "; Pending diagnostics: imperial-conversion",
        )
        for fragment in (
            "(goal byzantine-target-player-lock 0)",
            "(players-unit-type-count any-enemy camel-rider-line >= 3)",
            "(players-unit-type-count any-enemy archer-line >= 4)",
            "(players-unit-type-count any-enemy cavalry-archer-line >= 4)",
            "(goal byzantine-target-player-lock 1)",
            "(players-unit-type-count target-player camel-rider-line >= 3)",
            "(players-unit-type-count target-player knight >= 3)",
            "(players-unit-type-count target-player archer-line >= 4)",
            "(players-unit-type-count target-player cavalry-archer-line >= 4)",
        ):
            self.assertIn(fragment, section)

        for rule in section.split("(defrule")[1:]:
            if "any-enemy" in rule and "set-goal byzantine-imperial-composition-posture" in rule:
                self.assertIn(
                    "(goal byzantine-target-player-lock 0)",
                    rule,
                    "global enemy composition may only write the defensive posture before offensive target lock",
                )

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