import unittest

from Compiler.primitives.engine_semantics import EngineSemanticMappingStatus
from Compiler.primitives.native_binder import NativeSupportState
from Compiler.primitives.native_engine_effects import (
    NativeEffectKind,
    NativeStateDomain,
    default_native_engine_effect_catalog,
)
from Compiler.primitives.native_schema import load_default_native_schema
from Compiler.primitives.registry import default_de_registry


class NativeEngineEffectCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = default_native_engine_effect_catalog()
        self.native = load_default_native_schema()
        self.registry = default_de_registry()

    def test_control_plane_inventory_is_explicit_and_schema_backed(self):
        expected = {
            "set-goal",
            "goal",
            "up-compare-goal",
            "up-modify-goal",
            "set-strategic-number",
            "strategic-number",
            "up-compare-sn",
            "up-modify-sn",
            "enable-timer",
            "disable-timer",
            "timer-triggered",
            "up-set-timer",
            "up-timer-status",
            "disable-self",
            "up-jump-rule",
        }
        self.assertEqual(set(self.catalog.commands()), expected)
        self.catalog.validate_native_registry(self.native)

    def test_goal_effects_are_typed(self):
        self.assertEqual(
            self.catalog.require("set-goal").effect,
            NativeEffectKind.WRITE,
        )
        self.assertEqual(
            self.catalog.require("goal").effect,
            NativeEffectKind.READ,
        )
        self.assertTrue(
            self.catalog.require("up-compare-goal").typed_operand_dependency
        )
        self.assertEqual(
            self.catalog.require("up-modify-goal").native_kind,
            "Fact/Action",
        )

    def test_strategic_number_effects_distinguish_target_write_from_operand_read(self):
        modify = self.catalog.require("up-modify-sn")
        compare = self.catalog.require("up-compare-sn")
        self.assertEqual(modify.domain, NativeStateDomain.STRATEGIC_NUMBER)
        self.assertEqual(modify.effect, NativeEffectKind.WRITE)
        self.assertEqual(modify.identifier_arg, 0)
        self.assertTrue(modify.typed_operand_dependency)
        self.assertEqual(compare.effect, NativeEffectKind.READ)
        self.assertTrue(compare.typed_operand_dependency)

    def test_timer_effects_share_one_persistent_domain(self):
        for command in (
            "enable-timer",
            "disable-timer",
            "up-set-timer",
        ):
            effect = self.catalog.require(command)
            self.assertEqual(effect.domain, NativeStateDomain.TIMER)
            self.assertEqual(effect.effect, NativeEffectKind.WRITE)
            self.assertTrue(effect.persistent)
        for command in ("timer-triggered", "up-timer-status"):
            effect = self.catalog.require(command)
            self.assertEqual(effect.domain, NativeStateDomain.TIMER)
            self.assertEqual(effect.effect, NativeEffectKind.READ)

    def test_rule_control_effects_are_not_mistaken_for_persistent_value_state(self):
        disable_self = self.catalog.require("disable-self")
        jump = self.catalog.require("up-jump-rule")
        self.assertEqual(disable_self.domain, NativeStateDomain.RULE_CONTROL)
        self.assertEqual(disable_self.effect, NativeEffectKind.CONTROL)
        self.assertTrue(disable_self.persistent)
        self.assertFalse(disable_self.same_pass_visible)
        self.assertEqual(jump.domain, NativeStateDomain.RULE_CONTROL)
        self.assertEqual(jump.effect, NativeEffectKind.CONTROL)
        self.assertFalse(jump.persistent)
        self.assertTrue(jump.same_pass_visible)

    def test_all_control_plane_commands_have_evidence(self):
        for effect in self.catalog.contracts:
            self.assertTrue(effect.evidence_sources)
            self.assertTrue(effect.semantics)
            self.assertTrue(all(source.startswith(("http://", "https://", "repo://", "test://"))
                                for source in effect.evidence_sources))

    def test_support_state_promotes_mapped_control_plane_commands(self):
        for command in self.catalog.commands():
            assessment = self.registry.assess_support(command)
            expected = (
                NativeSupportState.EXECUTABLE_SAFE
                if self.registry.get(command) is not None
                else NativeSupportState.ENGINE_SEMANTICS_MAPPED
            )
            self.assertEqual(assessment.state, expected, command)

    def test_dual_fact_action_commands_are_schema_typed_but_not_falsely_promoted_to_primitive_safe(self):
        for command in ("up-modify-goal", "up-modify-sn"):
            assessment = self.registry.assess_support(command)
            self.assertEqual(
                assessment.state,
                NativeSupportState.ENGINE_SEMANTICS_MAPPED,
                command,
            )
            self.assertIsNone(assessment.binding)

    def test_existing_primitive_engine_mapping_contracts_remain_distinct(self):
        mapping = self.registry.require("can-build").engine_semantics_id
        self.assertIsNotNone(mapping)
        self.assertEqual(
            self.registry.assess_support("can-build").state,
            NativeSupportState.EXECUTABLE_SAFE,
        )
        self.assertEqual(
            self.registry.assess_support("can-build").binding.mapping_status,
            EngineSemanticMappingStatus.CONTRACTED,
        )


if __name__ == "__main__":
    unittest.main()
