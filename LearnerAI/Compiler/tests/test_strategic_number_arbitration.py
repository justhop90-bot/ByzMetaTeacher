import unittest

from Compiler.ast import SourceLocation
from Compiler.ir.strategic_number_arbitration import (
    StrategicNumberActionAttachment,
    StrategicNumberArbitrationPlan,
    StrategicNumberController,
    StrategicNumberControllerLayer,
    StrategicNumberControllerScope,
    StrategicNumberReleaseEvidence,
    StrategicNumberRestorationPolicy,
)


class StrategicNumberArbitrationIrTests(unittest.TestCase):
    def _controller(
        self,
        identity="base",
        *,
        sn=227,
        value=75,
        layer=StrategicNumberControllerLayer.AGE_BASE,
        priority=0,
        activation=None,
        release=None,
        scope=StrategicNumberControllerScope.PERSISTENT,
        action=None,
        evidence=None,
    ):
        return StrategicNumberController(
            identity=identity,
            native_strategic_number_id=sn,
            value=value,
            layer=layer,
            priority=priority,
            activation_guard=activation,
            release_guard=release,
            scope=scope,
            restoration=StrategicNumberRestorationPolicy.REASSERT_UNDERLAY,
            release_evidence=evidence,
            action_identity=action,
            owner="fixture",
        )

    def test_fixed_precedence_is_closed(self):
        ordered = tuple(
            sorted(
                StrategicNumberControllerLayer,
                key=lambda item: item.precedence,
                reverse=True,
            )
        )
        self.assertEqual(
            ordered,
            (
                StrategicNumberControllerLayer.RECOVERY,
                StrategicNumberControllerLayer.ACTION,
                StrategicNumberControllerLayer.TEMPORARY,
                StrategicNumberControllerLayer.STRATEGY,
                StrategicNumberControllerLayer.AGE_BASE,
                StrategicNumberControllerLayer.DEFAULT_BASE,
            ),
        )

    def test_controller_derives_one_physical_state_and_stable_activation_state(self):
        controller = self._controller(
            "attack-surge",
            layer=StrategicNumberControllerLayer.ACTION,
            activation="(goal attack-state 1)",
            release="(goal attack-state 0)",
            scope=StrategicNumberControllerScope.ACTION_SCOPED,
            action="attack-now-rule",
            evidence=StrategicNumberReleaseEvidence.TIMER_CADENCE,
        )
        self.assertEqual(controller.native_state_name, "sn-native-227")
        self.assertEqual(
            controller.activation_state_name,
            "sn-controller-attack-surge-active",
        )

    def test_temporary_requires_release_guard_and_release_evidence(self):
        with self.assertRaisesRegex(ValueError, "release_guard"):
            self._controller(
                "temporary",
                layer=StrategicNumberControllerLayer.TEMPORARY,
                scope=StrategicNumberControllerScope.UNTIL_RELEASE,
            )

        with self.assertRaisesRegex(ValueError, "release_evidence"):
            self._controller(
                "temporary",
                layer=StrategicNumberControllerLayer.TEMPORARY,
                release="(true)",
                scope=StrategicNumberControllerScope.UNTIL_RELEASE,
            )

    def test_action_requires_exact_action_identity_and_action_scope(self):
        with self.assertRaisesRegex(ValueError, "action_identity"):
            self._controller(
                "attack-surge",
                layer=StrategicNumberControllerLayer.ACTION,
                activation="(true)",
                release="(true)",
                scope=StrategicNumberControllerScope.ACTION_SCOPED,
                evidence=StrategicNumberReleaseEvidence.TIMER_CADENCE,
            )

        with self.assertRaisesRegex(ValueError, "ACTION_SCOPED"):
            self._controller(
                "attack-surge",
                layer=StrategicNumberControllerLayer.ACTION,
                activation="(true)",
                release="(true)",
                scope=StrategicNumberControllerScope.UNTIL_RELEASE,
                action="attack-now-rule",
                evidence=StrategicNumberReleaseEvidence.TIMER_CADENCE,
            )

    def test_persistent_underlay_cannot_have_release_guard(self):
        with self.assertRaisesRegex(ValueError, "persistent"):
            self._controller(
                "base",
                release="(true)",
                evidence=StrategicNumberReleaseEvidence.WORLD_WITNESS,
            )

    def test_invalid_native_id_and_value_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "0..511"):
            self._controller("bad-sn", sn=512)

        with self.assertRaisesRegex(ValueError, "-32768..32767"):
            self._controller("bad-value", value=32768)

    def test_plan_has_one_physical_identity_per_native_sn(self):
        plan = StrategicNumberArbitrationPlan(
            controllers=(
                self._controller("age", sn=227, value=75),
                self._controller(
                    "strategy",
                    sn=227,
                    value=50,
                    layer=StrategicNumberControllerLayer.STRATEGY,
                    activation="(goal strategy-posture 1)",
                ),
            )
        )
        self.assertEqual(plan.native_strategic_number_ids, (227,))
        self.assertEqual(
            tuple(item.identity for item in plan.controllers_for_sn(227)),
            ("strategy", "age"),
        )

    def test_same_layer_equal_priority_conflict_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "conflicting"):
            StrategicNumberArbitrationPlan(
                controllers=(
                    self._controller(
                        "a",
                        value=50,
                        activation="(goal strategy-posture 1)",
                        layer=StrategicNumberControllerLayer.STRATEGY,
                    ),
                    self._controller(
                        "b",
                        value=75,
                        activation="(goal strategy-posture 1)",
                        layer=StrategicNumberControllerLayer.STRATEGY,
                    ),
                )
            )

    def test_same_layer_equal_priority_same_value_is_coalesced(self):
        plan = StrategicNumberArbitrationPlan(
            controllers=(
                self._controller(
                    "b",
                    value=50,
                    activation="(goal strategy-posture 1)",
                    layer=StrategicNumberControllerLayer.STRATEGY,
                ),
                self._controller(
                    "a",
                    value=50,
                    activation="(goal strategy-posture 1)",
                    layer=StrategicNumberControllerLayer.STRATEGY,
                ),
            )
        )
        self.assertEqual(
            tuple(item.identity for item in plan.controllers),
            ("a",),
        )

    def test_controller_order_is_deterministic(self):
        plan = StrategicNumberArbitrationPlan(
            controllers=(
                self._controller(
                    "z",
                    layer=StrategicNumberControllerLayer.ACTION,
                    priority=10,
                    activation="(true)",
                    release="(true)",
                    scope=StrategicNumberControllerScope.ACTION_SCOPED,
                    action="attack-z",
                    evidence=StrategicNumberReleaseEvidence.TIMER_CADENCE,
                ),
                self._controller(
                    "a",
                    layer=StrategicNumberControllerLayer.STRATEGY,
                    priority=0,
                    activation="(goal strategy-posture 1)",
                ),
                self._controller(
                    "m",
                    layer=StrategicNumberControllerLayer.TEMPORARY,
                    priority=5,
                    activation="(goal emergency 1)",
                    release="(goal emergency 0)",
                    scope=StrategicNumberControllerScope.UNTIL_RELEASE,
                    evidence=StrategicNumberReleaseEvidence.WORLD_WITNESS,
                ),
            )
        )
        self.assertEqual(
            tuple(item.identity for item in plan.controllers),
            ("z", "m", "a"),
        )

    def test_action_attachment_requires_exact_nonempty_identity(self):
        with self.assertRaisesRegex(ValueError, "identity"):
            StrategicNumberActionAttachment(
                identity="",
                controller_identity="attack-surge",
                action_identity="attack-now-rule",
                native_strategic_number_id=227,
                value=100,
                activation_state_name="sn-controller-attack-surge-active",
            )


if __name__ == "__main__":
    unittest.main()
