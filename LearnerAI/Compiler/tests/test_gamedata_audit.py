import unittest

from LearnerAI.Compiler.ir.civ_profile import ByzantineProfile, resolve_effective_civ
from LearnerAI.Compiler.ir.game_data import (
    Age,
    BuildingId,
    EntitySelector,
    ResourceCost,
    UnitId,
    UnitLineId,
)


class GameDataAuditTests(unittest.TestCase):
    def setUp(self):
        self.profile = ByzantineProfile.for_update_185872()
        self.data = resolve_effective_civ(self.profile)

    def test_age_advances_are_separate_from_ordinary_technology(self):
        imperial = self.data.age_advance(Age.IMPERIAL)
        self.assertEqual(imperial.provider_building, BuildingId(109))
        self.assertEqual(imperial.base_cost, ResourceCost(food=1000, gold=800))

    def test_imperial_discount_only_applies_to_imperial_age_advance(self):
        self.assertEqual(
            self.data.cost_of_age_advance(Age.IMPERIAL),
            ResourceCost(food=667, gold=536),
        )
        self.assertEqual(self.data.cost_of("unit:38"), ResourceCost(food=60, gold=75))
        self.assertEqual(self.data.cost_of("building:82"), self.data.building(82).base_cost)

    def test_spearman_line_discount_covers_all_three_units(self):
        self.assertEqual(
            self.data.unit_line("spearman-line").members,
            (UnitId(93), UnitId(358), UnitId(359)),
        )
        self.assertEqual(self.data.cost_of("unit:93"), ResourceCost(food=26, wood=19))
        self.assertEqual(self.data.cost_of("unit:358"), ResourceCost(food=26, wood=19))
        self.assertEqual(self.data.cost_of("unit:359"), ResourceCost(food=26, wood=19))

    def test_building_hp_bonus_does_not_match_units_or_technologies(self):
        castle_building = self.data.building(82)
        bonus = next(item for item in self.profile.bonuses if item.id == "byz-building-hp-castle")
        self.assertTrue(self.data.matches_bonus_selector(bonus.selector, castle_building))
        self.assertTrue(self.data.matches_bonus_selector(bonus.selector, self.data.building(12)))
        self.assertFalse(self.data.matches_bonus_selector(bonus.selector, self.data.unit(40)))
        self.assertEqual(bonus.age_scope, Age.CASTLE)

    def test_fire_ship_is_present_in_effective_data(self):
        self.assertEqual(self.data.unit(529).name, "Fire Ship")
        self.assertEqual(self.data.unit(529).line, UnitLineId("fire-ship-line"))

    def test_free_town_watch_and_patrol_are_civ_data(self):
        self.assertEqual(self.data.tech(8).base_cost, ResourceCost(food=75))
        self.assertEqual(self.data.tech(280).base_cost, ResourceCost(food=300, gold=100))
        self.assertTrue(self.data.is_free_for_civ("tech:8"))
        self.assertTrue(self.data.is_free_for_civ("tech:280"))

    def test_logistica_has_verified_current_cost(self):
        self.assertEqual(self.data.tech(61).base_cost, ResourceCost(food=800, gold=600))

    def test_current_patch_attack_and_healing_modifiers_are_encoded(self):
        fire = next(item for item in self.profile.bonuses if item.id == "byz-fire-ship-speed")
        monk = next(item for item in self.profile.bonuses if item.id == "byz-team-monk-heal")
        self.assertEqual((fire.modifier.value.numerator, fire.modifier.value.denominator), (4, 5))
        self.assertEqual((monk.modifier.value.numerator, monk.modifier.value.denominator), (2, 1))

    def test_dromon_and_greek_fire_effects_are_present(self):
        self.assertEqual(self.data.unit(1795).name, "Dromon")
        greek_fire = self.data.tech(464)
        self.assertEqual(len(greek_fire.effects), 3)

    def test_logistica_trample_target_is_verified_current_unit_set(self):
        interaction = next(
            item for item in self.profile.interactions
            if item.id == "logistica-trample-current-units"
        )
        self.assertEqual(
            interaction.target,
            EntitySelector.units(UnitId(40), UnitId(553), UnitId(2703), UnitId(2704)),
        )

    def test_provider_graph_has_verified_production_relationships(self):
        self.assertIn(UnitLineId("skirmisher-line"), self.data.building(87).trainable_lines)
        self.assertIn(UnitLineId("hand-cannoneer-line"), self.data.building(87).trainable_lines)
        self.assertIn(UnitLineId("cavalry-archer-line"), self.data.building(87).trainable_lines)
        self.assertIn(UnitLineId("camel-rider-line"), self.data.building(101).trainable_lines)
        self.assertIn(UnitLineId("cataphract-line"), self.data.building(82).trainable_lines)
        self.assertIn(UnitLineId("bombard-cannon-line"), self.data.building(49).trainable_lines)
        self.assertIn(UnitLineId("dromon-line"), self.data.building(45).trainable_lines)
        self.assertIn(UnitLineId("varangian-guard-line"), self.data.building(12).trainable_lines)

    def test_age_advances_do_not_claim_unverified_static_building_prerequisites(self):
        for age in (Age.FEUDAL, Age.CASTLE, Age.IMPERIAL):
            self.assertEqual(self.data.age_advance(age).prerequisites, ())

    def test_varangian_ids_are_repository_anchored_and_patch_valid(self):
        self.assertEqual(self.data.unit(2703).name, "Varangian Guard")
        self.assertEqual(self.data.unit(2704).name, "Elite Varangian Guard")
        self.assertEqual(self.data.tech(1454).name, "Elite Varangian Guard")


if __name__ == "__main__":
    unittest.main()
