"""Strategy-owned posture/age Strategic Number mode synthesis."""
import unittest
from dataclasses import replace

from Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_castle_strategy,
    compile_strategy_profile,
)
from Compiler.ir.civ_profile import resolve_effective_civ
from Compiler.ir.game_data import Age
from Compiler.ir.strategy import (
    StrategicNumberMode,
    StrategicNumberReassertionPolicy,
    StrategyPosture,
    lower_strategy_profile,
)


class StrategyStrategicNumberModeTests(unittest.TestCase):
    def _profile(self):
        effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        return effective, build_byzantine_castle_strategy(effective)

    def test_age_mode_lowers_documented_native_sn_into_deterministic_guarded_rules(self):
        effective, profile = self._profile()
        profile = replace(
            profile,
            strategic_number_modes=(
                StrategicNumberMode(
                    "builders-dark",
                    native_strategic_number_id=4,
                    value=3,
                    minimum_age=Age.DARK,
                    maximum_age=Age.DARK,
                ),
                StrategicNumberMode(
                    "builders-feudal",
                    native_strategic_number_id=4,
                    value=5,
                    minimum_age=Age.FEUDAL,
                    maximum_age=Age.FEUDAL,
                ),
            ),
        )

        first = lower_strategy_profile(profile, effective)
        second = lower_strategy_profile(profile, effective)

        self.assertEqual(first.control_plan, second.control_plan)
        self.assertIsNotNone(first.control_plan)
        plan = first.control_plan
        assert plan is not None
        self.assertEqual(
            tuple(state.identifier for state in plan.states if state.identifier.startswith("sn-mode-")),
            ("sn-mode-builders-dark", "sn-mode-builders-feudal"),
        )
        rules = {
            rule.identity: rule
            for rule in plan.rules
            if rule.identity.startswith("sn-mode-")
        }
        self.assertEqual(
            rules["sn-mode-builders-dark-000"].actions[0].source,
            "(set-strategic-number sn-mode-builders-dark 3)",
        )
        self.assertIn("(current-age == dark-age)", rules["sn-mode-builders-dark-000"].facts[0].source)
        self.assertIn("(up-compare-sn sn-mode-builders-dark != 3)", rules["sn-mode-builders-dark-000"].facts[0].source)
        self.assertEqual(
            rules["sn-mode-builders-feudal-001"].actions[0].source,
            "(set-strategic-number sn-mode-builders-feudal 5)",
        )
        self.assertIn("(current-age == feudal-age)", rules["sn-mode-builders-feudal-001"].facts[0].source)

    def test_posture_mode_lowers_against_persistent_strategy_posture_and_reasserts_only_on_drift(self):
        effective, profile = self._profile()
        profile = replace(
            profile,
            strategic_number_modes=(
                StrategicNumberMode(
                    "attack-allocation-flush",
                    native_strategic_number_id=227,
                    value=50,
                    minimum_age=Age.FEUDAL,
                    postures=(StrategyPosture.FLUSH,),
                    reassertion_policy=StrategicNumberReassertionPolicy.ON_DRIFT,
                ),
                StrategicNumberMode(
                    "attack-allocation-boom",
                    native_strategic_number_id=227,
                    value=75,
                    minimum_age=Age.FEUDAL,
                    postures=(StrategyPosture.BOOM,),
                    reassertion_policy=StrategicNumberReassertionPolicy.ON_DRIFT,
                ),
            ),
        )

        compilation = lower_strategy_profile(profile, effective)
        self.assertIsNotNone(compilation.control_plan)
        plan = compilation.control_plan
        assert plan is not None

        self.assertIn("strategy-posture", tuple(state.identifier for state in plan.states))
        rules = {
            rule.identity: rule
            for rule in plan.rules
            if rule.identity.startswith("sn-mode-attack-allocation")
        }
        flush = rules["sn-mode-attack-allocation-flush-000"]
        boom = rules["sn-mode-attack-allocation-boom-001"]

        self.assertIn("(goal strategy-posture 1)", flush.facts[0].source)
        self.assertIn("(current-age >= feudal-age)", flush.facts[0].source)
        self.assertIn("(up-compare-sn sn-mode-attack-allocation-flush != 50)", flush.facts[0].source)
        self.assertEqual(
            flush.actions[0].source,
            "(set-strategic-number sn-mode-attack-allocation-flush 50)",
        )
        self.assertIn("(goal strategy-posture 3)", boom.facts[0].source)
        self.assertIn("(up-compare-sn sn-mode-attack-allocation-boom != 75)", boom.facts[0].source)

    def test_overlap_for_same_native_sn_is_rejected(self):
        effective, profile = self._profile()
        profile = replace(
            profile,
            strategic_number_modes=(
                StrategicNumberMode(
                    "builders-a",
                    native_strategic_number_id=4,
                    value=3,
                    minimum_age=Age.FEUDAL,
                ),
                StrategicNumberMode(
                    "builders-b",
                    native_strategic_number_id=4,
                    value=5,
                    minimum_age=Age.FEUDAL,
                ),
            ),
        )

        with self.assertRaisesRegex(ValueError, "overlapping Strategic Number modes"):
            lower_strategy_profile(profile, effective)

    def test_undocumented_native_sn_mode_is_rejected(self):
        effective, profile = self._profile()
        profile = replace(
            profile,
            strategic_number_modes=(
                StrategicNumberMode(
                    "invalid",
                    native_strategic_number_id=510,
                    value=5,
                    minimum_age=Age.FEUDAL,
                ),
            ),
        )

        with self.assertRaisesRegex(ValueError, "DE-documented"):
            lower_strategy_profile(profile, effective)

    def test_compiler_emits_native_mode_aliases_without_fake_initialization(self):
        effective, profile = self._profile()
        profile = replace(
            profile,
            strategic_number_modes=(
                StrategicNumberMode(
                    "builders-dark",
                    native_strategic_number_id=4,
                    value=3,
                    minimum_age=Age.DARK,
                    maximum_age=Age.DARK,
                ),
            ),
        )

        first = compile_strategy_profile(profile, effective)
        second = compile_strategy_profile(profile, effective)

        self.assertEqual(first, second)
        self.assertIn("(defconst sn-mode-builders-dark 4)", first)
        self.assertIn("(set-strategic-number sn-mode-builders-dark 3)", first)
        self.assertIn("(up-compare-sn sn-mode-builders-dark != 3)", first)
        self.assertNotIn("(set-strategic-number sn-mode-builders-dark 0)", first)


if __name__ == "__main__":
    unittest.main()
