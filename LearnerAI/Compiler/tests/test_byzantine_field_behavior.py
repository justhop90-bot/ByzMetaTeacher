import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PER_PATH = REPO_ROOT / "Byzantine.per"


class ByzantineFieldBehaviorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.per = PER_PATH.read_text(encoding="utf-8")

    def _section_from(self, marker, end_marker=None):
        start = self.per.index(marker)
        if end_marker is None:
            end = len(self.per)
        else:
            end = self.per.index(end_marker, start)
        return self.per[start:end]

    def test_near_resource_fronts_build_camps_without_castle_age_gate(self):
        wood = self._section_from(
            "; Byzantine near-resource lumber-camp recovery",
            "; Byzantine near-resource mining-camp recovery",
        )
        gold = self._section_from(
            "; Byzantine near-resource mining-camp recovery",
            "; The same bounded front rule applies to stone",
        )

        self.assertIn("(resource-found wood)", wood)
        self.assertIn("(dropsite-min-distance wood > 6)", wood)
        self.assertIn("(dropsite-min-distance wood <= 18)", wood)
        self.assertIn("(can-build lumber-camp)", wood)
        self.assertIn("(build lumber-camp)", wood)
        self.assertNotIn("(current-age >= castle-age)", wood)

        self.assertIn("(resource-found gold)", gold)
        self.assertIn("(dropsite-min-distance gold > 6)", gold)
        self.assertIn("(dropsite-min-distance gold <= 18)", gold)
        self.assertIn("(can-build mining-camp)", gold)
        self.assertIn("(build mining-camp)", gold)
        self.assertNotIn("(current-age >= castle-age)", gold)

    def test_resource_walking_distance_is_bounded_and_never_widens_to_36(self):
        init = self._section_from(
            "; Native economy rule: byzantine-community-economy-initialize",
            "; Native economy rule: byzantine-boar-lure-enable",
        )
        self.assertIn(
            "(set-strategic-number sn-maximum-wood-drop-distance 16)",
            init,
        )
        self.assertIn(
            "(set-strategic-number sn-maximum-gold-drop-distance 16)",
            init,
        )

        self.assertIn(
            "(set-strategic-number sn-lumber-camp-max-distance 18)",
            self.per,
        )
        self.assertIn(
            "(set-strategic-number sn-mining-camp-max-distance 18)",
            self.per,
        )
        self.assertNotIn(
            "(set-strategic-number sn-lumber-camp-max-distance 36)",
            self.per,
        )
        self.assertNotIn(
            "(set-strategic-number sn-mining-camp-max-distance 36)",
            self.per,
        )

    def test_remote_resource_recovery_never_retasks_into_far_or_fortified_resource(self):
        recovery = self._section_from(
            "; REMOTE RESOURCE RECOVERY / PRODUCTIVITY-WITNESSED CAMP CONTROL",
            "; PERSISTENT BYZANTINE STANDING ARMY FLOORS",
        )
        self.assertIn(
            "(dropsite-min-distance gold <= 18)",
            recovery,
        )
        self.assertIn(
            "(dropsite-min-distance wood <= 18)",
            recovery,
        )
        self.assertIn(
            "(not (goal byzantine-fortification-threat 1))",
            recovery,
        )

    def test_fortified_castle_transitions_into_targeted_siege_push(self):
        self.assertIn(
            "(up-get-point position-object byzantine-offensive-castle-point)",
            self.per,
        )
        self.assertIn(
            "(set-goal byzantine-siege-approach byzantine-siege-approach-staging)",
            self.per,
        )
        self.assertIn(
            "(up-target-objects 0 action-attack-move -1 stance-aggressive)",
            self.per,
        )
        self.assertIn(
            "(set-strategic-number sn-percent-attack-soldiers 100)",
            self.per,
        )
        self.assertIn(
            "(up-filter-include cmdid-military -1 -1 -1)",
            self.per,
        )
        self.assertIn(
            "(goal byzantine-offensive-castle-valid 1)",
            self.per,
        )

    def test_imperial_siege_ram_upgrade_is_reasserted_when_rams_exist(self):
        self.assertIn(
            "(current-age >= imperial-age)",
            self.per,
        )
        self.assertIn(
            "(unit-type-count-total battering-ram-line >= 1)",
            self.per,
        )
        self.assertIn(
            "(set-goal demand-research-siege-ram 1)",
            self.per,
        )


if __name__ == "__main__":
    unittest.main()
