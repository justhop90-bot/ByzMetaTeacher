from dataclasses import replace
import unittest

from LearnerAI.Compiler.ir.civ_profile import (
    ByzantineProfile,
    EffectiveCivData,
    resolve_effective_civ,
)
from LearnerAI.Compiler.ir.game_data import (
    Age,
    BuildingId,
    CoverageStatus,
    Prerequisite,
    PrerequisiteKind,
    ResourceCost,
    SelectorKind,
    UnitDef,
)
from LearnerAI.Compiler.ir.versioning import PatchId


class GameDataTests(unittest.TestCase):
    def test_byzantine_185872_resolves_current_factual_snapshot(self):
        data = resolve_effective_civ(ByzantineProfile.for_update_185872())

        self.assertIsInstance(data, EffectiveCivData)
        self.assertEqual(data.patch.update, "185872")
        self.assertEqual(data.civ_name, "Byzantines")
        self.assertIn(BuildingId(82), data.available_buildings)
        self.assertEqual(data.building(82).name, "Castle")
        self.assertEqual(data.unit(358).name, "Pikeman")
        self.assertEqual(data.unit(358).base_cost, ResourceCost(food=35, wood=25))
        self.assertEqual(data.tech(61).name, "Logistica")
        self.assertEqual(data.coverage.status, CoverageStatus.FACTUAL_SUBSET)

    def test_byzantine_cost_modifier_resolves_without_mutating_base_game_cost(self):
        profile = ByzantineProfile.for_update_185872()
        effective = resolve_effective_civ(profile)

        self.assertEqual(effective.unit(358).base_cost, ResourceCost(food=35, wood=25))
        self.assertEqual(
            effective.cost_of("unit:358"),
            ResourceCost(food=26, wood=19),
        )

    def test_patch_identity_is_part_of_the_effective_snapshot_fingerprint(self):
        profile = ByzantineProfile.for_update_185872()
        first = resolve_effective_civ(profile)
        self.assertEqual(first.fingerprint, resolve_effective_civ(profile).fingerprint)
        with self.assertRaisesRegex(ValueError, "GameData snapshot patch"):
            resolve_effective_civ(
                replace(
                    profile,
                    patch=PatchId(
                        product="AOE2DE",
                        update="185873",
                        build=None,
                        release_date="2026-09-23",
                    ),
                )
            )

    def test_strategy_semantics_are_not_available_in_game_data(self):
        unit = UnitDef(
            id=358,
            name="Pikeman",
            line="pikeman-line",
            available_age=Age.CASTLE,
            providers=(),
            base_cost=ResourceCost(food=35, wood=25),
            train_time_seconds=None,
            prerequisites=(),
            classes=("INFANTRY",),
        )

        self.assertFalse(hasattr(unit, "strategic_tags"))

    def test_n_of_prerequisite_rejects_invalid_shape(self):
        with self.assertRaises(ValueError):
            Prerequisite(PrerequisiteKind.N_OF, count=0, children=(Prerequisite(PrerequisiteKind.AGE, age=Age.DARK),))
        with self.assertRaises(ValueError):
            Prerequisite(PrerequisiteKind.N_OF, count=2, children=(Prerequisite(PrerequisiteKind.AGE, age=Age.DARK),))

    def test_invalid_selector_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            SelectorKind("BEST_RESPONSE")


if __name__ == "__main__":
    unittest.main()
