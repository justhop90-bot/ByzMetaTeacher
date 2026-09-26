import unittest

from LearnerAI.Compiler.ir.civ_profile import ByzantineProfile, resolve_effective_civ
from LearnerAI.Compiler.ir.game_data import (
    Age,
    BuildingId,
    ResourceCost,
    UnitId,
    UnitLineId,
)


class GameDataHardeningTests(unittest.TestCase):
    def setUp(self):
        self.profile = ByzantineProfile.for_update_185872()
        self.data = resolve_effective_civ(self.profile)

    def test_byzantine_land_roster_lines_are_complete_for_current_land_subset(self):
        expected = {
            "militia-line": (74, 75, 77, 473, 567),
            "spearman-line": (93, 358, 359),
            "scout-cavalry-line": (448, 546, 441),
            "knight-line": (38, 283, 569),
            "camel-rider-line": (329, 330),
            "archer-line": (4,),
            "crossbow-line": (24, 492),
            "cavalry-archer-line": (39, 474),
        }
        for line_id, members in expected.items():
            self.assertEqual(
                self.data.unit_line(line_id).members,
                tuple(UnitId(value) for value in members),
                line_id,
            )

    def test_byzantine_land_roster_contains_hand_cannoneer_and_varangian_guards(self):
        self.assertEqual(self.data.unit(5).name, "Hand Cannoneer")
        self.assertEqual(self.data.unit(5).line, UnitLineId("hand-cannoneer-line"))
        self.assertEqual(self.data.unit(2703).name, "Varangian Guard")
        self.assertEqual(self.data.unit(2703).line, UnitLineId("varangian-guard-line"))
        self.assertEqual(self.data.unit(2704).name, "Elite Varangian Guard")
        self.assertEqual(self.data.tech(1454).name, "Elite Varangian Guard")

    def test_barracks_and_archery_range_expose_current_varangian_and_hand_cannoneer_capabilities(self):
        self.assertIn(UnitLineId("varangian-guard-line"), self.data.building(12).trainable_lines)
        self.assertIn(UnitLineId("hand-cannoneer-line"), self.data.building(87).trainable_lines)

    def test_logistica_targets_exact_current_units_not_an_unresolved_fake_class(self):
        interaction = next(
            item for item in self.profile.interactions
            if item.id == "logistica-trample-current-units"
        )
        self.assertEqual(
            interaction.target.ids,
            ("40", "553", "2703", "2704"),
        )
        self.assertEqual(interaction.target.kind.value, "UNIT")

    def test_upgrade_links_are_bidirectional_for_land_lines(self):
        for current_id, previous_id in (
            (75, 74),
            (77, 75),
            (473, 77),
            (567, 473),
            (358, 93),
            (359, 358),
            (546, 448),
            (441, 546),
            (283, 38),
            (569, 283),
            (474, 39),
            (492, 24),
            (330, 329),
            (553, 40),
            (6, 7),
        ):
            current = self.data.unit(current_id)
            previous = self.data.unit(previous_id)
            self.assertEqual(current.upgrades_from, UnitId(previous_id))
            self.assertEqual(previous.upgrades_to, UnitId(current_id))

    def test_known_unavailable_generic_siege_upgrades_are_not_promoted(self):
        self.assertNotIn(UnitId(550), self.data.available_units)
        self.assertNotIn(UnitId(588), self.data.available_units)
        self.assertNotIn(UnitId(542), self.data.available_units)

    def test_factual_costs_for_current_land_additions(self):
        self.assertEqual(self.data.cost_of("unit:5"), ResourceCost(food=45, gold=50))
        self.assertEqual(self.data.cost_of("unit:39"), ResourceCost(wood=40, gold=60))
        self.assertEqual(self.data.cost_of("unit:2703"), ResourceCost(food=65, gold=45))
        self.assertEqual(self.data.cost_of("unit:2704"), ResourceCost(food=65, gold=45))
        self.assertEqual(
            self.data.cost_of_age_advance(Age.IMPERIAL),
            ResourceCost(food=667, gold=536),
        )


if __name__ == "__main__":
    unittest.main()
