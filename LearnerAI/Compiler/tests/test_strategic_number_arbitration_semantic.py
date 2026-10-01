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

    def test_existing_age_and_posture_modes_normalize_to_fixed_layers(self):
        effective, profile = self._profile()

        controllers = tuple(
            strategic_number_mode_to_controller(mode, profile.profile_id)
            for mode in profile.strategic_number_modes
        )

        age = next(
            item
            for item in controllers
            if item.identity == "civilian-builders-feudal"
        )
        strategy = next(
            item
            for item in controllers
            if item.identity == "attack-allocation-flush"
        )

        self.assertIs(
            age.layer,
            StrategicNumberControllerLayer.AGE_BASE,
        )
        self.assertIs(
            strategy.layer,
            StrategicNumberControllerLayer.STRATEGY,
        )
        self.assertEqual(age.native_state_name, "sn-native-4")
        self.assertEqual(strategy.native_state_name, "sn-native-227")

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
            "(not (goal emergency-defense 1))",
            base_rule.facts[0].source,
        )

    def test_release_rule_does_not_capture_or_restore_historical_value(self):
        temporary = StrategicNumberController(
            identity="emergency-defense",
            native_strategic_number_id=227,
            value=25,
            layer=StrategicNumberControllerLayer.TEMPORARY,
            activation_guard="(goal emergency 1)",
            release_guard="(goal emergency-cleared 1)",
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
            extra_controllers=(temporary,),
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
            ("set-goal",),
        )
        self.assertNotIn(
            "(set-strategic-number sn-native-227 75)",
            "
".join(item.source for item in release_rule.actions),
        )

    def test_action_controller_produces_exact_attachment_and_release(self):
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
            extra_controllers=(action,),
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
