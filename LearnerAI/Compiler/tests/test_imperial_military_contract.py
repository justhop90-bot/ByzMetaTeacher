from __future__ import annotations

import unittest

from Compiler.ir.imperial_military import (
    ImperialMilitaryBand,
    ImperialMilitaryReason,
    ImperialMilitaryInput,
    default_imperial_military_plan,
    resolve_imperial_military,
)


class ImperialMilitaryContractTests(unittest.TestCase):
    def test_band_and_reason_values_are_stable(self):
        self.assertEqual(ImperialMilitaryBand.STANDING_FLOOR.value, 0)
        self.assertEqual(ImperialMilitaryBand.OPEN_FIELD.value, 1)
        self.assertEqual(ImperialMilitaryBand.FORTIFIED_PUSH.value, 2)
        self.assertEqual(ImperialMilitaryBand.GOLD_STARVED_TRASH.value, 3)

        self.assertEqual(ImperialMilitaryReason.NONE.value, 0)
        self.assertEqual(ImperialMilitaryReason.FLOOR_BREAK.value, 10)
        self.assertEqual(ImperialMilitaryReason.FORTIFIED_ESCALATION.value, 20)
        self.assertEqual(ImperialMilitaryReason.ECONOMIC_COLLAPSE.value, 30)
        self.assertEqual(ImperialMilitaryReason.GOLD_STARVED.value, 40)
        self.assertEqual(ImperialMilitaryReason.GOLD_RECOVERY.value, 50)
        self.assertEqual(ImperialMilitaryReason.OPEN_FIELD_ELIGIBLE.value, 60)
        self.assertEqual(ImperialMilitaryReason.FORTIFIED_CLEAR.value, 70)
        self.assertEqual(ImperialMilitaryReason.OBJECTIVE_LOST.value, 80)
        self.assertEqual(ImperialMilitaryReason.HOLD_DWELL.value, 90)
        self.assertEqual(ImperialMilitaryReason.HOLD_COOLDOWN.value, 91)

    def test_default_plan_freezes_thresholds_and_timers(self):
        plan = default_imperial_military_plan()
        self.assertEqual(plan.floor, (18, 18, 12))
        self.assertEqual(plan.open_entry_resources, (2400, 2000, 2000))
        self.assertEqual(plan.open_exit_resources, (1800, 1500))
        self.assertEqual(plan.fortified_resources, (2400, 2400, 2600))
        self.assertEqual(plan.trash_entry_gold, 800)
        self.assertEqual(plan.trash_exit_gold, 1800)
        self.assertEqual(plan.siege_entry_floor, 2)
        self.assertEqual(plan.minimum_dwell, {
            ImperialMilitaryBand.STANDING_FLOOR: 30,
            ImperialMilitaryBand.OPEN_FIELD: 60,
            ImperialMilitaryBand.FORTIFIED_PUSH: 45,
            ImperialMilitaryBand.GOLD_STARVED_TRASH: 90,
        })
        self.assertEqual(plan.guard_dwell, {
            ImperialMilitaryBand.OPEN_FIELD: 20,
            ImperialMilitaryBand.FORTIFIED_PUSH: 15,
            ImperialMilitaryBand.GOLD_STARVED_TRASH: 30,
        })
        self.assertEqual(plan.rearm, {
            ImperialMilitaryBand.OPEN_FIELD: 30,
            ImperialMilitaryBand.FORTIFIED_PUSH: 30,
            ImperialMilitaryBand.GOLD_STARVED_TRASH: 45,
        })

    def test_floor_break_precedes_all_other_conditions(self):
        decision = resolve_imperial_military(
            ImperialMilitaryInput(
                current=ImperialMilitaryBand.OPEN_FIELD,
                halberdiers=17,
                elite_skirmishers=18,
                hussars=12,
                food=1700,
                wood=3000,
                gold=600,
                siege=6,
                objective_claimed=True,
                fortification_threat=True,
                siege_approach_fortified=True,
                fortified_guard_seconds=30,
                gold_starved_seconds=30,
                economic_collapse_seconds=30,
                dwell_seconds=60,
                rearm_band=None,
                rearm_seconds=0,
            )
        )
        self.assertEqual(decision.destination, ImperialMilitaryBand.STANDING_FLOOR)
        self.assertEqual(decision.reason, ImperialMilitaryReason.FLOOR_BREAK)

    def test_fortified_escalation_beats_economic_collapse_when_executable(self):
        decision = resolve_imperial_military(
            ImperialMilitaryInput(
                current=ImperialMilitaryBand.OPEN_FIELD,
                halberdiers=24,
                elite_skirmishers=24,
                hussars=16,
                food=2400,
                wood=2400,
                gold=2600,
                siege=2,
                objective_claimed=True,
                fortification_threat=True,
                siege_approach_fortified=True,
                fortified_guard_seconds=15,
                economic_collapse_seconds=30,
                dwell_seconds=10,
                rearm_band=None,
                rearm_seconds=0,
            )
        )
        self.assertEqual(decision.destination, ImperialMilitaryBand.FORTIFIED_PUSH)
        self.assertEqual(decision.reason, ImperialMilitaryReason.FORTIFIED_ESCALATION)

    def test_exact_entry_guard_is_inclusive_and_timer_is_not_truth(self):
        base = dict(
            current=ImperialMilitaryBand.STANDING_FLOOR,
            halberdiers=18,
            elite_skirmishers=18,
            hussars=12,
            food=2400,
            wood=2000,
            gold=2000,
            siege=4,
            objective_claimed=True,
            fortification_threat=False,
            siege_approach_fortified=False,
            rearm_band=None,
            rearm_seconds=0,
            dwell_seconds=30,
        )
        before = resolve_imperial_military(
            ImperialMilitaryInput(**base, candidate_band=ImperialMilitaryBand.OPEN_FIELD, guard_seconds=19)
        )
        exact = resolve_imperial_military(
            ImperialMilitaryInput(**base, candidate_band=ImperialMilitaryBand.OPEN_FIELD, guard_seconds=20)
        )

        self.assertNotEqual(before.destination, ImperialMilitaryBand.OPEN_FIELD)
        self.assertEqual(exact.destination, ImperialMilitaryBand.OPEN_FIELD)

        stale = resolve_imperial_military(
            ImperialMilitaryInput(
                **base,
                candidate_band=ImperialMilitaryBand.OPEN_FIELD,
                guard_seconds=20,
                objective_claimed=False,
            )
        )
        self.assertNotEqual(stale.destination, ImperialMilitaryBand.OPEN_FIELD)

    def test_cooldown_blocks_before_exact_expiry(self):
        base = dict(
            current=ImperialMilitaryBand.STANDING_FLOOR,
            halberdiers=18,
            elite_skirmishers=18,
            hussars=12,
            food=2400,
            wood=2000,
            gold=2000,
            siege=4,
            objective_claimed=True,
            fortification_threat=False,
            siege_approach_fortified=False,
            candidate_band=ImperialMilitaryBand.OPEN_FIELD,
            guard_seconds=20,
            dwell_seconds=30,
            rearm_band=ImperialMilitaryBand.OPEN_FIELD,
        )
        blocked = resolve_imperial_military(
            ImperialMilitaryInput(**base, rearm_seconds=29)
        )
        clear = resolve_imperial_military(
            ImperialMilitaryInput(**base, rearm_seconds=30)
        )

        self.assertNotEqual(blocked.destination, ImperialMilitaryBand.OPEN_FIELD)
        self.assertEqual(clear.destination, ImperialMilitaryBand.OPEN_FIELD)


if __name__ == "__main__":
    unittest.main()
