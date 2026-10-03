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
        end = self.per.find("(defrule", start + len(marker))
        return self.per[start:] if end < 0 else self.per[start:end]

    def test_safe_land_opening_selects_fast_castle(self):
        block = self._rule_block("; Native control rule: opening-selector-defensive-standard")
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
            "(and (current-age >= castle-age) (stone-amount < 650) (resource-found stone))",
            self.per,
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
        block = self._rule_block("; FEUDAL SECOND MILL: FORAGE / BERRY TRANSITION")
        self.assertIn("(current-age == feudal-age)", block)
        self.assertIn("(set-strategic-number sn-preferred-mill-placement 0)", block)
        self.assertIn("(build mill)", block)
        self.assertIn("(up-pending-placement c: 68)", block)

    def test_fast_castle_defers_eco_research_until_castle(self):
        for marker in (
            "; Action issuance: research-wheelbarrow | ACTIVE -> ISSUED",
            "; Action issuance: research-double-bit-axe | ACTIVE -> ISSUED",
            "; Action issuance: research-horse-collar | ACTIVE -> ISSUED",
            "; Action issuance: research-gold-mining | ACTIVE -> ISSUED",
        ):
            block = self._rule_block(marker)
            self.assertIn("(current-age >= castle-age)", block)
            self.assertNotIn("(current-age >= feudal-age)", block)


if __name__ == "__main__":
    unittest.main()
