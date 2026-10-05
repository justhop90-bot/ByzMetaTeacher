from __future__ import annotations

import random
import unittest
from dataclasses import replace

from Compiler.ir.imperial_military import (
    ImperialMilitaryBand,
    ImperialMilitaryReason,
    ImperialMilitaryInput,
    default_imperial_military_plan,
    resolve_imperial_military,
)


def around(center: int, radius: int = 3, samples: int = 12) -> tuple[int, ...]:
    rng = random.Random(center * 7919 + radius * 104729 + samples)
    values = {max(0, center + delta) for delta in range(-radius, radius + 1)}
    while len(values) < samples:
        values.add(max(0, center + rng.randint(-64, 64)))
    return tuple(sorted(values))


class ImperialMilitaryPropertyTests(unittest.TestCase):
    PLAN = default_imperial_military_plan()

    @staticmethod
    def base(**overrides) -> ImperialMilitaryInput:
        values = dict(
            current=ImperialMilitaryBand.OPEN_FIELD,
            halberdiers=30,
            elite_skirmishers=30,
            hussars=20,
            food=4000,
            wood=4000,
            gold=4000,
            siege=6,
            objective_claimed=True,
            fortification_threat=False,
            siege_approach_fortified=False,
            dwell_seconds=90,
            candidate_band=None,
            guard_seconds=0,
            rearm_band=None,
            rearm_seconds=0,
            economic_collapse_seconds=0,
            fortified_clear_seconds=0,
            gold_recovery_seconds=0,
        )
        values.update(overrides)
        return ImperialMilitaryInput(**values)

    def test_floor_units_are_strictly_below_at_n_minus_one_and_safe_at_n(self):
        for field, threshold in (
            ("halberdiers", 18),
            ("elite_skirmishers", 18),
            ("hussars", 12),
        ):
            for value in around(threshold):
                with self.subTest(field=field, value=value):
                    case = self.base(**{field: value})
                    decision = resolve_imperial_military(case)
                    if value < threshold:
                        self.assertEqual(
                            decision.destination,
                            ImperialMilitaryBand.STANDING_FLOOR,
                        )
                        self.assertEqual(
                            decision.reason,
                            ImperialMilitaryReason.FLOOR_BREAK,
                        )
                    else:
                        self.assertNotEqual(
                            decision.reason,
                            ImperialMilitaryReason.FLOOR_BREAK,
                        )

    def test_open_entry_resource_cutoffs_are_inclusive(self):
        cutoffs = (("food", 2400), ("wood", 2000), ("gold", 2000))
        for field, threshold in cutoffs:
            for value in around(threshold):
                with self.subTest(field=field, value=value):
                    case = self.base(
                        current=ImperialMilitaryBand.STANDING_FLOOR,
                        dwell_seconds=30,
                        candidate_band=ImperialMilitaryBand.OPEN_FIELD,
                        guard_seconds=20,
                        **{field: value},
                    )
                    # Keep the other Open entry resources safely above cutoff.
                    for other, safe in (("food", 3000), ("wood", 3000), ("gold", 3000)):
                        if other != field:
                            case = replace(case, **{other: safe})
                    decision = resolve_imperial_military(case)
                    if value >= threshold:
                        self.assertEqual(
                            decision.destination,
                            ImperialMilitaryBand.OPEN_FIELD,
                        )
                    else:
                        self.assertNotEqual(
                            decision.destination,
                            ImperialMilitaryBand.OPEN_FIELD,
                        )

    def test_open_economic_exit_is_strict(self):
        for field, threshold in (("food", 1800), ("wood", 1500)):
            for value in around(threshold):
                with self.subTest(field=field, value=value):
                    case = self.base(
                        current=ImperialMilitaryBand.OPEN_FIELD,
                        dwell_seconds=60,
                        economic_collapse_seconds=30,
                        **{field: value},
                    )
                    decision = resolve_imperial_military(case)
                    if value < threshold:
                        self.assertEqual(
                            decision.destination,
                            ImperialMilitaryBand.STANDING_FLOOR,
                        )
                        self.assertEqual(
                            decision.reason,
                            ImperialMilitaryReason.ECONOMIC_COLLAPSE,
                        )
                    else:
                        self.assertEqual(
                            decision.destination,
                            ImperialMilitaryBand.OPEN_FIELD,
                        )

    def test_trash_gold_entry_and_exit_use_hysteresis_edges(self):
        for value in around(800):
            with self.subTest(entry_gold=value):
                case = self.base(
                    current=ImperialMilitaryBand.OPEN_FIELD,
                    gold=value,
                    dwell_seconds=60,
                    candidate_band=ImperialMilitaryBand.GOLD_STARVED_TRASH,
                    guard_seconds=30,
                )
                decision = resolve_imperial_military(case)
                if value <= 800:
                    self.assertEqual(
                        decision.destination,
                        ImperialMilitaryBand.GOLD_STARVED_TRASH,
                    )
                    self.assertEqual(
                        decision.reason,
                        ImperialMilitaryReason.GOLD_STARVED,
                    )
                else:
                    self.assertNotEqual(
                        decision.destination,
                        ImperialMilitaryBand.GOLD_STARVED_TRASH,
                    )

        for value in around(1800):
            with self.subTest(exit_gold=value):
                case = self.base(
                    current=ImperialMilitaryBand.GOLD_STARVED_TRASH,
                    gold=value,
                    dwell_seconds=90,
                    candidate_band=ImperialMilitaryBand.OPEN_FIELD,
                    guard_seconds=30,
                    gold_recovery_seconds=30,
                )
                decision = resolve_imperial_military(case)
                if value >= 1800:
                    self.assertEqual(
                        decision.destination,
                        ImperialMilitaryBand.OPEN_FIELD,
                    )
                    self.assertEqual(
                        decision.reason,
                        ImperialMilitaryReason.GOLD_RECOVERY,
                    )
                else:
                    self.assertEqual(
                        decision.destination,
                        ImperialMilitaryBand.GOLD_STARVED_TRASH,
                    )

    def test_fortified_resources_are_all_inclusive_and_conjunctive(self):
        for field, threshold in (
            ("food", 2400),
            ("wood", 2400),
            ("gold", 2600),
            ("siege", 2),
        ):
            for value in around(threshold):
                with self.subTest(field=field, value=value):
                    case = self.base(
                        current=ImperialMilitaryBand.OPEN_FIELD,
                        fortification_threat=True,
                        siege_approach_fortified=True,
                        food=2400,
                        wood=2400,
                        gold=2600,
                        siege=2,
                        candidate_band=ImperialMilitaryBand.FORTIFIED_PUSH,
                        guard_seconds=15,
                        dwell_seconds=60,
                        **{field: value},
                    )
                    decision = resolve_imperial_military(case)
                    if value >= threshold:
                        self.assertEqual(
                            decision.destination,
                            ImperialMilitaryBand.FORTIFIED_PUSH,
                        )
                    else:
                        self.assertNotEqual(
                            decision.destination,
                            ImperialMilitaryBand.FORTIFIED_PUSH,
                        )

    def test_timer_boundaries_are_exact(self):
        cases = (
            (ImperialMilitaryBand.OPEN_FIELD, "open", 20, 60),
            (ImperialMilitaryBand.OPEN_FIELD, "trash", 30, 60),
            (ImperialMilitaryBand.GOLD_STARVED_TRASH, "gold", 30, 90),
            (ImperialMilitaryBand.FORTIFIED_PUSH, "clear", 20, 45),
        )
        for current, target, guard_boundary, dwell_boundary in cases:
            with self.subTest(current=current, target=target):
                if target == "open":
                    case = self.base(
                        current=ImperialMilitaryBand.STANDING_FLOOR,
                        dwell_seconds=dwell_boundary,
                        candidate_band=ImperialMilitaryBand.OPEN_FIELD,
                        guard_seconds=guard_boundary,
                    )
                    expected = ImperialMilitaryBand.OPEN_FIELD
                elif target == "trash":
                    case = self.base(
                        current=ImperialMilitaryBand.OPEN_FIELD,
                        gold=800,
                        dwell_seconds=dwell_boundary,
                        candidate_band=ImperialMilitaryBand.GOLD_STARVED_TRASH,
                        guard_seconds=guard_boundary,
                    )
                    expected = ImperialMilitaryBand.GOLD_STARVED_TRASH
                elif target == "gold":
                    case = self.base(
                        current=ImperialMilitaryBand.GOLD_STARVED_TRASH,
                        gold=1800,
                        dwell_seconds=dwell_boundary,
                        candidate_band=ImperialMilitaryBand.OPEN_FIELD,
                        guard_seconds=guard_boundary,
                        gold_recovery_seconds=guard_boundary,
                    )
                    expected = ImperialMilitaryBand.OPEN_FIELD
                else:
                    case = self.base(
                        current=ImperialMilitaryBand.FORTIFIED_PUSH,
                        fortification_threat=False,
                        siege_approach_fortified=False,
                        dwell_seconds=dwell_boundary,
                        candidate_band=ImperialMilitaryBand.OPEN_FIELD,
                        guard_seconds=guard_boundary,
                        fortified_clear_seconds=guard_boundary,
                    )
                    expected = ImperialMilitaryBand.OPEN_FIELD

                before = replace(case, guard_seconds=guard_boundary - 1)
                exact = replace(case, guard_seconds=guard_boundary)

                self.assertNotEqual(
                    resolve_imperial_military(before).destination,
                    expected,
                )
                self.assertEqual(
                    resolve_imperial_military(exact).destination,
                    expected,
                )

    def test_cooldown_boundaries_are_exact(self):
        scenarios = (
            (ImperialMilitaryBand.STANDING_FLOOR, ImperialMilitaryBand.OPEN_FIELD, 30),
            (ImperialMilitaryBand.OPEN_FIELD, ImperialMilitaryBand.GOLD_STARVED_TRASH, 45),
            (ImperialMilitaryBand.STANDING_FLOOR, ImperialMilitaryBand.FORTIFIED_PUSH, 30),
        )
        for source, destination, threshold in scenarios:
            with self.subTest(source=source, destination=destination):
                if destination is ImperialMilitaryBand.OPEN_FIELD:
                    case = self.base(
                        current=source,
                        dwell_seconds=30,
                        candidate_band=destination,
                        guard_seconds=20,
                        rearm_band=destination,
                    )
                elif destination is ImperialMilitaryBand.GOLD_STARVED_TRASH:
                    case = self.base(
                        current=source,
                        gold=800,
                        dwell_seconds=60,
                        candidate_band=destination,
                        guard_seconds=30,
                        rearm_band=destination,
                    )
                else:
                    case = self.base(
                        current=source,
                        fortification_threat=True,
                        siege_approach_fortified=True,
                        food=2400,
                        wood=2400,
                        gold=2600,
                        siege=2,
                        dwell_seconds=60,
                        candidate_band=destination,
                        guard_seconds=15,
                        rearm_band=destination,
                    )

                blocked = resolve_imperial_military(
                    replace(case, rearm_seconds=threshold - 1)
                )
                clear = resolve_imperial_military(
                    replace(case, rearm_seconds=threshold)
                )

                self.assertNotEqual(blocked.destination, destination)
                self.assertEqual(clear.destination, destination)

    def test_floor_break_precedes_fortified_economic_and_normal_conditions(self):
        for field, threshold in (
            ("halberdiers", 18),
            ("elite_skirmishers", 18),
            ("hussars", 12),
        ):
            case = self.base(
                current=ImperialMilitaryBand.OPEN_FIELD,
                fortification_threat=True,
                siege_approach_fortified=True,
                food=1700,
                wood=3000,
                gold=800,
                siege=6,
                candidate_band=ImperialMilitaryBand.FORTIFIED_PUSH,
                guard_seconds=60,
                economic_collapse_seconds=60,
                **{field: threshold - 1},
            )
            decision = resolve_imperial_military(case)
            self.assertEqual(
                decision.destination,
                ImperialMilitaryBand.STANDING_FLOOR,
            )
            self.assertEqual(
                decision.reason,
                ImperialMilitaryReason.FLOOR_BREAK,
            )


if __name__ == "__main__":
    unittest.main()
