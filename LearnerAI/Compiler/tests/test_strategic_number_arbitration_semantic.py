import unittest

from Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_castle_strategy,
    compile_strategy_profile,
)
from Compiler.ir import (
    StrategicNumberController,
    StrategicNumberControllerLayer,
    StrategicNumberControllerScope,
    StrategicNumberReleaseEvidence,
)
from Compiler.ir.strategy import StrategicNumberMode, StrategyPosture
from Compiler.primitives.strategic_number_catalog import (
    default_strategic_number_inventory,
)
from Compiler.ir.civ_profile import resolve_effective_civ
from Compiler.semantic.strategic_number_arbitration import (
    build_strategic_number_arbitration_plan,
    lower_strategic_number_arbitration,
    strategic_number_mode_to_controller,
    validate_strategic_number_arbitration,
)


class StrategicNumberArbitrationSemanticTests(unittest.TestCase):
    def _profile(self):
        effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        return effective, build_byzantine_castle_strategy(effective)

    def test_existing_posture_modes_normalize_to_fixed_layers(self):
        effective, profile = self._profile()

        controllers = tuple(
            strategic_number_mode_to_controller(mode, profile.profile_id)
            for mode in profile.strategic_number_modes
        )

        strategy = next(
            item
            for item in controllers
            if item.identity == "attack-allocation-flush"
        )

        self.assertIs(
            strategy.layer,
            StrategicNumberControllerLayer.STRATEGY,
        )
        self.assertEqual(strategy.native_state_name, "sn-native-227")

    def test_current_byzantine_posture_modes_cover_all_four_native_sn227_allocations(self):
        effective, profile = self._profile()

        controllers = tuple(
            strategic_number_mode_to_controller(mode, profile.profile_id)
            for mode in profile.strategic_number_modes
        )
        by_identity = {controller.identity: controller for controller in controllers}

        expected = {
            "attack-allocation-flush": (50, StrategyPosture.FLUSH),
            "attack-allocation-rush": (50, StrategyPosture.RUSH),
            "attack-allocation-boom": (75, StrategyPosture.BOOM),
            "attack-allocation-castle-power": (75, StrategyPosture.CASTLE_POWER),
        }

        self.assertEqual(set(by_identity), set(expected))
        for identity, (value, posture) in expected.items():
            controller = by_identity[identity]
            self.assertEqual(controller.native_strategic_number_id, 227)
            self.assertEqual(controller.value, value)
            expected_posture_guard = {
                StrategyPosture.FLUSH: "(goal strategy-posture 1)",
                StrategyPosture.RUSH: "(goal strategy-posture 2)",
                StrategyPosture.BOOM: "(goal strategy-posture 3)",
                StrategyPosture.CASTLE_POWER: "(goal strategy-posture 4)",
            }[posture]
            self.assertIn(expected_posture_guard, controller.activation_guard)
            self.assertIs(controller.layer, StrategicNumberControllerLayer.STRATEGY)
            self.assertEqual(controller.native_state_name, "sn-native-227")

    def test_undocumented_native_id_is_rejected_by_semantic_gate(self):
        controller = StrategicNumberController(
            identity="undocumented",
            native_strategic_number_id=510,
            value=50,
            layer=StrategicNumberControllerLayer.AGE_BASE,
            owner="fixture",
            activation_guard="(current-age >= feudal-age)",
        )
        plan = build_strategic_number_arbitration_plan(
            type(
                "Profile",
                (),
                {
                    "profile_id": "fixture",
                    "strategic_number_modes": (),
                },
            )(),
            extra_controllers=(controller,),
        )

        with self.assertRaisesRegex(ValueError, "undocumented"):
            validate_strategic_number_arbitration(
                plan,
                documented_native_ids=default_strategic_number_inventory().documented_ids,
            )

    def test_higher_precedence_override_suppresses_lower_underlay(self):
        base = StrategicNumberController(
            identity="strategy-base",
            native_strategic_number_id=227,
            value=75,
            layer=StrategicNumberControllerLayer.STRATEGY,
            activation_guard="(goal strategy-posture 3)",
            owner="fixture",
        )
        temporary = StrategicNumberController(
            identity="emergency-defense",
            native_strategic_number_id=227,
            value=25,
            layer=StrategicNumberControllerLayer.TEMPORARY,
            activation_guard="(goal emergency-defense 1)",
            release_guard="(goal emergency-defense 0)",
            rearm_guard="(goal emergency-defense-reset 1)",
            scope=StrategicNumberControllerScope.UNTIL_RELEASE,
            release_evidence=StrategicNumberReleaseEvidence.WORLD_WITNESS,
            owner="fixture",
        )
        plan = build_strategic_number_arbitration_plan(
            type(
                "Profile",
                (),
                {
                    "profile_id": "fixture",
                    "strategic_number_modes": (),
                },
            )(),
            extra_controllers=(base, temporary),
        )

        lowered = lower_strategic_number_arbitration(
            plan,
            profile_id="fixture",
            documented_native_ids=frozenset({227}),
        )
        assert lowered.control_plan is not None
        base_rule = next(
            item
            for item in lowered.control_plan.rules
            if item.identity == "sn-controller-strategy-base-write"
        )
        self.assertIn(
            "(not (goal sn-controller-emergency-defense-active 1))",
            base_rule.facts[0].source,
        )
        self.assertNotIn(
            "(not (or (goal emergency-defense 1) "
            "(goal sn-controller-emergency-defense-active 1)))",
            base_rule.facts[0].source,
        )


    def test_recovery_release_allows_underlay_reassertion_while_activation_guard_remains_true(self):
        base = StrategicNumberController(
            identity="strategy-base",
            native_strategic_number_id=227,
            value=75,
            layer=StrategicNumberControllerLayer.STRATEGY,
            activation_guard="(current-age >= feudal-age)",
            owner="fixture",
        )
        recovery = StrategicNumberController(
            identity="recovery-override",
            native_strategic_number_id=227,
            value=100,
            layer=StrategicNumberControllerLayer.RECOVERY,
            activation_guard="(current-age >= feudal-age)",
            release_guard="(current-age >= imperial-age)",
            rearm_guard="(goal recovery-reset 1)",
            scope=StrategicNumberControllerScope.UNTIL_RELEASE,
            release_evidence=StrategicNumberReleaseEvidence.WORLD_WITNESS,
            owner="fixture",
        )
        plan = build_strategic_number_arbitration_plan(
            type("Profile", (), {"profile_id": "fixture", "strategic_number_modes": ()})(),
            extra_controllers=(base, recovery),
        )
        lowered = lower_strategic_number_arbitration(
            plan,
            profile_id="fixture",
            documented_native_ids=frozenset({227}),
        )
        assert lowered.control_plan is not None
        base_rule = next(
            item
            for item in lowered.control_plan.rules
            if item.identity == "sn-controller-strategy-base-write"
        )
        self.assertIn(
            "(not (goal sn-controller-recovery-override-active 1))",
            base_rule.facts[0].source,
        )
        stale_recovery_claim = (
            "(not (or (current-age >= feudal-age) "
            "(goal sn-controller-recovery-override-active 1)))"
        )
        self.assertNotIn(
            stale_recovery_claim,
            base_rule.facts[0].source,
        )

    def test_higher_priority_same_layer_suppresses_lower_priority(self):
        high = StrategicNumberController(
            identity="high-priority",
            native_strategic_number_id=227,
            value=50,
            layer=StrategicNumberControllerLayer.TEMPORARY,
            priority=20,
            activation_guard="(goal emergency-high 1)",
            release_guard="(goal emergency-high 0)",
            rearm_guard="(goal emergency-high-reset 1)",
            scope=StrategicNumberControllerScope.UNTIL_RELEASE,
            release_evidence=StrategicNumberReleaseEvidence.WORLD_WITNESS,
            owner="fixture",
        )
        low = StrategicNumberController(
            identity="low-priority",
            native_strategic_number_id=227,
            value=25,
            layer=StrategicNumberControllerLayer.TEMPORARY,
            priority=10,
            activation_guard="(goal emergency-low 1)",
            release_guard="(goal emergency-low 0)",
            rearm_guard="(goal emergency-low-reset 1)",
            scope=StrategicNumberControllerScope.UNTIL_RELEASE,
            release_evidence=StrategicNumberReleaseEvidence.WORLD_WITNESS,
            owner="fixture",
        )
        base = StrategicNumberController(
            identity="base",
            native_strategic_number_id=227,
            value=75,
            layer=StrategicNumberControllerLayer.STRATEGY,
            activation_guard="(goal strategy-posture 3)",
            owner="fixture",
        )
        plan = build_strategic_number_arbitration_plan(
            type("Profile", (), {"profile_id": "fixture", "strategic_number_modes": ()})(),
            extra_controllers=(base, high, low),
        )
        lowered = lower_strategic_number_arbitration(
            plan,
            profile_id="fixture",
            documented_native_ids=frozenset({227}),
        )
        assert lowered.control_plan is not None
        low_rule = next(
            item
            for item in lowered.control_plan.rules
            if item.identity == "sn-controller-low-priority-steady"
        )
        self.assertIn(
            "(not (goal sn-controller-high-priority-active 1))",
            low_rule.facts[0].source,
        )
        self.assertNotIn(
            "(not (or (goal emergency-high 1) "
            "(goal sn-controller-high-priority-active 1)))",
            low_rule.facts[0].source,
        )

    def test_release_rearm_uses_explicit_reset_guard(self):
        base = StrategicNumberController(
            identity="strategy-base",
            native_strategic_number_id=227,
            value=75,
            layer=StrategicNumberControllerLayer.STRATEGY,
            activation_guard="(current-age >= feudal-age)",
            owner="fixture",
        )

        for layer, identity, activation, release, rearm in (
            (
                StrategicNumberControllerLayer.TEMPORARY,
                "temporary-rearm",
                "(goal emergency 1)",
                "(goal emergency-cleared 1)",
                "(goal temporary-rearm-reset 1)",
            ),
            (
                StrategicNumberControllerLayer.RECOVERY,
                "recovery-rearm",
                "(goal recovery-needed 1)",
                "(goal recovery-clear 1)",
                "(goal recovery-rearm-reset 1)",
            ),
        ):
            controller = StrategicNumberController(
                identity=identity,
                native_strategic_number_id=227,
                value=25,
                layer=layer,
                activation_guard=activation,
                release_guard=release,
                rearm_guard=rearm,
                scope=StrategicNumberControllerScope.UNTIL_RELEASE,
                release_evidence=StrategicNumberReleaseEvidence.WORLD_WITNESS,
                owner="fixture",
            )
            plan = build_strategic_number_arbitration_plan(
                type("Profile", (), {"profile_id": "fixture", "strategic_number_modes": ()})(),
                extra_controllers=(base, controller),
            )
            lowered = lower_strategic_number_arbitration(
                plan,
                profile_id="fixture",
                documented_native_ids=frozenset({227}),
            )
            assert lowered.control_plan is not None

            activation_rule = next(
                item
                for item in lowered.control_plan.rules
                if item.identity == f"sn-controller-{identity}-activate"
            )
            self.assertIn(
                f"(goal sn-controller-{identity}-release-block 0)",
                activation_rule.facts[0].source,
            )
            self.assertIn(
                f"(goal sn-rearm-{identity} 0)",
                activation_rule.facts[0].source,
            )

            clear_rule_index = next(
                index
                for index, rule in enumerate(lowered.control_plan.rules)
                if rule.identity == f"sn-controller-{identity}-rearm-pass-clear"
            )
            activation_index = next(
                index
                for index, rule in enumerate(lowered.control_plan.rules)
                if rule.identity == f"sn-controller-{identity}-activate"
            )
            self.assertLess(
                clear_rule_index,
                activation_index,
                "rearm-pass clear must precede activation so the sentinel belongs to the next pass",
            )

            release_rule = next(
                item
                for item in lowered.control_plan.rules
                if item.identity == f"sn-controller-{identity}-release"
            )
            self.assertEqual(
                tuple(action.source for action in release_rule.actions),
                (
                    f"(set-goal sn-controller-{identity}-active 0)",
                    f"(set-goal sn-controller-{identity}-release-block 1)",
                ),
            )

            rearm_rule = next(
                item
                for item in lowered.control_plan.rules
                if item.identity == f"sn-controller-{identity}-rearm"
            )
            self.assertIn(
                f"(goal sn-controller-{identity}-release-block 1)",
                rearm_rule.facts[0].source,
            )
            self.assertIn(
                f"(goal sn-controller-{identity}-active 0)",
                rearm_rule.facts[0].source,
            )
            self.assertIn(
                rearm,
                rearm_rule.facts[0].source,
            )
            self.assertNotIn(
                f"(not {activation})",
                rearm_rule.facts[0].source,
            )
            self.assertEqual(
                tuple(action.source for action in rearm_rule.actions),
                (
                    f"(set-goal sn-controller-{identity}-release-block 0)",
                    f"(set-goal sn-rearm-{identity} 1)",
                    "(set-goal sn-reassert-227 1)",
                ),
            )

            steady_index = next(
                index
                for index, rule in enumerate(lowered.control_plan.rules)
                if rule.identity == f"sn-controller-{identity}-steady"
            )
            self.assertLess(
                next(
                    index
                    for index, rule in enumerate(lowered.control_plan.rules)
                    if rule.identity == f"sn-controller-{identity}-release"
                ),
                next(
                    index
                    for index, rule in enumerate(lowered.control_plan.rules)
                    if rule.identity == f"sn-controller-{identity}-rearm"
                ),
            )
            rearm_index = next(
                index
                for index, rule in enumerate(lowered.control_plan.rules)
                if rule.identity == f"sn-controller-{identity}-rearm"
            )
            self.assertLess(
                rearm_index,
                steady_index,
            )

            rearm_actions = lowered.control_plan.rules[rearm_index].actions
            self.assertEqual(
                tuple(action.head for action in rearm_actions),
                ("set-goal", "set-goal", "set-goal"),
            )


    def test_rearm_marks_physical_sn_for_underlay_handoff(self):
        base = StrategicNumberController(
            identity="strategy-base",
            native_strategic_number_id=227,
            value=75,
            layer=StrategicNumberControllerLayer.STRATEGY,
            activation_guard="(goal strategy-posture 3)",
            owner="fixture",
        )
        recovery = StrategicNumberController(
            identity="recovery-override",
            native_strategic_number_id=227,
            value=100,
            layer=StrategicNumberControllerLayer.RECOVERY,
            activation_guard="(goal recovery-needed 1)",
            release_guard="(goal recovery-clear 1)",
            rearm_guard="(goal recovery-reset 1)",
            scope=StrategicNumberControllerScope.UNTIL_RELEASE,
            release_evidence=StrategicNumberReleaseEvidence.WORLD_WITNESS,
            owner="fixture",
        )
        lowered = lower_strategic_number_arbitration(
            build_strategic_number_arbitration_plan(
                type("Profile", (), {"profile_id": "fixture", "strategic_number_modes": ()})(),
                extra_controllers=(base, recovery),
            ),
            profile_id="fixture",
            documented_native_ids=frozenset({227}),
        )
        assert lowered.control_plan is not None
        rearm = next(
            rule
            for rule in lowered.control_plan.rules
            if rule.identity == "sn-controller-recovery-override-rearm"
        )
        self.assertEqual(
            tuple(action.source for action in rearm.actions),
            (
                "(set-goal sn-controller-recovery-override-release-block 0)",
                "(set-goal sn-rearm-recovery-override 1)",
                "(set-goal sn-reassert-227 1)",
            ),
        )
        underlay = next(
            rule
            for rule in lowered.control_plan.rules
            if rule.identity == "sn-controller-strategy-base-write"
        )
        self.assertIn("(goal sn-reassert-227 1)", underlay.facts[0].source)
        self.assertEqual(
            underlay.actions[-1].source,
            "(set-goal sn-reassert-227 0)",
        )


        recovery_steady = next(
            rule
            for rule in lowered.control_plan.rules
            if rule.identity == "sn-controller-recovery-override-steady"
        )
        self.assertNotIn("(goal sn-reassert-227 1)", recovery_steady.facts[0].source)
        self.assertNotIn(
            "(set-goal sn-reassert-227 0)",
            tuple(action.source for action in recovery_steady.actions),
        )


    def test_temporary_activation_latches_even_when_native_value_is_already_correct(self):
        base = StrategicNumberController(
            identity="strategy-base",
            native_strategic_number_id=227,
            value=25,
            layer=StrategicNumberControllerLayer.STRATEGY,
            activation_guard="(goal strategy-posture 3)",
            owner="fixture",
        )
        temporary = StrategicNumberController(
            identity="emergency-defense",
            native_strategic_number_id=227,
            value=25,
            layer=StrategicNumberControllerLayer.TEMPORARY,
            activation_guard="(goal emergency 1)",
            release_guard="(goal emergency-cleared 1)",
            rearm_guard="(goal emergency-reset 1)",
            scope=StrategicNumberControllerScope.UNTIL_RELEASE,
            release_evidence=StrategicNumberReleaseEvidence.WORLD_WITNESS,
            owner="fixture",
        )
        plan = build_strategic_number_arbitration_plan(
            type(
                "Profile",
                (),
                {
                    "profile_id": "fixture",
                    "strategic_number_modes": (),
                },
            )(),
            extra_controllers=(base, temporary),
        )
        lowered = lower_strategic_number_arbitration(
            plan,
            profile_id="fixture",
            documented_native_ids=frozenset({227}),
        )
        assert lowered.control_plan is not None
        activation_rule = next(
            item
            for item in lowered.control_plan.rules
            if item.identity == "sn-controller-emergency-defense-activate"
        )
        self.assertNotIn("(up-compare-sn sn-native-227 != 25)", activation_rule.facts[0].source)
        self.assertEqual(
            tuple(action.head for action in activation_rule.actions),
            ("set-goal", "set-strategic-number"),
        )

    def test_transient_release_precedes_steady_reassertion(self):
        controllers = (
            StrategicNumberController(
                identity="temporary",
                native_strategic_number_id=227,
                value=25,
                layer=StrategicNumberControllerLayer.TEMPORARY,
                activation_guard="(goal emergency 1)",
                release_guard="(goal emergency-cleared 1)",
                rearm_guard="(goal emergency-reset 1)",
                scope=StrategicNumberControllerScope.UNTIL_RELEASE,
                release_evidence=StrategicNumberReleaseEvidence.WORLD_WITNESS,
                owner="fixture",
            ),
        )
        base = StrategicNumberController(
            identity="base",
            native_strategic_number_id=227,
            value=75,
            layer=StrategicNumberControllerLayer.STRATEGY,
            activation_guard="(goal strategy-posture 3)",
            owner="fixture",
        )
        plan = build_strategic_number_arbitration_plan(
            type("Profile", (), {"profile_id": "fixture", "strategic_number_modes": ()})(),
            extra_controllers=(*controllers, base),
        )
        lowered = lower_strategic_number_arbitration(
            plan,
            profile_id="fixture",
            documented_native_ids=frozenset({227}),
        )
        assert lowered.control_plan is not None
        release_index = next(
            index
            for index, rule in enumerate(lowered.control_plan.rules)
            if rule.identity == "sn-controller-temporary-release"
        )
        steady_index = next(
            index
            for index, rule in enumerate(lowered.control_plan.rules)
            if rule.identity == "sn-controller-temporary-steady"
        )
        self.assertLess(
            release_index,
            steady_index,
            "temporary release must clear ownership before steady-state reassertion",
        )

        recovery = StrategicNumberController(
            identity="recovery",
            native_strategic_number_id=227,
            value=100,
            layer=StrategicNumberControllerLayer.RECOVERY,
            activation_guard="(goal recovery-needed 1)",
            release_guard="(goal recovery-clear 1)",
            rearm_guard="(goal recovery-reset 1)",
            scope=StrategicNumberControllerScope.UNTIL_RELEASE,
            release_evidence=StrategicNumberReleaseEvidence.WORLD_WITNESS,
            owner="fixture",
        )
        plan = build_strategic_number_arbitration_plan(
            type("Profile", (), {"profile_id": "fixture", "strategic_number_modes": ()})(),
            extra_controllers=(base, recovery),
        )
        lowered = lower_strategic_number_arbitration(
            plan,
            profile_id="fixture",
            documented_native_ids=frozenset({227}),
        )
        assert lowered.control_plan is not None
        release_index = next(
            index
            for index, rule in enumerate(lowered.control_plan.rules)
            if rule.identity == "sn-controller-recovery-release"
        )
        steady_index = next(
            index
            for index, rule in enumerate(lowered.control_plan.rules)
            if rule.identity == "sn-controller-recovery-steady"
        )
        self.assertLess(
            release_index,
            steady_index,
            "recovery release must clear ownership before steady-state reassertion",
        )

    def test_release_rule_does_not_capture_or_restore_historical_value(self):
        base = StrategicNumberController(
            identity="strategy-base",
            native_strategic_number_id=227,
            value=75,
            layer=StrategicNumberControllerLayer.STRATEGY,
            activation_guard="(goal strategy-posture 3)",
            owner="fixture",
        )
        temporary = StrategicNumberController(
            identity="emergency-defense",
            native_strategic_number_id=227,
            value=25,
            layer=StrategicNumberControllerLayer.TEMPORARY,
            activation_guard="(goal emergency 1)",
            release_guard="(goal emergency-cleared 1)",
            rearm_guard="(goal emergency-reset 1)",
            scope=StrategicNumberControllerScope.UNTIL_RELEASE,
            release_evidence=StrategicNumberReleaseEvidence.WORLD_WITNESS,
            owner="fixture",
        )
        plan = build_strategic_number_arbitration_plan(
            type(
                "Profile",
                (),
                {
                    "profile_id": "fixture",
                    "strategic_number_modes": (),
                },
            )(),
            extra_controllers=(base, temporary),
        )

        lowered = lower_strategic_number_arbitration(
            plan,
            profile_id="fixture",
            documented_native_ids=frozenset({227}),
        )
        assert lowered.control_plan is not None
        release_rule = next(
            item
            for item in lowered.control_plan.rules
            if item.identity == "sn-controller-emergency-defense-release"
        )
        self.assertEqual(
            tuple(item.head for item in release_rule.actions),
            ("set-goal", "set-goal"),
        )
        self.assertEqual(
            tuple(item.source for item in release_rule.actions),
            (
                "(set-goal sn-controller-emergency-defense-active 0)",
                "(set-goal sn-controller-emergency-defense-release-block 1)",
            ),
        )
        self.assertNotIn(
            "(set-strategic-number sn-native-227 75)",
            "\n".join(item.source for item in release_rule.actions),
        )


    def test_override_without_underlay_is_rejected(self):
        temporary = StrategicNumberController(
            identity="orphan-override",
            native_strategic_number_id=227,
            value=25,
            layer=StrategicNumberControllerLayer.TEMPORARY,
            activation_guard="(goal emergency 1)",
            release_guard="(goal emergency-cleared 1)",
            rearm_guard="(goal emergency-reset 1)",
            scope=StrategicNumberControllerScope.UNTIL_RELEASE,
            release_evidence=StrategicNumberReleaseEvidence.WORLD_WITNESS,
            owner="fixture",
        )
        plan = build_strategic_number_arbitration_plan(
            type("Profile", (), {"profile_id": "fixture", "strategic_number_modes": ()})(),
            extra_controllers=(temporary,),
        )
        with self.assertRaisesRegex(ValueError, "no lower-precedence underlay"):
            validate_strategic_number_arbitration(
                plan,
                documented_native_ids=frozenset({227}),
            )

    def test_action_release_arms_underlay_reassert_when_native_drift_is_absent(self):
        base = StrategicNumberController(
            identity="strategy-base",
            native_strategic_number_id=227,
            value=100,
            layer=StrategicNumberControllerLayer.STRATEGY,
            activation_guard="(goal strategy-posture 3)",
            owner="fixture",
        )
        action = StrategicNumberController(
            identity="attack-surge",
            native_strategic_number_id=227,
            value=100,
            layer=StrategicNumberControllerLayer.ACTION,
            activation_guard="(goal attack-state 1)",
            release_guard="(goal attack-state 0)",
            scope=StrategicNumberControllerScope.ACTION_SCOPED,
            action_identity="attack-now",
            release_evidence=StrategicNumberReleaseEvidence.WORLD_WITNESS,
            owner="fixture",
        )
        plan = build_strategic_number_arbitration_plan(
            type(
                "Profile",
                (),
                {
                    "profile_id": "fixture",
                    "strategic_number_modes": (),
                },
            )(),
            extra_controllers=(base, action),
        )

        lowered = lower_strategic_number_arbitration(
            plan,
            profile_id="fixture",
            documented_native_ids=frozenset({227}),
            action_identities=frozenset({"attack-now"}),
        )
        assert lowered.control_plan is not None

        release_rule = next(
            item
            for item in lowered.control_plan.rules
            if item.identity == "sn-controller-attack-surge-release"
        )
        self.assertEqual(
            tuple(item.source for item in release_rule.actions),
            (
                "(set-goal sn-controller-attack-surge-active 0)",
                "(set-goal sn-reassert-227 1)",
            ),
        )

        underlay_rule = next(
            item
            for item in lowered.control_plan.rules
            if item.identity == "sn-controller-strategy-base-write"
        )
        self.assertIn("(goal sn-reassert-227 1)", underlay_rule.facts[0].source)
        self.assertIn(
            "(up-compare-sn sn-native-227 != 100)",
            underlay_rule.facts[0].source,
        )
        self.assertEqual(
            underlay_rule.actions[-1].source,
            "(set-goal sn-reassert-227 0)",
        )



    def test_action_controller_produces_exact_attachment_and_release(self):
        base = StrategicNumberController(
            identity="strategy-base",
            native_strategic_number_id=227,
            value=75,
            layer=StrategicNumberControllerLayer.STRATEGY,
            activation_guard="(goal strategy-posture 3)",
            owner="fixture",
        )
        action = StrategicNumberController(
            identity="attack-surge",
            native_strategic_number_id=227,
            value=100,
            layer=StrategicNumberControllerLayer.ACTION,
            activation_guard="(goal attack-state 1)",
            release_guard="(goal attack-state 0)",
            scope=StrategicNumberControllerScope.ACTION_SCOPED,
            action_identity="attack-now",
            release_evidence=StrategicNumberReleaseEvidence.TIMER_CADENCE,
            owner="fixture",
        )
        plan = build_strategic_number_arbitration_plan(
            type(
                "Profile",
                (),
                {
                    "profile_id": "fixture",
                    "strategic_number_modes": (),
                },
            )(),
            extra_controllers=(base, action),
        )

        lowered = lower_strategic_number_arbitration(
            plan,
            profile_id="fixture",
            documented_native_ids=frozenset({227}),
            action_identities=frozenset({"attack-now"}),
        )
        self.assertEqual(len(lowered.action_attachments), 1)
        attachment = lowered.action_attachments[0]
        self.assertEqual(attachment.action_identity, "attack-now")
        self.assertEqual(attachment.native_strategic_number_id, 227)
        self.assertEqual(attachment.value, 100)


    def test_explicit_equal_precedence_conflict_fails_closed_even_with_different_guards(self):
        first = StrategicNumberController(
            identity="override-a",
            native_strategic_number_id=227,
            value=25,
            layer=StrategicNumberControllerLayer.TEMPORARY,
            activation_guard="(goal emergency-a 1)",
            release_guard="(goal emergency-a 0)",
            rearm_guard="(goal emergency-a-reset 1)",
            scope=StrategicNumberControllerScope.UNTIL_RELEASE,
            release_evidence=StrategicNumberReleaseEvidence.WORLD_WITNESS,
            owner="fixture",
        )
        second = StrategicNumberController(
            identity="override-b",
            native_strategic_number_id=227,
            value=35,
            layer=StrategicNumberControllerLayer.TEMPORARY,
            activation_guard="(goal emergency-b 1)",
            release_guard="(goal emergency-b 0)",
            rearm_guard="(goal emergency-b-reset 1)",
            scope=StrategicNumberControllerScope.UNTIL_RELEASE,
            release_evidence=StrategicNumberReleaseEvidence.WORLD_WITNESS,
            owner="fixture",
        )
        base = StrategicNumberController(
            identity="base",
            native_strategic_number_id=227,
            value=75,
            layer=StrategicNumberControllerLayer.STRATEGY,
            activation_guard="(goal strategy-posture 3)",
            owner="fixture",
        )
        plan = build_strategic_number_arbitration_plan(
            type("Profile", (), {"profile_id": "fixture", "strategic_number_modes": ()})(),
            extra_controllers=(base, first, second),
        )
        with self.assertRaisesRegex(ValueError, "conflicting explicit"):
            validate_strategic_number_arbitration(
                plan,
                documented_native_ids=frozenset({227}),
            )

    def test_current_byzantine_strategy_remains_deterministic_through_arbitration(self):
        effective, profile = self._profile()
        first = compile_strategy_profile(profile, effective)
        second = compile_strategy_profile(profile, effective)
        self.assertEqual(first, second)
        self.assertIn("(defconst sn-native-227 227)", first)
        self.assertIn("(set-strategic-number sn-native-227 50)", first)
        self.assertIn("(set-strategic-number sn-native-227 75)", first)
        self.assertNotIn("(set-strategic-number sn-native-227 0)", first)


if __name__ == "__main__":
    unittest.main()
