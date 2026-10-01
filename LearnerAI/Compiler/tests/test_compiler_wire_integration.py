"""Compiler wire-integration regressions for strategy/runtime/native seams."""
from __future__ import annotations

import unittest

from LearnerAI.Compiler.clients.basilisk import ByzantineProfile, build_byzantine_castle_strategy
from LearnerAI.Compiler.clients.basilisk.compiler import compile_strategy_profile
from LearnerAI.Compiler.ir import (
    NativeAttackLifecyclePlan,
    NativeAttackRule,
    AttackLifecycleObservation,
)
from LearnerAI.Compiler.ir.strategy import StrategyPosture
from LearnerAI.Compiler.ir.strategy_runtime import (
    CompositionUpgradeReadiness,
    CompositionUpgradeReadinessState,
    RuntimeObservationSnapshot,
)
from LearnerAI.Compiler.ir.civ_profile import resolve_effective_civ
from LearnerAI.Compiler.ir.strategy import lower_strategy_profile
from LearnerAI.Compiler.ir.strategy_runtime import ReassessmentReason


class CompilerWireIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        self.profile = build_byzantine_castle_strategy(self.effective)

    def test_byzantine_infantry_counter_declares_logistica_readiness(self):
        package = next(
            item for item in self.profile.counter_packages
            if item.identity == "INFANTRY_PRESSURE_CASTLE"
        )
        self.assertEqual(len(package.upgrade_requirements), 1)
        requirement = package.upgrade_requirements[0]
        self.assertEqual(requirement.identity, "logistica")
        self.assertEqual(requirement.observation_ref, "byz-logistica-complete")
        self.assertEqual(requirement.technology_id, 61)

    def test_runtime_exposes_upgrade_readiness_and_change_reason(self):
        trigger = self.profile.observation("enemy-infantry-pressure").expression
        research = self.profile.observation("byz-logistica-complete").expression
        previous = CompositionUpgradeReadinessState(
            status=CompositionUpgradeReadiness.READY,
            selected_packages=("INFANTRY_PRESSURE_CASTLE",),
            requirements=(),
        )
        snapshot = RuntimeObservationSnapshot(
            fact_results=((trigger, True), (research, False)),
            previous_posture=StrategyPosture.CASTLE_POWER,
            previous_composition_upgrade_readiness=previous,
        )
        from LearnerAI.Compiler.ir.strategy_runtime import evaluate_strategy_runtime
        state = evaluate_strategy_runtime(self.profile, self.effective, snapshot)
        self.assertIsNotNone(state.composition_upgrade_readiness)
        self.assertEqual(
            state.composition_upgrade_readiness.status,
            CompositionUpgradeReadiness.BLOCKED,
        )
        self.assertIn(
            ReassessmentReason.UPGRADE_READINESS_CHANGE,
            state.reassessment_reasons,
        )

    def test_counter_demands_are_native_gated_by_arbitrated_package_state(self):
        compilation = lower_strategy_profile(self.profile, self.effective)
        demand = next(
            item for item in compilation.demands
            if item.name == "counter-mounted-spears"
        )
        sources = tuple(item.source for item in demand.requirements)
        self.assertIn(
            "(up-compare-goal counter-package-mounted_pressure_feudal c:== 1)",
            sources,
        )
        self.assertIn(
            "counter-package-mounted_pressure_feudal",
            tuple(state.identifier for state in compilation.control_plan.states),
        )

    def test_strategy_compile_accepts_and_emits_existing_attack_plan(self):
        lifecycle = (
            AttackLifecycleObservation.ADMISSION_REQUIRED,
            AttackLifecycleObservation.ISSUE,
            AttackLifecycleObservation.COMPLETION_UNOBSERVED,
            AttackLifecycleObservation.REASSESS_REQUIRED,
        )
        from LearnerAI.Compiler.ast import Expression
        plan = NativeAttackLifecyclePlan(
            rules=(
                NativeAttackRule(
                    identity="wire-test-attack",
                    order=1,
                    facts=(Expression("(true)", "true", ()),),
                    actions=(Expression("(attack-now)", "attack-now", ()),),
                    lifecycle=lifecycle,
                ),
            )
        )
        artifact = compile_strategy_profile(
            self.profile,
            self.effective,
            attack_plan=plan,
        )
        self.assertIn("; Native attack lifecycle plan", artifact)
        self.assertIn("(attack-now)", artifact)


if __name__ == "__main__":
    unittest.main()
