import unittest
from dataclasses import replace

from LearnerAI.Compiler.ir.endgame import (
    EndgameMode,
    EndgamePolicyRule,
    EndgamePushState,
    EndgameRuntimeState,
    EndgameWinCondition,
    EndgamePlan,
    EndgameFrontierState,
    EndgamePushContract,
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

    def test_endgame_push_contract_is_bounded_and_frontier_ordered(self):
        contract = EndgamePushContract(
            identity="byzantine-endgame-push-v1",
            attack_group_count=1,
            attack_soldier_percent=100,
            minimum_group_size=6,
            maximum_group_size=40,
            live_witness_expression="(attack-soldier-count > 0)",
            frontier=(
                EndgameFrontierState.SIEGE,
                EndgameFrontierState.DEFENSE,
                EndgameFrontierState.PRODUCTION,
                EndgameFrontierState.TOWN_CENTER,
            ),
        )
        self.assertEqual(contract.attack_group_count, 1)
        self.assertEqual(contract.maximum_group_size, 40)
        self.assertEqual(
            contract.frontier,
            (
                EndgameFrontierState.SIEGE,
                EndgameFrontierState.DEFENSE,
                EndgameFrontierState.PRODUCTION,
                EndgameFrontierState.TOWN_CENTER,
            ),
        )
        with self.assertRaises(ValueError):
            EndgamePushContract(
                identity="bad",
                attack_group_count=0,
                attack_soldier_percent=100,
                minimum_group_size=6,
                maximum_group_size=40,
                live_witness_expression="(attack-soldier-count > 0)",
                frontier=contract.frontier,
            )

    def test_byzantine_stock_lowers_endgame_push_and_frontier_control(self):
        profile = build_byzantine_stock_strategy(self.effective)
        plan = profile.endgame_plan
        self.assertIsNotNone(plan)
        self.assertIsNotNone(plan.push_contract)
        compilation = lower_strategy_profile(profile, self.effective)

        self.assertIn(
            "byzantine-endgame-push-state",
            {state.identifier for state in compilation.control_plan.states},
        )
        self.assertIn(
            "byzantine-endgame-frontier",
            {state.identifier for state in compilation.control_plan.states},
        )
        rules = {rule.identity: rule for rule in compilation.control_plan.rules}
        for identity in (
            "byzantine-endgame-push-admit",
            "byzantine-endgame-push-release",
            "byzantine-endgame-frontier-defense",
            "byzantine-endgame-frontier-production",
            "byzantine-endgame-frontier-town-center",
        ):
            self.assertIn(identity, rules)

        attack_rules = {
            rule.identity: rule
            for rule in profile.attack_plan.rules
        }
        pulse = attack_rules["byzantine-imperial-attack-group-pulse"]
        self.assertIn(
            "(goal byzantine-endgame-push-state 1)",
            tuple(fact.source for fact in pulse.facts),
        )
        self.assertEqual(
            tuple(
                attachment.native_strategic_number_id
                for attachment in profile.attack_plan.strategic_number_action_attachments
            ),
            (36, 227, 16, 26),
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
