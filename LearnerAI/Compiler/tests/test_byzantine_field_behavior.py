import re
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
        self.assertIn("(dropsite-min-distance wood s:<= sn-lumber-camp-max-distance)", camp)
        self.assertIn("(can-build lumber-camp)", camp)
        self.assertIn("(set-goal demand-economy-lumber-camp-floor-1 1)", camp)
        self.assertNotIn("(current-age >= castle-age)\n    (resource-found wood)", camp)

        self.assertIn("(resource-found gold)", camp)
        self.assertIn("(dropsite-min-distance gold > 6)", camp)
        self.assertIn("(dropsite-min-distance gold s:<= sn-mining-camp-max-distance)", camp)
        self.assertIn("(can-build mining-camp)", camp)
        self.assertIn("(set-goal demand-economy-gold-camp-floor-1 1)", camp)
        self.assertNotIn("(current-age >= castle-age)\n    (resource-found gold)", camp)

        self.assertNotIn("(build lumber-camp)", camp)
        self.assertNotIn("(build mining-camp)", camp)

    def test_resource_walking_distance_tracks_camp_policy_and_stops_at_sparse_fallback(self):
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

        controller = self._section_from(
            "; BYZANTINE THREE-LAYER CAMP PLACEMENT CONTROLLER",
            "; RESOURCE-CENTERED CAMP PLACEMENT EXECUTION",
        )
        self.assertIn(
            "(set-strategic-number sn-lumber-camp-max-distance byzantine-resource-camp-radius-wide)",
            controller,
        )
        self.assertIn(
            "(set-strategic-number sn-mining-camp-max-distance byzantine-resource-camp-radius-remote)",
            controller,
        )
        self.assertIn(
            "(defconst byzantine-resource-camp-radius-wide 24)",
            self.per,
        )
        self.assertIn(
            "(defconst byzantine-resource-camp-radius-remote 30)",
            self.per,
        )

    def test_resource_camp_radius_controller_synchronizes_demand_search_and_progressive_widening(self):
        controller = self._section_from(
            "; BYZANTINE THREE-LAYER CAMP PLACEMENT CONTROLLER",
            "; RESOURCE-CENTERED CAMP PLACEMENT EXECUTION",
        )

        self.assertIn("(defconst byzantine-resource-camp-radius-stage 790)", self.per)
        self.assertIn("(defconst byzantine-resource-camp-radius-stage-base 0)", self.per)
        self.assertIn("(defconst byzantine-resource-camp-radius-stage-wide 1)", self.per)
        self.assertIn("(defconst byzantine-resource-camp-radius-stage-remote 2)", self.per)
        self.assertIn("(defconst byzantine-resource-camp-radius-wide 24)", self.per)
        self.assertIn("(defconst byzantine-resource-camp-radius-remote 30)", self.per)

        for radius in (16, 18, 20):
            self.assertIn(
                f"(set-strategic-number sn-lumber-camp-max-distance {radius})",
                controller,
            )
            self.assertIn(
                f"(set-strategic-number sn-mining-camp-max-distance {radius})",
                controller,
            )
            self.assertIn(
                f"(set-strategic-number sn-maximum-wood-drop-distance {radius})",
                controller,
            )
            self.assertIn(
                f"(set-strategic-number sn-maximum-gold-drop-distance {radius})",
                controller,
            )

        self.assertIn(
            "(set-strategic-number sn-lumber-camp-max-distance byzantine-resource-camp-radius-wide)",
            controller,
        )
        self.assertIn(
            "(set-strategic-number sn-mining-camp-max-distance byzantine-resource-camp-radius-wide)",
            controller,
        )
        self.assertIn(
            "(set-strategic-number sn-maximum-wood-drop-distance byzantine-resource-camp-radius-wide)",
            controller,
        )
        self.assertIn(
            "(set-strategic-number sn-maximum-gold-drop-distance byzantine-resource-camp-radius-wide)",
            controller,
        )
        self.assertIn(
            "(set-strategic-number sn-lumber-camp-max-distance byzantine-resource-camp-radius-remote)",
            controller,
        )
        self.assertIn(
            "(set-strategic-number sn-mining-camp-max-distance byzantine-resource-camp-radius-remote)",
            controller,
        )

        self.assertIn(
            "(dropsite-min-distance wood s:<= sn-lumber-camp-max-distance)",
            controller,
        )
        self.assertIn(
            "(dropsite-min-distance gold s:<= sn-mining-camp-max-distance)",
            controller,
        )
        self.assertIn(
            "(dropsite-min-distance stone s:<= sn-mining-camp-max-distance)",
            controller,
        )
        self.assertNotIn("(dropsite-min-distance wood <= 18)", controller)
        self.assertNotIn("(dropsite-min-distance gold <= 18)", controller)
        self.assertNotIn("(dropsite-min-distance stone <= 18)", controller)

        self.assertIn(
            "(goal byzantine-resource-camp-radius-stage byzantine-resource-camp-radius-stage-base)",
            controller,
        )
        self.assertIn(
            "(set-goal byzantine-resource-camp-radius-stage byzantine-resource-camp-radius-stage-wide)",
            controller,
        )
        self.assertIn(
            "(set-goal byzantine-resource-camp-radius-stage byzantine-resource-camp-radius-stage-remote)",
            controller,
        )
        self.assertIn(
            "(set-goal byzantine-resource-camp-state byzantine-resource-camp-state-search)",
            controller,
        )

        self.assertIn(
            "(up-compare-goal byzantine-resource-camp-search-state-remote-list == 0)",
            controller,
        )
        self.assertIn(
            "(goal byzantine-resource-camp-radius-stage byzantine-resource-camp-radius-stage-wide)",
            controller,
        )
        self.assertIn(
            "(goal byzantine-resource-camp-radius-stage byzantine-resource-camp-radius-stage-remote)",
            controller,
        )

    def test_failed_wood_search_hands_off_gold_once_then_releases_to_lumber(self):
        controller = self._section_from(
            "; BYZANTINE THREE-LAYER CAMP PLACEMENT CONTROLLER",
            "; RESOURCE-CENTERED CAMP PLACEMENT EXECUTION",
        )
        self.assertIn(
            "(defconst byzantine-resource-camp-gold-handoff 795)",
            self.per,
        )
        self.assertIn(
            "(set-goal byzantine-resource-camp-gold-handoff 0)",
            self.per,
        )

        # Normal lumber priority is disabled only while the one-pass handoff is active.
        normal_selector = controller.split(
            "(defrule\n    (goal byzantine-resource-camp-state byzantine-resource-camp-state-idle)",
            1,
        )[1]
        self.assertIn(
            "(goal byzantine-resource-camp-gold-handoff 0)",
            normal_selector,
        )
        self.assertIn(
            "(not (town-under-attack))",
            normal_selector,
        )
        self.assertIn(
            "(goal byzantine-resource-camp-gold-handoff 1)\n        (not\n            (or\n                (goal demand-economy-lumber-camp-floor-1 1)",
            controller,
        )

        failure = controller[
            controller.index(
                "(goal byzantine-resource-camp-kind byzantine-resource-camp-kind-wood)\n"
                "    (goal byzantine-resource-camp-radius-stage byzantine-resource-camp-radius-stage-remote)"
            ):
        ]
        failure_end = failure.index(
            "(defrule",
            1,
        )
        failure = failure[:failure_end]

        self.assertIn("(goal byzantine-resource-camp-gold-handoff 0)", failure)
        self.assertIn("(set-goal byzantine-resource-camp-gold-handoff 1)", failure)

        gold_failure = controller[
            controller.index(
                "(goal byzantine-resource-camp-kind byzantine-resource-camp-kind-gold)\n"
                "    (goal byzantine-resource-camp-radius-stage byzantine-resource-camp-radius-stage-remote)"
            ):
        ]
        gold_failure_end = gold_failure.index("(defrule", 1)
        gold_failure = gold_failure[:gold_failure_end]
        self.assertIn("(goal byzantine-resource-camp-gold-handoff 1)", gold_failure)
        self.assertIn("(set-goal byzantine-resource-camp-gold-handoff 0)", gold_failure)

        gold_complete = self._section_from(
            "; economy-gold-camp-floor-1",
            "; economy-gold-camp-floor-2",
        )
        self.assertIn(
            "(set-goal byzantine-resource-camp-gold-handoff 0)",
            gold_complete,
        )

        self.assertEqual(
            self.per.count("(set-goal byzantine-resource-camp-gold-handoff 1)"),
            1,
        )

    def test_resource_camp_search_state_goal_fields_are_declared(self):
        for expected in (
            "(defconst byzantine-resource-camp-search-state-local-total 791)",
            "(defconst byzantine-resource-camp-search-state-local-list 792)",
            "(defconst byzantine-resource-camp-search-state-remote-total 793)",
            "(defconst byzantine-resource-camp-search-state-remote-list 794)",
        ):
            self.assertIn(expected, self.per)


    def test_dark_age_base_camp_radius_preserves_known_good_opening_distance(self):
        controller = self._section_from(
            "; BYZANTINE THREE-LAYER CAMP PLACEMENT CONTROLLER",
            "; RESOURCE-CENTERED CAMP PLACEMENT EXECUTION",
        )
        self.assertIn(
            "(set-strategic-number sn-lumber-camp-max-distance 16)",
            controller,
        )
        self.assertIn(
            "(set-strategic-number sn-mining-camp-max-distance 16)",
            controller,
        )
        self.assertIn(
            "(set-strategic-number sn-maximum-wood-drop-distance 16)",
            controller,
        )
        self.assertIn(
            "(set-strategic-number sn-maximum-gold-drop-distance 16)",
            controller,
        )

    def test_arabia_dark_age_first_camps_use_persisted_point_legality_then_ring_fallback(self):
        self.assertNotIn(
            "; Standard Arabia opening first-camp placement bypasses the strict candidate-ring legality probe.",
            self.per,
        )
        controller = self._section_from(
            "; BYZANTINE RESOURCE CAMP CANDIDATE-RING PLACEMENT",
            "; RESOURCE-CENTERED CAMP PLACEMENT EXECUTION",
        )
        self.assertIn(
            "(up-can-build-line 0 byzantine-resource-camp-point c: lumber-camp)",
            controller,
        )
        self.assertIn(
            "(up-can-build-line 0 byzantine-resource-camp-point c: mining-camp)",
            controller,
        )

    def test_remote_resource_recovery_never_retasks_into_far_or_fortified_resource(self):
        recovery = self._section_from(
            "; REMOTE RESOURCE RECOVERY / PRODUCTIVITY-WITNESSED CAMP CONTROL",
            "; PERSISTENT BYZANTINE STANDING ARMY FLOORS",
        )
        self.assertIn(
            "(dropsite-min-distance gold s:<= sn-mining-camp-max-distance)",
            recovery,
        )
        self.assertIn(
            "(dropsite-min-distance wood s:<= sn-lumber-camp-max-distance)",
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

    def test_resource_camp_searches_an_eight_point_legal_candidate_ring_before_execution(self):
        ring = self._section_from(
            "; BYZANTINE RESOURCE CAMP CANDIDATE-RING PLACEMENT",
            "; RESOURCE-CENTERED CAMP PLACEMENT EXECUTION",
        )
        for pair, x, y in (
            ("byzantine-resource-camp-ring-ne", 3, 3),
            ("byzantine-resource-camp-ring-e", 3, 0),
            ("byzantine-resource-camp-ring-se", 3, -3),
            ("byzantine-resource-camp-ring-s", 0, -3),
            ("byzantine-resource-camp-ring-sw", -3, -3),
            ("byzantine-resource-camp-ring-w", -3, 0),
            ("byzantine-resource-camp-ring-nw", -3, 3),
            ("byzantine-resource-camp-ring-n", 0, 3),
        ):
            self.assertIn(f"(defconst {pair} ", ring)
            self.assertIn(f"(set-goal {pair} {x})", ring)
            self.assertIn(f"(set-goal {pair}-y {y})", ring)

        self.assertIn(
            "(up-copy-point byzantine-resource-camp-candidate-point byzantine-resource-camp-point)",
            ring,
        )
        self.assertIn(
            "(up-add-point byzantine-resource-camp-candidate-point byzantine-resource-camp-ring-ne c: 1)",
            ring,
        )
        self.assertIn(
            "(up-bound-point byzantine-resource-camp-candidate-point byzantine-resource-camp-candidate-point)",
            ring,
        )
        self.assertIn(
            "(up-can-build-line 0 byzantine-resource-camp-candidate-point c: lumber-camp)",
            ring,
        )
        self.assertIn(
            "(up-can-build-line 0 byzantine-resource-camp-candidate-point c: mining-camp)",
            ring,
        )
        self.assertIn(
            "(up-copy-point byzantine-resource-camp-point byzantine-resource-camp-candidate-point)",
            ring,
        )
        self.assertIn(
            "(up-remove-objects search-remote object-data-index c:== 0)",
            ring,
        )
        self.assertIn(
            "(set-goal byzantine-resource-camp-state byzantine-resource-camp-state-reselect)",
            ring,
        )

    def test_opening_camp_arbitration_does_not_deadlock_gold_behind_wood_demand(self):
        controller = self._section_from(
            "; BYZANTINE THREE-LAYER CAMP PLACEMENT CONTROLLER",
            "; RESOURCE-CENTERED CAMP PLACEMENT EXECUTION",
        )
        self.assertNotIn(
            "(current-age == dark-age)\n                (unit-type-count-total villager >= 12)",
            controller,
        )
        self.assertNotIn(
            "(current-age == dark-age)\n    (unit-type-count-total villager >= 12)",
            controller,
        )
        self.assertIn(
            "(goal demand-economy-gold-camp-floor-1 1)",
            controller,
        )
        self.assertIn(
            "(goal demand-economy-lumber-camp-floor-1 1)",
            controller,
        )

    def test_resource_camp_prefers_persisted_resource_point_before_candidate_ring(self):
        controller = self._section_from(
            "; BYZANTINE THREE-LAYER CAMP PLACEMENT CONTROLLER",
            "; RESOURCE-CENTERED CAMP PLACEMENT EXECUTION",
        )
        direct = controller.index(
            "(up-can-build-line 0 byzantine-resource-camp-point c: lumber-camp)"
        )
        ring = controller.index(
            "(up-add-point byzantine-resource-camp-candidate-point byzantine-resource-camp-ring-ne c: 1)"
        )
        self.assertLess(direct, ring)
        self.assertIn(
            "(up-can-build-line 0 byzantine-resource-camp-point c: mining-camp)",
            controller,
        )

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

    def test_resource_camp_builder_assignment_precedes_point_build_and_is_preserved(self):
        for building, start_marker, end_marker in (
            (
                "lumber-camp",
                "; Action issuance: economy-lumber-camp-floor-1 | ACTIVE -> ISSUED",
                "; Pending diagnostics: economy-lumber-camp-floor-2",
            ),
            (
                "mining-camp",
                "; economy-gold-camp-floor-1",
                "; economy-gold-camp-floor-2",
            ),
        ):
            start = self.per.index(start_marker)
            end = self.per.index(end_marker, start)
            action = self.per[start:end]
            assign = action.index(f"(up-assign-builders c: {building} c: 1)")
            build = action.index(f"(up-build place-point 0 c: {building})")
            self.assertLess(assign, build)

    def test_first_camp_failed_placement_removes_candidate_and_widens_before_retry(self):
        lumber_start = self.per.index("; Failed first-camp placement recovery: remove the consumed wood candidate before retry.")
        lumber_end = self.per.index("; Pending diagnostics: economy-lumber-camp-floor-1", lumber_start)
        lumber = self.per[lumber_start:lumber_end]

        gold_start = self.per.index("; Failed first-camp placement recovery: remove the consumed gold candidate before retry.")
        gold_end = self.per.index("; economy-gold-camp-floor-1", gold_start)
        gold = self.per[gold_start:gold_end]

        for recovery, building_id, demand_states, resource in (
            (lumber, "562", ("77", "75"), "wood"),
            (gold, "584", ("621", "622"), "gold"),
        ):
            self.assertIn(f"(up-pending-objects c: {building_id} == 0)", recovery)
            self.assertIn(f"(not (up-pending-placement c: {building_id}))", recovery)
            self.assertIn("(goal byzantine-resource-camp-state byzantine-resource-camp-state-idle)", recovery)
            self.assertIn("(up-remove-objects search-remote object-data-index c:== 0)", recovery)
            self.assertIn("(up-clean-search search-remote object-data-distance search-order-asc)", recovery)
            self.assertIn("(up-get-search-state byzantine-resource-camp-search-state)", recovery)
            self.assertIn(
                f"(set-goal byzantine-resource-camp-placement-failure-kind byzantine-resource-camp-kind-{resource})",
                recovery,
            )
            self.assertIn("(set-goal byzantine-resource-camp-state byzantine-resource-camp-state-reselect)", recovery)
            for state in demand_states:
                self.assertIn(f"(goal demand-economy-{'lumber-camp-floor-1' if resource == 'wood' else 'gold-camp-floor-1'} {state})", recovery)

        controller = self._section_from(
            "; A nearest resource already covered by an existing dropsite is not viable.",
            "; REMOTE RESOURCE RECOVERY / PRODUCTIVITY-WITNESSED CAMP CONTROL",
        )
        base = controller.index(
            "(goal byzantine-resource-camp-radius-stage byzantine-resource-camp-radius-stage-base)"
        )
        wide = controller.index(
            "(goal byzantine-resource-camp-radius-stage byzantine-resource-camp-radius-stage-wide)"
        )
        remote = controller.index(
            "(goal byzantine-resource-camp-radius-stage byzantine-resource-camp-radius-stage-remote)"
        )
        self.assertLess(base, wide)
        self.assertLess(wide, remote)
        self.assertIn(
            "(set-goal byzantine-resource-camp-state byzantine-resource-camp-state-acquire-origin)",
            controller,
        )
        self.assertIn("(defconst byzantine-resource-camp-placement-failure-kind 747)", self.per)
        self.assertIn(
            "(not (goal byzantine-resource-camp-placement-failure-kind byzantine-resource-camp-kind-wood))",
            self.per,
        )
        self.assertIn(
            "(not (goal byzantine-resource-camp-placement-failure-kind byzantine-resource-camp-kind-gold))",
            self.per,
        )
        self.assertIn("(set-goal byzantine-resource-camp-placement-failure-kind 0)", self.per)

        lumber_start = self.per.index("; Failed first-camp placement recovery: remove the consumed wood candidate before retry.")
        lumber_end = self.per.index("; Pending diagnostics: economy-lumber-camp-floor-2", lumber_start)
        lumber_lifecycle = self.per[lumber_start:lumber_end]
        self.assertLess(
            lumber_lifecycle.index("; Failed first-camp placement recovery: remove the consumed wood candidate before retry."),
            lumber_lifecycle.index("; RETRY | ISSUED/PENDING -> ACTIVE"),
        )

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

    def test_castle_muster_search_groups_stay_inside_native_group_range(self):
        names = (
            "byzantine-siege-muster-mangonel-group",
            "byzantine-siege-muster-army-group",
            "byzantine-siege-muster-trebuchet-group",
            "byzantine-siege-muster-bombard-group",
            "byzantine-siege-muster-ram-group",
        )
        values = []
        for name in names:
            match = re.search(rf"\\(defconst {re.escape(name)} (\\d+)\\)", self.per)
            self.assertIsNotNone(match, f"{name} must be defined")
            values.append(int(match.group(1)))

        self.assertEqual(values, [5, 6, 7, 8, 9])
        self.assertEqual(len(values), len(set(values)))
        self.assertTrue(all(0 <= value <= 9 for value in values))

    def test_fortified_castle_transitions_into_witnessed_siege_muster(self):
        self.assertIn(
            "(up-get-point position-object byzantine-offensive-castle-point)",
            self.per,
        )
        self.assertIn(
            "(set-goal byzantine-siege-approach byzantine-siege-approach-staging)",
            self.per,
        )
        self.assertIn(
            "(defconst byzantine-siege-muster-state 15000)",
            self.per,
        )
        self.assertIn(
            "(up-lerp-tiles byzantine-siege-muster-point position-self c: bt-byzantine-muster-objective-distance)",
            self.per,
        )
        self.assertIn(
            "(up-create-group 0 40 c: byzantine-siege-muster-army-group)",
            self.per,
        )
        self.assertIn(
            "(up-group-size c: byzantine-siege-muster-army-group >= bt-byzantine-muster-imperial-army)",
            self.per,
        )
        self.assertIn(
            "(set-strategic-number sn-number-attack-groups 1)",
            self.per,
        )
        self.assertIn(
            "(up-target-point 0 action-attack-move -1 stance-aggressive)",
            self.per,
        )
        self.assertIn(
            "(set-goal byzantine-siege-approach byzantine-siege-approach-escorted)",
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


    def test_blocked_ring_candidate_restores_candidate_state_for_next_slot(self):
        ring = self._section_from(
            "; BYZANTINE RESOURCE CAMP CANDIDATE-RING PLACEMENT",
            "; RESOURCE-CENTERED CAMP PLACEMENT EXECUTION",
        )
        self.assertIn(
            "(goal byzantine-resource-camp-ring-index 0)\n"
            "    (goal byzantine-resource-camp-building-kind byzantine-resource-camp-building-lumber)",
            ring,
        )
        self.assertIn(
            "(set-goal byzantine-resource-camp-target-valid 1)\n"
            "    (set-goal byzantine-resource-camp-placement-state "
            "byzantine-resource-camp-placement-state-candidate)\n"
            "    (set-goal byzantine-resource-camp-ring-index 1)",
            ring,
        )
        self.assertIn(
            "(goal byzantine-resource-camp-ring-index 0)\n"
            "    (goal byzantine-resource-camp-building-kind byzantine-resource-camp-building-mining)",
            ring,
        )

    def test_arabia_first_camp_does_not_bypass_persisted_point_legality(self):
        self.assertNotIn(
            "; Standard Arabia opening first-camp placement bypasses the strict candidate-ring legality probe.",
            self.per,
        )
        controller = self._section_from(
            "; BYZANTINE RESOURCE CAMP CANDIDATE-RING PLACEMENT",
            "; RESOURCE-CENTERED CAMP PLACEMENT EXECUTION",
        )
        self.assertIn(
            "(up-can-build-line 0 byzantine-resource-camp-point c: lumber-camp)",
            controller,
        )
        self.assertIn(
            "(up-can-build-line 0 byzantine-resource-camp-point c: mining-camp)",
            controller,
        )

    def test_foundational_camps_are_required_before_feudal_research_issuance(self):
        action = self._section_from(
            "; Action issuance: feudal-transition | ACTIVE -> ISSUED",
            "; Recovery: feudal-resource-claim | RELEASED/COMPLETE cleanup",
        )
        self.assertIn(
            "(building-type-count-total lumber-camp >= 1)",
            action,
        )
        self.assertIn(
            "(building-type-count-total mining-camp >= 1)",
            action,
        )


if __name__ == "__main__":
    unittest.main()