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

    def test_near_resource_fronts_reopen_existing_camp_demands_without_castle_age_gate(self):
        camp = self._section_from(
            "; BYZANTINE THREE-LAYER CAMP PLACEMENT CONTROLLER",
            "; Per-pass transient action arbitration",
        )

        self.assertIn("(resource-found wood)", camp)
        self.assertIn("(dropsite-min-distance wood > 6)", camp)
        self.assertIn("(dropsite-min-distance wood <= 18)", camp)
        self.assertIn("(can-build lumber-camp)", camp)
        self.assertIn("(set-goal demand-economy-lumber-camp-floor-1 1)", camp)
        self.assertNotIn("(current-age >= castle-age)\n    (resource-found wood)", camp)

        self.assertIn("(resource-found gold)", camp)
        self.assertIn("(dropsite-min-distance gold > 6)", camp)
        self.assertIn("(dropsite-min-distance gold <= 18)", camp)
        self.assertIn("(can-build mining-camp)", camp)
        self.assertIn("(set-goal demand-economy-gold-camp-floor-1 1)", camp)
        self.assertNotIn("(current-age >= castle-age)\n    (resource-found gold)", camp)

        self.assertNotIn("(build lumber-camp)", camp)
        self.assertNotIn("(build mining-camp)", camp)

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

    def test_resource_camp_selector_chooses_nearest_real_resource_and_persists_point(self):
        self.assertIn("(up-clean-search search-remote object-data-distance search-order-asc)", self.per)
        self.assertIn("(up-set-target-object search-remote c: 0)", self.per)
        self.assertIn("(up-get-point position-object byzantine-resource-camp-point)", self.per)
        self.assertIn("(set-goal byzantine-resource-camp-state byzantine-resource-camp-state-ready)", self.per)
        self.assertIn("(goal byzantine-resource-camp-kind byzantine-resource-camp-kind-wood)", self.per)
        self.assertIn("(goal byzantine-resource-camp-kind byzantine-resource-camp-kind-gold)", self.per)

    def test_resource_camp_executes_at_persisted_point_through_existing_builder_lifecycle(self):
        for building, demand in (
            ("lumber-camp", "demand-economy-lumber-camp-floor-1"),
            ("mining-camp", "demand-economy-gold-camp-floor-1"),
        ):
            self.assertIn("(up-set-target-point byzantine-resource-camp-point)", self.per)
            self.assertIn(f"(up-assign-builders c: {building} c: 1)", self.per)
            self.assertIn(f"(up-build place-point 0 c: {building})", self.per)
            self.assertIn(f"(goal {demand} 1)", self.per)

        camp_actions = self.per[
            self.per.index("; RESOURCE-CENTERED CAMP PLACEMENT EXECUTION"):
            self.per.index("; REMOTE RESOURCE RECOVERY / PRODUCTIVITY-WITNESSED CAMP CONTROL")
        ]
        self.assertNotIn("(build lumber-camp)", self.per)
        self.assertNotIn("(build mining-camp)", self.per)

    def test_blocked_camp_placement_enters_pending_instead_of_reissuing(self):
        lumber = self._section_from(
            "; Pending diagnostics: economy-lumber-camp-floor-1",
            "; Pending diagnostics: economy-lumber-camp-floor-2",
        )
        gold_start = self.per.index("; economy-gold-camp-floor-1")
        gold = self.per[gold_start:self.per.index("; economy-gold-camp-floor-2", gold_start)]

        for lifecycle, building_id, pending_goal in (
            (lumber, "562", "75"),
            (gold, "584", "622"),
        ):
            self.assertIn(
                f"(up-pending-objects c: {building_id} >= 1)",
                lifecycle,
            )
            self.assertIn(
                f"(up-pending-objects c: {building_id} == 0)\n    (up-pending-placement c: {building_id})",
                lifecycle,
            )
            self.assertIn(
                f"(set-goal demand-economy-{'lumber-camp-floor-1' if building_id == '562' else 'gold-camp-floor-1'} {pending_goal})",
                lifecycle,
            )
            self.assertIn(
                f"(up-pending-objects c: {building_id} == 0)\n    (not (up-pending-placement c: {building_id}))",
                lifecycle,
            )

    def test_blocked_nearest_candidate_is_removed_before_alternate_candidate_reselection(self):
        reselect = self._section_from(
            "; A nearest resource already covered by an existing dropsite is not viable.",
            "; REMOTE RESOURCE RECOVERY / PRODUCTIVITY-WITNESSED CAMP CONTROL",
        )
        for resource in ("wood", "gold", "stone"):
            self.assertIn(
                f"(goal byzantine-resource-camp-kind byzantine-resource-camp-kind-{resource})",
                reselect,
            )
            self.assertIn(
                "(up-remove-objects search-remote object-data-index c:== 0)",
                reselect,
            )
            self.assertIn(
                "(up-clean-search search-remote object-data-distance search-order-asc)",
                reselect,
            )
        self.assertIn(
            "(set-goal byzantine-resource-camp-state byzantine-resource-camp-state-reselect)",
            reselect,
        )
        self.assertIn(
            "(goal byzantine-resource-camp-state byzantine-resource-camp-state-reselect)",
            reselect,
        )
        self.assertIn(
            "(up-set-target-object search-remote c: 0)",
            reselect,
        )
        self.assertIn(
            "(up-get-point position-object byzantine-resource-camp-point)",
            reselect,
        )

    def test_camp_loss_reopens_completed_floor_demand_for_lumber_and_gold(self):
        lumber = self._section_from(
            "; Pending diagnostics: economy-lumber-camp-floor-1",
            "; Pending diagnostics: economy-lumber-camp-floor-2",
        )
        gold_start = self.per.index("; economy-gold-camp-floor-1")
        gold = self.per[gold_start:self.per.index("; economy-gold-camp-floor-2", gold_start)]

        for lifecycle, demand, building in (
            (lumber, "demand-economy-lumber-camp-floor-1", "lumber-camp"),
            (gold, "demand-economy-gold-camp-floor-1", "mining-camp"),
        ):
            self.assertIn(f"(set-goal {demand} 0)", lifecycle)
            self.assertIn(f"(goal {demand} 0)", lifecycle)
            self.assertIn(f"(not (building-type-count {building} >= 1))", lifecycle)
            self.assertIn(f"(set-goal {demand} 1)", lifecycle)

    def test_resource_depletion_releases_camp_demand_without_immediate_reactivation(self):
        lumber = self._section_from(
            "; Pending diagnostics: economy-lumber-camp-floor-1",
            "; Pending diagnostics: economy-lumber-camp-floor-2",
        )
        gold_start = self.per.index("; economy-gold-camp-floor-1")
        gold = self.per[gold_start:self.per.index("; economy-gold-camp-floor-2", gold_start)]

        for lifecycle, resource, demand in (
            (lumber, "wood", "demand-economy-lumber-camp-floor-1"),
            (gold, "gold", "demand-economy-gold-camp-floor-1"),
        ):
            self.assertIn(f"(set-goal {demand} 0)", lifecycle)
            self.assertIn(f"(resource-found {resource})", lifecycle)
            self.assertIn(f"(goal {demand} 0)", lifecycle)
            self.assertIn(f"(not (building-type-count", lifecycle)
            self.assertIn(f"(resource-found {resource})", lifecycle)
            self.assertNotIn(
                f"(goal {demand} 0)\n    (not (resource-found {resource}))",
                lifecycle,
            )
            self.assertIn(f"(set-goal {demand} 1)", lifecycle)


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
