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
from LearnerAI.Compiler.ir.community_strategy_packs import build_byzantine_stock_strategy


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
            live_witness_ref="strategy-endgame-attack-package-live",
            cleared_witness_ref="strategy-endgame-attack-package-cleared",
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
                live_witness_ref="strategy-endgame-attack-package-live",
                cleared_witness_ref="strategy-endgame-attack-package-cleared",
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
        self.assertIn(
            "byzantine-endgame-frontier-witness",
            {state.identifier for state in compilation.control_plan.states},
        )
        rules = {rule.identity: rule for rule in compilation.control_plan.rules}
        for identity in (
            "byzantine-endgame-push-imperial-ready",
            "byzantine-endgame-push-admit",
            "byzantine-endgame-push-release",
            "byzantine-endgame-frontier-witness-defense",
            "byzantine-endgame-frontier-witness-production",
            "byzantine-endgame-frontier-witness-town-center",
            "byzantine-endgame-frontier-commit-defense",
            "byzantine-endgame-frontier-commit-production-from-siege",
            "byzantine-endgame-frontier-commit-town-center-from-production",
        ):
            self.assertIn(identity, rules)

        rules = {rule.identity: rule for rule in compilation.control_plan.rules}
        admit = rules["byzantine-endgame-push-admit"]
        self.assertIn(
            "(set-goal byzantine-endgame-push-state 2)",
            tuple(action.source for action in admit.actions),
        )
        self.assertIn(
            "(set-strategic-number sn-native-36 1)",
            tuple(action.source for action in admit.actions),
        )
        self.assertIn(
            "(set-strategic-number sn-native-227 100)",
            tuple(action.source for action in admit.actions),
        )
        frontier = rules["byzantine-endgame-frontier-witness-defense"]
        self.assertNotIn(
            "(goal byzantine-endgame-push-state 2)",
            tuple(fact.source for fact in frontier.facts),
        )
        self.assertIn(
            "(goal byzantine-offensive-objective-state byzantine-offensive-objective-state-witness)",
            tuple(fact.source for fact in frontier.facts),
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

    def test_endgame_push_witness_refs_are_part_of_plan_observation_contract(self):
        plan = EndgamePlan(
            identity="byzantine-endgame-v1",
            rules=(
                EndgamePolicyRule(
                    identity="breakthrough",
                    mode=EndgameMode.BREAKTHROUGH,
                    win_condition=EndgameWinCondition.CAPABILITY_COLLAPSE,
                    observation_refs=("strategy-imperial-spend-gold",),
                    priority=100,
                ),
            ),
            objective_priority=("siege", "defense", "production", "town-center"),
            push_contract=EndgamePushContract(
                identity="push",
                attack_group_count=1,
                attack_soldier_percent=100,
                minimum_group_size=6,
                maximum_group_size=40,
                live_witness_ref="live",
                cleared_witness_ref="cleared",
                frontier=(
                    EndgameFrontierState.SIEGE,
                    EndgameFrontierState.DEFENSE,
                    EndgameFrontierState.PRODUCTION,
                    EndgameFrontierState.TOWN_CENTER,
                ),
            ),
        )
        self.assertEqual(
            plan.observation_references,
            ("cleared", "live", "strategy-imperial-spend-gold"),
        )
        with self.assertRaisesRegex(ValueError, "cleared"):
            from LearnerAI.Compiler.ir.endgame import validate_endgame_plan
            validate_endgame_plan(
                plan,
                observation_ids=("strategy-imperial-spend-gold", "live"),
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
