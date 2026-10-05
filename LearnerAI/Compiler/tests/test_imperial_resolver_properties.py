from __future__ import annotations

import random
import unittest
from dataclasses import replace

from Compiler.ir.imperial_resolver import (
    ImperialBand,
    ImperialReason,
    ImperialResolver,
    ImperialResolverInput,
)


FLOOR_THRESHOLDS = {
    "halberdiers": 18,
    "elite_skirmishers": 18,
    "hussars": 12,
}

FLOOR_RECOVERY_THRESHOLDS = {
    "food": 2000,
    "wood": 1700,
    "gold": 1600,
}

OPEN_ENTRY_THRESHOLDS = {
    "food": 2400,
    "wood": 2000,
    "gold": 2000,
}

OPEN_EXIT_THRESHOLDS = {
    "food": 1800,
    "wood": 1500,
}

TRASH_ENTRY_GOLD = 800
TRASH_EXIT_GOLD = 1800

TRASH_RESOURCE_THRESHOLDS = {
    "food": 2400,
    "wood": 2200,
}

FORTIFIED_RESOURCE_THRESHOLDS = {
    "food": 2400,
    "wood": 2400,
    "gold": 2600,
    "siege": 2,
}

TIMER_THRESHOLDS = {
    "floor_recovery": 30,
    "open_entry": 20,
    "open_min_dwell": 60,
    "fortified_entry": 15,
    "fortified_min_dwell": 45,
    "fortified_clear": 20,
    "trash_entry": 30,
    "trash_min_dwell": 90,
    "gold_recovery": 30,
    "economic_collapse": 30,
}

COOLDOWN_THRESHOLDS = {
    ImperialBand.OPEN_FIELD: 30,
    ImperialBand.FORTIFIED_PUSH: 30,
    ImperialBand.GOLD_STARVED_TRASH: 45,
}


def around(center: int, *, radius: int = 4, samples: int = 24) -> tuple[int, ...]:
    rng = random.Random((center << 8) ^ radius ^ samples)
    generated = {max(0, center + delta) for delta in range(-radius, radius + 1)}
    while len(generated) < samples:
        generated.add(max(0, center + rng.randint(-250, 250)))
    return tuple(sorted(generated))


class ImperialResolverPropertyTests(unittest.TestCase):
    @staticmethod
    def base() -> ImperialResolverInput:
        return ImperialResolverInput(
            current=ImperialBand.STANDING_FLOOR,
            halberdiers=30,
            elite_skirmishers=30,
            hussars=20,
            food=4000,
            wood=4000,
            gold=4000,
            siege=6,
            offensive_objective=True,
            fortification_threat=False,
            siege_approach="normal",
            enemy_field_army=24,
            fortified_objective_requires_siege=False,
        )

    @staticmethod
    def resolve(value: ImperialResolverInput, **timers):
        return ImperialResolver().resolve(value, **timers)

    def test_property_floor_thresholds_are_inclusive(self):
        base = self.base()
        for field, threshold in FLOOR_THRESHOLDS.items():
            for value in around(threshold):
                with self.subTest(field=field, value=value):
                    case = replace(base, **{field: value})
                    decision = self.resolve(
                        case,
                        dwell_seconds=30,
                        guard_seconds=20,
                        rearm_seconds=0,
                    )
                    if value < threshold:
                        self.assertEqual(
                            decision.destination,
                            ImperialBand.STANDING_FLOOR,
                        )
                        self.assertEqual(
                            decision.reason,
                            ImperialReason.FLOOR_BREAK,
                        )
                    else:
                        self.assertNotEqual(
                            decision.reason,
                            ImperialReason.FLOOR_BREAK,
                        )

    def test_property_floor_recovery_resources_are_inclusive(self):
        base = self.base()
        for field, threshold in FLOOR_RECOVERY_THRESHOLDS.items():
            for value in around(threshold):
                with self.subTest(field=field, value=value):
                    case = replace(
                        base,
                        **{field: value},
                    )
                    decision = self.resolve(
                        case,
                        dwell_seconds=30,
                        guard_seconds=20,
                        rearm_seconds=0,
                    )
                    self.assertEqual(
                        ImperialResolver.floor_recovered(case),
                        value >= threshold,
                    )


    def test_open_and_trash_posture_do_not_require_objective_claim(self):
        base = self.base()
        without_claim = replace(base, offensive_objective=False)
        self.assertTrue(ImperialResolver.open_field_eligible(without_claim))
        trash = replace(
            without_claim,
            gold=800,
            food=3000,
            wood=3000,
            current=ImperialBand.GOLD_STARVED_TRASH,
        )
        self.assertTrue(ImperialResolver.gold_starved_eligible(trash))

    def test_property_open_entry_requires_offensive_objective(self):
        base = self.base()
        without_objective = replace(base, offensive_objective=False)
        decision = self.resolve(
            without_objective,
            dwell_seconds=30,
            guard_seconds=20,
            rearm_seconds=0,
        )
        self.assertNotEqual(
            decision.destination,
            ImperialBand.OPEN_FIELD,
        )

    def test_property_open_entry_thresholds_are_inclusive(self):
        base = self.base()
        for field, threshold in OPEN_ENTRY_THRESHOLDS.items():
            for value in around(threshold):
                with self.subTest(field=field, value=value):
                    case = replace(
                        base,
                        **{field: value},
                    )
                    decision = self.resolve(
                        case,
                        dwell_seconds=30,
                        guard_seconds=20,
                        rearm_seconds=0,
                    )
                    if value < threshold:
                        self.assertNotEqual(
                            decision.destination,
                            ImperialBand.OPEN_FIELD,
                        )
                    else:
                        self.assertEqual(
                            decision.destination,
                            ImperialBand.OPEN_FIELD,
                        )

    def test_property_open_exit_thresholds_are_exclusive(self):
        base = replace(
            self.base(),
            current=ImperialBand.OPEN_FIELD,
        )
        for field, threshold in OPEN_EXIT_THRESHOLDS.items():
            for value in around(threshold):
                with self.subTest(field=field, value=value):
                    case = replace(base, **{field: value})
                    decision = self.resolve(
                        case,
                        dwell_seconds=60,
                        guard_seconds=30,
                        rearm_seconds=0,
                    )
                    if value < threshold:
                        self.assertEqual(
                            decision.destination,
                            ImperialBand.STANDING_FLOOR,
                        )
                        self.assertEqual(
                            decision.reason,
                            ImperialReason.ECONOMIC_COLLAPSE,
                        )
                    else:
                        self.assertEqual(
                            decision.destination,
                            ImperialBand.OPEN_FIELD,
                        )

    def test_property_trash_gold_entry_is_inclusive(self):
        base = replace(
            self.base(),
            current=ImperialBand.OPEN_FIELD,
        )
        for value in around(TRASH_ENTRY_GOLD):
            with self.subTest(gold=value):
                case = replace(base, gold=value)
                decision = self.resolve(
                    case,
                    dwell_seconds=60,
                    guard_seconds=30,
                    rearm_seconds=0,
                )
                if value <= TRASH_ENTRY_GOLD:
                    self.assertEqual(
                        decision.destination,
                        ImperialBand.GOLD_STARVED_TRASH,
                    )
                    self.assertEqual(
                        decision.reason,
                        ImperialReason.GOLD_STARVED,
                    )
                else:
                    self.assertEqual(
                        decision.destination,
                        ImperialBand.OPEN_FIELD,
                    )

    def test_property_trash_gold_exit_is_inclusive(self):
        base = replace(
            self.base(),
            current=ImperialBand.GOLD_STARVED_TRASH,
        )
        for value in around(TRASH_EXIT_GOLD):
            with self.subTest(gold=value):
                case = replace(base, gold=value)
                decision = self.resolve(
                    case,
                    dwell_seconds=90,
                    guard_seconds=30,
                    rearm_seconds=0,
                )
                if value >= TRASH_EXIT_GOLD:
                    self.assertEqual(
                        decision.destination,
                        ImperialBand.OPEN_FIELD,
                    )
                    self.assertEqual(
                        decision.reason,
                        ImperialReason.GOLD_RECOVERY,
                    )
                else:
                    self.assertEqual(
                        decision.destination,
                        ImperialBand.GOLD_STARVED_TRASH,
                    )

    def test_property_trash_resource_thresholds_are_inclusive(self):
        base = replace(
            self.base(),
            current=ImperialBand.STANDING_FLOOR,
            gold=600,
        )
        for field, threshold in TRASH_RESOURCE_THRESHOLDS.items():
            for value in around(threshold):
                with self.subTest(field=field, value=value):
                    case = replace(base, **{field: value})
                    decision = self.resolve(
                        case,
                        dwell_seconds=30,
                        guard_seconds=30,
                        rearm_seconds=0,
                    )
                    if value < threshold:
                        self.assertNotEqual(
                            decision.destination,
                            ImperialBand.GOLD_STARVED_TRASH,
                        )
                    else:
                        self.assertEqual(
                            decision.destination,
                            ImperialBand.GOLD_STARVED_TRASH,
                        )

    def test_property_fortified_resource_thresholds_are_conjunctive_and_inclusive(self):
        base = replace(
            self.base(),
            current=ImperialBand.OPEN_FIELD,
            fortification_threat=True,
            siege_approach="fortified",
            offensive_objective=True,
            food=2400,
            wood=2400,
            gold=2600,
            siege=2,
        )
        for field, threshold in FORTIFIED_RESOURCE_THRESHOLDS.items():
            for value in around(threshold):
                with self.subTest(field=field, value=value):
                    case = replace(base, **{field: value})
                    decision = self.resolve(
                        case,
                        dwell_seconds=0,
                        guard_seconds=15,
                        rearm_seconds=0,
                    )
                    if value < threshold:
                        self.assertNotEqual(
                            decision.destination,
                            ImperialBand.FORTIFIED_PUSH,
                        )
                    else:
                        self.assertEqual(
                            decision.destination,
                            ImperialBand.FORTIFIED_PUSH,
                        )

    def test_property_timer_expiry_is_exact(self):
        cases = (
            (
                "floor_recovery",
                ImperialBand.STANDING_FLOOR,
                30,
                20,
                ImperialBand.OPEN_FIELD,
            ),
            (
                "open_entry",
                ImperialBand.STANDING_FLOOR,
                30,
                20,
                ImperialBand.OPEN_FIELD,
            ),
            (
                "fortified_entry",
                ImperialBand.OPEN_FIELD,
                60,
                15,
                ImperialBand.FORTIFIED_PUSH,
            ),
            (
                "fortified_clear",
                ImperialBand.FORTIFIED_PUSH,
                45,
                20,
                ImperialBand.OPEN_FIELD,
            ),
            (
                "trash_entry",
                ImperialBand.OPEN_FIELD,
                60,
                30,
                ImperialBand.GOLD_STARVED_TRASH,
            ),
            (
                "gold_recovery",
                ImperialBand.GOLD_STARVED_TRASH,
                90,
                30,
                ImperialBand.OPEN_FIELD,
            ),
            (
                "economic_collapse",
                ImperialBand.OPEN_FIELD,
                60,
                30,
                ImperialBand.STANDING_FLOOR,
            ),
        )

        for name, current, dwell, guard, expected in cases:
            with self.subTest(timer=name):
                case = replace(self.base(), current=current)
                if name == "fortified_entry":
                    case = replace(
                        case,
                        fortification_threat=True,
                        siege_approach="fortified",
                        food=2400,
                        wood=2400,
                        gold=2600,
                        siege=2,
                    )
                elif name == "fortified_clear":
                    case = replace(
                        case,
                        fortification_threat=False,
                        siege_approach="normal",
                        current=ImperialBand.FORTIFIED_PUSH,
                    )
                elif name == "trash_entry":
                    case = replace(
                        case,
                        gold=800,
                        current=ImperialBand.OPEN_FIELD,
                    )
                elif name == "gold_recovery":
                    case = replace(
                        case,
                        gold=1800,
                        current=ImperialBand.GOLD_STARVED_TRASH,
                    )
                elif name == "economic_collapse":
                    case = replace(
                        case,
                        food=1799,
                        current=ImperialBand.OPEN_FIELD,
                    )

                below = self.resolve(
                    case,
                    dwell_seconds=max(0, dwell - 1),
                    guard_seconds=max(0, guard - 1),
                    rearm_seconds=0,
                )
                exact = self.resolve(
                    case,
                    dwell_seconds=dwell,
                    guard_seconds=guard,
                    rearm_seconds=0,
                )

                self.assertNotEqual(
                    below.destination,
                    expected,
                    msg=f"{name}: transition occurred before exact timer boundary",
                )
                self.assertEqual(
                    exact.destination,
                    expected,
                    msg=f"{name}: transition failed at exact timer boundary",
                )

    def test_property_cooldown_expiry_is_exact(self):
        for band, threshold in COOLDOWN_THRESHOLDS.items():
            with self.subTest(band=band):
                if band == ImperialBand.OPEN_FIELD:
                    current = ImperialBand.STANDING_FLOOR
                    case = self.base()
                    guard = 20
                    dwell = 30
                elif band == ImperialBand.FORTIFIED_PUSH:
                    current = ImperialBand.OPEN_FIELD
                    case = replace(
                        self.base(),
                        current=current,
                        fortification_threat=True,
                        siege_approach="fortified",
                        food=2400,
                        wood=2400,
                        gold=2600,
                        siege=2,
                    )
                    guard = 15
                    dwell = 60
                else:
                    current = ImperialBand.OPEN_FIELD
                    case = replace(
                        self.base(),
                        current=current,
                        gold=800,
                    )
                    guard = 30
                    dwell = 60

                blocked = self.resolve(
                    case,
                    dwell_seconds=dwell,
                    guard_seconds=guard,
                    rearm_seconds=threshold - 1,
                    rearm_band=band,
                )
                clear = self.resolve(
                    case,
                    dwell_seconds=dwell,
                    guard_seconds=guard,
                    rearm_seconds=threshold,
                    rearm_band=band,
                )

                self.assertNotEqual(
                    blocked.destination,
                    band,
                    msg=f"{band}: cooldown admitted target too early",
                )
                self.assertEqual(
                    clear.destination,
                    band,
                    msg=f"{band}: cooldown did not clear at exact boundary",
                )

    def test_property_floor_break_precedes_every_other_transition(self):
        scenarios = (
            ("fortified", ImperialBand.OPEN_FIELD),
            ("economic", ImperialBand.OPEN_FIELD),
            ("trash", ImperialBand.OPEN_FIELD),
            ("normal", ImperialBand.STANDING_FLOOR),
        )

        for scenario, current in scenarios:
            for field, threshold in FLOOR_THRESHOLDS.items():
                for value in (threshold - 1,):
                    with self.subTest(
                        scenario=scenario,
                        field=field,
                        value=value,
                    ):
                        case = replace(
                            self.base(),
                            current=current,
                            **{field: value},
                        )

                        if scenario == "fortified":
                            case = replace(
                                case,
                                fortification_threat=True,
                                siege_approach="fortified",
                                food=2400,
                                wood=2400,
                                gold=2600,
                                siege=2,
                            )
                        elif scenario == "economic":
                            case = replace(
                                case,
                                food=1700,
                                wood=3000,
                            )
                        elif scenario == "trash":
                            case = replace(
                                case,
                                gold=800,
                            )

                        decision = self.resolve(
                            case,
                            dwell_seconds=0,
                            guard_seconds=60,
                            rearm_seconds=0,
                        )

                        self.assertEqual(
                            decision.destination,
                            ImperialBand.STANDING_FLOOR,
                        )
                        self.assertEqual(
                            decision.reason,
                            ImperialReason.FLOOR_BREAK,
                        )


if __name__ == "__main__":
    unittest.main()
