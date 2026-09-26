import unittest

from LearnerAI.Compiler.ir.civ_profile import ByzantineProfile, resolve_effective_civ
from LearnerAI.Compiler.ir.game_data import (
    Age,
    BuildingId,
    EntitySelector,
    FactStatus,
    PrerequisiteKind,
    Rational,
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

    def test_rational_values_are_canonical(self):
        self.assertEqual(Rational(2, 4), Rational(1, 2))

    def test_skirmisher_discount_is_a_separate_byzantine_unit_line_modifier(self):
        self.assertEqual(
            self.data.unit_line("skirmisher-line").members,
            (UnitId(7), UnitId(6)),
        )
        self.assertEqual(self.data.cost_of("unit:7"), ResourceCost(food=19, wood=26))
        self.assertEqual(self.data.cost_of("unit:6"), ResourceCost(food=19, wood=26))

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
        dromon = next(item for item in self.profile.bonuses if item.id == "byz-dromon-speed")
        monk = next(item for item in self.profile.bonuses if item.id == "byz-team-monk-heal")
        self.assertEqual((fire.modifier.value.numerator, fire.modifier.value.denominator), (4, 5))
        self.assertEqual(fire.selector, EntitySelector.unit_line(UnitLineId("fire-ship-line")))
        self.assertEqual((dromon.modifier.value.numerator, dromon.modifier.value.denominator), (4, 5))
        self.assertEqual(dromon.selector, EntitySelector.unit_line(UnitLineId("dromon-line")))
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

    def test_age_advances_encode_verified_building_prerequisites(self):
        feudal = self.data.age_advance(Age.FEUDAL)
        castle = self.data.age_advance(Age.CASTLE)
        imperial = self.data.age_advance(Age.IMPERIAL)

        self.assertEqual(feudal.from_age, Age.DARK)
        self.assertEqual(castle.from_age, Age.FEUDAL)
        self.assertEqual(imperial.from_age, Age.CASTLE)
        self.assertEqual(feudal.native_tech_id, 101)
        self.assertEqual(castle.native_tech_id, 102)
        self.assertEqual(imperial.native_tech_id, 103)

        self.assertEqual(feudal.prerequisites[0].kind, PrerequisiteKind.N_OF)
        self.assertEqual(feudal.prerequisites[0].count, 2)
        self.assertEqual(castle.prerequisites[0].kind, PrerequisiteKind.N_OF)
        self.assertEqual(castle.prerequisites[0].count, 2)
        self.assertEqual(imperial.prerequisites[0].kind, PrerequisiteKind.ANY)
        self.assertEqual(imperial.prerequisites[0].children[0].building, BuildingId(82))
        self.assertEqual(imperial.prerequisites[0].children[1].kind, PrerequisiteKind.N_OF)

    def test_upgrade_relations_carry_native_research_triggers(self):
        expected = {
            (93, 358): 197,
            (358, 359): 429,
            (4, 24): 100,
            (24, 492): 237,
            (329, 330): 236,
            (40, 553): 361,
            (2703, 2704): 1454,
            (529, 532): 246,
        }
        actual = {
            (int(relation.previous), int(relation.current)): int(relation.research)
            for relation in self.data.upgrade_relations
        }
        for edge, research in expected.items():
            self.assertEqual(actual[edge], research)

    def test_varangian_effects_are_typed_engine_facts(self):
        varangian = self.data.unit(2703)
        self.assertIn("SHOCK_INFANTRY", {item.value for item in varangian.engine_classes})
        self.assertTrue(
            any(effect.attribute == "gold-when-fighting-other-units" for effect in varangian.effects)
        )
        self.assertTrue(
            any(effect.attribute == "affected-by-gambesons" for effect in varangian.effects)
        )

    def test_bounded_strategic_fact_status_is_tristate(self):
        self.assertEqual(self.data.factual_status("unit", 93), FactStatus.VERIFIED)
        self.assertEqual(self.data.factual_status("unit-line", "spearman-line"), FactStatus.VERIFIED)
        self.assertEqual(self.data.factual_status("age-advance", "castle-age"), FactStatus.VERIFIED)
        self.assertEqual(
            self.data.factual_status("technology", 435),
            FactStatus.VERIFIED_UNAVAILABLE,
        )
        self.assertEqual(
            self.data.factual_status("unit", 588),
            FactStatus.VERIFIED_UNAVAILABLE,
        )
        self.assertEqual(
            self.data.factual_status("unit", 999999),
            FactStatus.UNKNOWN,
        )

    def test_bounded_strategic_facts_carry_provenance(self):
        objects = (
            self.data.building(12),
            self.data.building(82),
            self.data.building(103),
            self.data.building(109),
            self.data.unit_line("spearman-line"),
            self.data.unit_line("skirmisher-line"),
            self.data.unit_line("camel-rider-line"),
            self.data.unit(40),
            self.data.unit(553),
            self.data.unit(2703),
            self.data.unit(2704),
            self.data.tech(197),
            self.data.tech(429),
            self.data.tech(98),
            self.data.tech(236),
            self.data.age_advance(Age.FEUDAL),
            self.data.age_advance(Age.CASTLE),
        )
        for item in objects:
            self.assertTrue(item.provenance, type(item).__name__)

    def test_current_snapshot_marks_itself_as_a_factual_subset(self):
        self.assertEqual(self.data.coverage.status.value, "FACTUAL_SUBSET")
        self.data.require_coverage("unit", 2703)
        with self.assertRaisesRegex(ValueError, "factual coverage"):
            self.data.require_coverage("unit", 550)

    def test_verified_unavailable_byzantine_entities_are_first_class_facts(self):
        for tech_id in (435, 436, 239):
            self.assertIn(tech_id, [int(item) for item in self.data.verified_unavailable_technologies])
            self.assertNotIn(tech_id, [int(item) for item in self.data.available_technologies])
        for unit_id in (588, 542):
            self.assertIn(UnitId(unit_id), self.data.verified_unavailable_units)
            self.assertNotIn(UnitId(unit_id), self.data.available_units)

    def test_varangian_ids_are_repository_anchored_and_patch_valid(self):
        self.assertEqual(self.data.unit(2703).name, "Varangian Guard")
        self.assertEqual(self.data.unit(2704).name, "Elite Varangian Guard")
        self.assertEqual(self.data.tech(1454).name, "Elite Varangian Guard")


if __name__ == "__main__":
    unittest.main()
