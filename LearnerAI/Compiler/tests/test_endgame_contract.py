import unittest
from dataclasses import replace

from LearnerAI.Compiler.ir.endgame import (
    EndgameMode,
    EndgamePolicyRule,
    EndgamePushState,
    EndgameRuntimeState,
    EndgameWinCondition,
    EndgamePlan,
)
from LearnerAI.Compiler.ir.civ_profile import ByzantineProfile, resolve_effective_civ
from LearnerAI.Compiler.ir.strategy import (
    StrategyEnvelope,
    StrategicObservationSpec,
    StrategyProfile,
    lower_strategy_profile,
)


class EndgameContractTests(unittest.TestCase):
    def setUp(self):
        self.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())

    def test_endgame_plan_requires_deterministic_policy_order(self):
        plan = EndgamePlan(
            identity="byzantine-endgame-v1",
            rules=(
                EndgamePolicyRule(
                    identity="breakthrough",
                    mode=EndgameMode.BREAKTHROUGH,
                    win_condition=EndgameWinCondition.CAPABILITY_COLLAPSE,
                    observation_refs=("army-ready",),
                    priority=100,
                ),
                EndgamePolicyRule(
                    identity="resource-denial",
                    mode=EndgameMode.RESOURCE_DENIAL,
                    win_condition=EndgameWinCondition.RESOURCE_CONTROL,
                    observation_refs=("enemy-gold-access",),
                    priority=80,
                ),
            ),
            objective_priority=("siege", "defense", "production", "economy", "town-center"),
        )
        self.assertEqual(
            tuple(rule.identity for rule in plan.rules),
            ("breakthrough", "resource-denial"),
        )
        with self.assertRaises(ValueError):
            EndgamePlan(
                identity="byzantine-endgame-v1",
                rules=tuple(reversed(plan.rules)),
                objective_priority=plan.objective_priority,
            )
        self.assertEqual(
            plan.push_states,
            (
                EndgamePushState.FORMING,
                EndgamePushState.READY,
                EndgamePushState.EXECUTING,
                EndgamePushState.WITNESS,
                EndgamePushState.ADVANCE,
                EndgamePushState.RECOVERY,
            ),
        )

    def test_endgame_runtime_recovery_requires_recovery_push_state(self):
        with self.assertRaises(ValueError):
            EndgameRuntimeState(
                mode=EndgameMode.RECOVERY,
                win_condition=EndgameWinCondition.CAPABILITY_COLLAPSE,
                push_state=EndgamePushState.READY,
                frontier_valid=True,
                recovery_required=True,
            )

    def test_endgame_plan_rejects_unknown_observation(self):
        plan = EndgamePlan(
            identity="byzantine-endgame-v1",
            rules=(
                EndgamePolicyRule(
                    identity="breakthrough",
                    mode=EndgameMode.BREAKTHROUGH,
                    win_condition=EndgameWinCondition.CAPABILITY_COLLAPSE,
                    observation_refs=("missing-observation",),
                    priority=100,
                ),
            ),
            objective_priority=("siege", "defense", "production", "town-center"),
        )
        with self.assertRaises(ValueError):
            from LearnerAI.Compiler.ir.endgame import validate_endgame_plan

            validate_endgame_plan(plan)

    def test_endgame_plan_can_be_attached_to_and_lowered_with_strategy_profile(self):
        base = StrategyProfile(
            profile_id="test-profile",
            civ_id=self.effective.civ_id,
            patch_key=self.effective.patch.key,
            effective_snapshot_fingerprint=self.effective.fingerprint,
            envelope=StrategyEnvelope("1v1", "standard", ("arabia",)),
            postures=(),
            demands=(),
            transitions=(),
            provenance=(),
            observations=(
                StrategicObservationSpec(
                    identity="army-ready",
                    expression="(current-age >= imperial-age)",
                ),
            ),
        )
        plan = EndgamePlan(
            identity="byzantine-endgame-v1",
            rules=(
                EndgamePolicyRule(
                    identity="breakthrough",
                    mode=EndgameMode.BREAKTHROUGH,
                    win_condition=EndgameWinCondition.CAPABILITY_COLLAPSE,
                    observation_refs=("army-ready",),
                    priority=100,
                ),
            ),
            objective_priority=("siege", "defense", "production", "town-center"),
        )
        profile = replace(base, endgame_plan=plan)
        compilation = lower_strategy_profile(profile, self.effective)
        self.assertIs(compilation.endgame_plan, plan)


if __name__ == "__main__":
    unittest.main()
