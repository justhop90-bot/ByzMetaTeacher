import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from LearnerAI.Compiler.clients.basilisk import (
    compile_strategy_profile,
    compile_strategy_runtime_profile,
)
from LearnerAI.Compiler.ast import Expression
from LearnerAI.Compiler.ir.civ_profile import resolve_effective_civ
from LearnerAI.Compiler.ir.game_data import Resource
from LearnerAI.Compiler.ir.native_duc import NativeDucPlan, NativeDucRule
from LearnerAI.Compiler.ir.strategy import StrategyPosture
from LearnerAI.Compiler.ir.strategy_runtime import RuntimeObservationSnapshot
from LearnerAI.Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_castle_strategy,
    lower_strategy_profile,
    build_byzantine_strategy,
)


class StrategyCompilerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        self.profile = build_byzantine_castle_strategy(self.effective)
        self.stock_profile = build_byzantine_strategy(self.effective)

    def test_protected_research_declares_explicit_escrow_resources(self):
        demand = self.profile.demand("feudal-transition")
        self.assertEqual(
            demand.execution.escrow_release_resources,
            (Resource.FOOD, Resource.GOLD),
        )

    def test_strategy_lowering_produces_targeted_escrow_release_plan(self):
        compilation = lower_strategy_profile(self.profile, self.effective)

        self.assertIsNotNone(compilation.escrow_plan)
        plan = compilation.escrow_plan
        assert plan is not None

        feudal_operations = tuple(
            operation
            for operation in plan.operations
            if operation.target_demand.local_name == "feudal-transition"
        )
        castle_operations = tuple(
            operation
            for operation in plan.operations
            if operation.target_demand.local_name == "castle-age-transition"
        )
        self.assertEqual(
            tuple(operation.resource for operation in feudal_operations),
            ("food", "gold"),
        )
        self.assertEqual(
            tuple(operation.resource for operation in castle_operations),
            ("food", "gold"),
        )
        self.assertTrue(
            all(operation.command == "release-escrow" for operation in plan.operations)
        )
        self.assertTrue(
            all(operation.command == "release-escrow" for operation in plan.operations)
        )

    def test_strategy_compiler_emits_castle_age_transition_and_priority_guards(self):
        output = compile_strategy_profile(self.stock_profile, self.effective)

        self.assertIn("demand-castle-age-transition", output)
        self.assertIn("(research castle-age)", output)
        self.assertIn(
            "(not (can-research-with-escrow castle-age))",
            output,
        )

        dba_start = output.index("; Action issuance: research-double-bit-axe")
        horse_start = output.index("; Action issuance: research-horse-collar")
        castle_start = output.index("(goal demand-castle-age-transition 1)")
        dba_block = output[dba_start:horse_start]
        self.assertIn(
            "(not (can-research-with-escrow castle-age))",
            dba_block,
        )
        self.assertLess(
            output.rfind("(can-research-with-escrow castle-age)", 0, castle_start + 1),
            castle_start,
        )

    def test_strategy_compiler_emits_protected_research_release_before_research(self):
        output = compile_strategy_profile(
            self.profile,
            self.effective,
        )
        action_start = output.index("; Action issuance: feudal-transition")
        action_block = output[action_start:]
        self.assertLess(
            action_block.index("(release-escrow food)"),
            action_block.index("(research feudal-age)"),
        )
        self.assertLess(
            action_block.index("(release-escrow gold)"),
            action_block.index("(research feudal-age)"),
        )

    def test_strategy_compilation_exposes_profile_and_override_duc_channels(self):
        profile_plan = NativeDucPlan(
            rules=(
                NativeDucRule(
                    identity="byzantine-duc-profile",
                    order=0,
                    facts=(Expression("(true)", "true", ()),),
                    actions=(
                        Expression(
                            "(up-full-reset-search)",
                            "up-full-reset-search",
                            (),
                        ),
                    ),
                ),
            )
        )
        override_plan = NativeDucPlan(
            rules=(
                NativeDucRule(
                    identity="byzantine-duc-override",
                    order=0,
                    facts=(Expression("(true)", "true", ()),),
                    actions=(
                        Expression(
                            "(up-full-reset-search)",
                            "up-full-reset-search",
                            (),
                        ),
                    ),
                ),
            )
        )
        profile = replace(self.profile, duc_plan=profile_plan)

        compilation = lower_strategy_profile(profile, self.effective)
        self.assertIs(compilation.duc_plan, profile_plan)

        default_output = compile_strategy_profile(profile, self.effective)
        self.assertIn("; Native DUC execution plan", default_output)
        self.assertIn("; Native DUC rule: byzantine-duc-profile", default_output)

        override_output = compile_strategy_profile(
            self.profile,
            self.effective,
            duc_plan=override_plan,
        )
        self.assertIn("; Native DUC rule: byzantine-duc-override", override_output)
        self.assertNotIn("; Native DUC rule: byzantine-duc-profile", override_output)

        runtime_output = compile_strategy_runtime_profile(
            profile,
            self.effective,
            RuntimeObservationSnapshot(previous_posture=StrategyPosture.CASTLE_POWER),
            duc_plan=override_plan,
        )
        self.assertIn("; Native DUC rule: byzantine-duc-override", runtime_output)

    def test_byzantine_strategy_lowers_default_duc_target_pipeline(self):
        compilation = lower_strategy_profile(self.profile, self.effective)

        self.assertIsNotNone(compilation.duc_plan)
        plan = compilation.duc_plan
        assert plan is not None
        self.assertEqual(
            tuple(rule.identity for rule in plan.rules),
            (
                "byzantine-castle-target-knight",
                "byzantine-castle-target-infantry",
            ),
        )
        self.assertEqual(
            tuple(item.source for item in plan.rules[0].facts),
            (
                "(current-age >= castle-age)",
                "(up-compare-sn 227 >= 75)",
                "(players-unit-type-count any-enemy knight >= 3)",
            ),
        )
        self.assertEqual(
            tuple(item.source for item in plan.rules[1].facts),
            (
                "(current-age >= castle-age)",
                "(up-compare-sn 227 >= 75)",
                "(players-unit-type-count any-enemy militia-line >= 5)",
            ),
        )
        self.assertEqual(
            tuple(item.head for item in plan.rules[0].actions[:3]),
            (
                "up-full-reset-search",
                "up-find-remote",
                "up-set-target-object",
            ),
        )
        self.assertEqual(
            tuple(item.head for item in plan.rules[1].actions[:3]),
            (
                "up-full-reset-search",
                "up-find-remote",
                "up-set-target-object",
            ),
        )
        self.assertTrue(
            all(
                any(
                    output.rule_identity == rule.identity
                    and output.command == "up-get-object-data"
                    for output in plan.output_requests
                )
                for rule in plan.rules
            )
        )

        output = compile_strategy_profile(self.profile, self.effective)
        self.assertIn("; Native DUC rule: byzantine-castle-target-knight", output)
        self.assertIn("(up-find-remote c: 38 c: 1)", output)
        self.assertIn("(up-set-target-object search-remote c: 0)", output)
        self.assertIn("; Native DUC rule: byzantine-castle-target-infantry", output)
        self.assertIn("(up-find-remote c: 74 c: 1)", output)

    def test_byzantine_stock_lowers_objective_control_state_and_ownership(self):
        compilation = lower_strategy_profile(self.stock_profile, self.effective)
        control = compilation.control_plan
        self.assertIsNotNone(control)
        assert control is not None

        state_ids = {state.identifier for state in control.states}
        for expected in (
            "byzantine-offensive-objective-state",
            "byzantine-offensive-objective-class",
            "byzantine-offensive-objective-point",
            "byzantine-offensive-objective-search",
            "byzantine-offensive-enemy-player",
            "byzantine-offensive-objective-claim",
            "byzantine-offensive-objective-timer",
        ):
            self.assertIn(expected, state_ids)

        constants = dict(control.constants)
        self.assertEqual(constants["byzantine-offensive-objective-state-idle"], 0)
        self.assertEqual(constants["byzantine-offensive-objective-state-witness"], 6)
        self.assertEqual(constants["byzantine-offensive-objective-class-town-center"], 4)

        initialize = next(
            rule for rule in control.rules
            if rule.identity == "byzantine-endgame-objective-initialize"
        )
        self.assertIn(
            "(set-goal byzantine-offensive-objective-claim 0)",
            tuple(action.source for action in initialize.actions),
        )

        output = compile_strategy_profile(self.stock_profile, self.effective)
        self.assertIn(
            "(defconst byzantine-offensive-objective-state-idle 0)",
            output,
        )
        self.assertIn(
            "(defconst byzantine-offensive-objective-class-town-center 4)",
            output,
        )
        self.assertIn(
            "(defconst byzantine-offensive-objective-claim ",
            output,
        )
        self.assertNotIn(
            "(up-target-objects 1 action-attack-move -1 -1)",
            output,
        )

    def test_byzantine_stock_lowers_frontier_target_control_through_duc(self):
        compilation = lower_strategy_profile(self.stock_profile, self.effective)

        self.assertIsNotNone(compilation.duc_plan)
        plan = compilation.duc_plan
        assert plan is not None

        target_rules = tuple(
            rule for rule in plan.rules
            if rule.identity.startswith("byzantine-endgame-target-")
        )
        self.assertEqual(len(target_rules), 18)
        for rule in target_rules:
            sources = tuple(fact.source for fact in rule.facts)
            self.assertIn("(goal byzantine-offensive-objective-claim 0)", sources)
            self.assertIn("(current-age >= imperial-age)", sources)
            actions = tuple(action.source for action in rule.actions)
            self.assertIn(
                "(up-set-target-point byzantine-offensive-objective-point)",
                actions,
            )
            self.assertIn("(up-filter-distance c: -1 c: 40)", actions)
            self.assertIn("(up-set-target-object search-remote c: 0)", actions)
            self.assertNotIn("(up-target-objects", " ".join(actions))
            self.assertNotIn("(attack-now)", " ".join(actions))
            self.assertFalse(
                any("set-strategic-number sn-native-36" in action for action in actions)
            )

        output = compile_strategy_profile(self.stock_profile, self.effective)
        self.assertIn(
            "(up-set-target-point byzantine-offensive-objective-point)",
            output,
        )
        self.assertIn("(up-filter-distance c: -1 c: 40)", output)
        self.assertIn("; Native DUC rule: byzantine-endgame-target-", output)

    def test_byzantine_endgame_push_is_a_bounded_attack_group_pulse(self):
        compilation = lower_strategy_profile(self.stock_profile, self.effective)

        self.assertIsNotNone(compilation.control_plan)
        control = compilation.control_plan
        assert control is not None

        state_ids = tuple(state.identifier for state in control.states)
        self.assertIn("byzantine-endgame-push-state", state_ids)
        self.assertIn("byzantine-endgame-push-timer", state_ids)

        rules = {
            rule.identity: rule
            for rule in control.rules
            if rule.identity.startswith("byzantine-endgame-push-")
        }
        self.assertIn("byzantine-endgame-push-admit", rules)
        self.assertIn("byzantine-endgame-push-live-witness", rules)
        self.assertIn("byzantine-endgame-push-pulse-expiry", rules)
        self.assertIn("byzantine-endgame-push-release", rules)

        admit_actions = tuple(action.source for action in rules["byzantine-endgame-push-admit"].actions)
        self.assertIn("(set-strategic-number sn-native-36 1)", admit_actions)
        self.assertIn("(set-strategic-number sn-native-227 100)", admit_actions)
        ready_actions = tuple(action.source for action in rules["byzantine-endgame-push-imperial-ready"].actions)
        self.assertIn("(set-strategic-number sn-native-16 6)", ready_actions)
        self.assertIn("(set-strategic-number sn-native-26 40)", ready_actions)
        self.assertIn("(enable-timer byzantine-endgame-push-timer 20)", admit_actions)

        live_actions = tuple(action.source for action in rules["byzantine-endgame-push-live-witness"].actions)
        self.assertIn("(set-strategic-number sn-native-36 0)", live_actions)
        self.assertIn("(set-strategic-number sn-native-227 75)", live_actions)
        self.assertIn("(disable-timer byzantine-endgame-push-timer)", live_actions)
        self.assertIn("(set-goal byzantine-endgame-push-state 3)", live_actions)

        expiry_actions = tuple(action.source for action in rules["byzantine-endgame-push-pulse-expiry"].actions)
        self.assertIn("(set-strategic-number sn-native-36 0)", expiry_actions)
        self.assertIn("(disable-timer byzantine-endgame-push-timer)", expiry_actions)
        self.assertIn("(set-goal byzantine-endgame-push-state 3)", expiry_actions)

        release_facts = tuple(fact.source for fact in rules["byzantine-endgame-push-release"].facts)
        self.assertIn("(goal byzantine-endgame-push-state 3)", release_facts)
        self.assertIn("(attack-soldier-count <= 0)", release_facts)
        self.assertIn("(unit-type-count cataphract >= 4)", " ".join(release_facts))

        release_actions = tuple(action.source for action in rules["byzantine-endgame-push-release"].actions)
        self.assertIn("(set-goal byzantine-endgame-push-state 1)", release_actions)

        output = compile_strategy_profile(self.stock_profile, self.effective)
        self.assertIn("(enable-timer byzantine-endgame-push-timer 20)", output)
        self.assertIn("(set-strategic-number sn-native-36 0)", output)

    def test_byzantine_endgame_closure_consumes_verified_campaign_state(self):
        compilation = lower_strategy_profile(self.stock_profile, self.effective)
        control = compilation.control_plan
        assert control is not None
        state_ids = tuple(state.identifier for state in control.states)
        self.assertIn("byzantine-endgame-mode", state_ids)
        self.assertIn("byzantine-endgame-win-condition", state_ids)
        rules = {rule.identity: rule for rule in control.rules}
        self.assertIn("byzantine-endgame-mode-recovery", rules)
        self.assertIn("byzantine-endgame-mode-resource-denial", rules)
        self.assertIn("byzantine-endgame-mode-attrition", rules)
        self.assertIn("byzantine-endgame-mode-breakthrough", rules)

        output = compile_strategy_profile(self.stock_profile, self.effective)
        self.assertIn("byzantine-endgame-frontier-verified", output)
        self.assertIn("byzantine-endgame-frontier-match", output)
        self.assertIn("byzantine-endgame-mode", output)
        self.assertIn("byzantine-endgame-win-condition", output)

        exact_frontier_match = "(goal byzantine-endgame-frontier-match 1)"
        for rule_id in (
            "byzantine-endgame-mode-recovery",
            "byzantine-endgame-mode-resource-denial",
            "byzantine-endgame-mode-attrition",
            "byzantine-endgame-mode-breakthrough",
        ):
            facts = tuple(fact.source for fact in rules[rule_id].facts)
            self.assertIn(exact_frontier_match, facts)

        conversion_demands = tuple(
            demand for demand in self.stock_profile.demands
            if demand.identity.startswith("imperial-forward-production-")
        )
        self.assertTrue(conversion_demands)
        self.assertTrue(
            all(demand.execution.action.startswith("(build ")
                    for demand in conversion_demands)
        )
        conversion_rules = tuple(
            rule for rule in control.rules
            if rule.identity.startswith("byzantine-endgame-conversion-admit-")
        )
        self.assertEqual(len(conversion_rules), len(conversion_demands))
        self.assertTrue(
            all(
                exact_frontier_match in tuple(fact.source for fact in rule.facts)
                for rule in conversion_rules
            )
        )

    def test_byzantine_strategy_lowers_attack_lifecycle_control_state_machine(self):
        compilation = lower_strategy_profile(self.profile, self.effective)

        self.assertIsNotNone(compilation.control_plan)
        control = compilation.control_plan
        assert control is not None
        state_ids = tuple(state.identifier for state in control.states)
        self.assertIn("byzantine-attack-phase", state_ids)

        rule_ids = tuple(
            rule.identity
            for rule in control.rules
            if rule.identity.startswith("byzantine-attack-phase-")
        )
        self.assertEqual(
            rule_ids,
            (
                "byzantine-attack-phase-initialize",
                "byzantine-attack-phase-prepare-cataphract",
                "byzantine-attack-phase-attack-cataphract",
                "byzantine-attack-phase-prepare-knight",
                "byzantine-attack-phase-attack-knight",
                "byzantine-attack-phase-complete-cataphract",
                "byzantine-attack-phase-complete-knight",
                "byzantine-attack-phase-recover-cataphract",
                "byzantine-attack-phase-recover-knight",
                "byzantine-attack-phase-reassess",
            ),
        )

        attack_plan = compilation.attack_plan
        assert attack_plan is not None
        self.assertIn(
            "(goal byzantine-attack-phase 2)",
            tuple(fact.source for fact in attack_plan.rules[0].facts),
        )
        self.assertIn(
            "(goal byzantine-attack-phase 4)",
            tuple(fact.source for fact in attack_plan.rules[1].facts),
        )

        output = compile_strategy_profile(self.profile, self.effective)
        self.assertIn("(defconst byzantine-attack-phase", output)
        self.assertIn(
            "(set-goal byzantine-attack-phase 1)",
            output,
        )
        self.assertIn(
            "(set-goal byzantine-attack-phase 2)",
            output,
        )
        self.assertIn(
            "(set-goal byzantine-attack-phase 0)",
            output,
        )

    def test_byzantine_strategy_lowers_default_attack_lifecycle(self):
        compilation = lower_strategy_profile(self.profile, self.effective)

        self.assertIsNotNone(compilation.attack_plan)
        plan = compilation.attack_plan
        assert plan is not None
        self.assertEqual(
            tuple(rule.identity for rule in plan.rules),
            (
                "byzantine-castle-attack-now-cataphract",
                "byzantine-castle-attack-now-knight",
            ),
        )
        self.assertEqual(
            tuple(item.source for item in plan.rules[0].facts),
            (
                "(current-age == castle-age)",
                "(up-compare-sn 227 >= 75)",
                "(or (goal byzantine-army-role-state byzantine-army-role-committed) "
                "(goal byzantine-army-role-state byzantine-army-role-raid-split))",
                "(unit-type-count cataphract >= 2)",
                "(goal byzantine-attack-phase 2)",
            ),
        )
        self.assertEqual(
            tuple(item.source for item in plan.rules[1].facts),
            (
                "(current-age == castle-age)",
                "(up-compare-sn 227 >= 75)",
                "(or (goal byzantine-army-role-state byzantine-army-role-committed) "
                "(goal byzantine-army-role-state byzantine-army-role-raid-split))",
                "(unit-type-count knight >= 3)",
                "(goal byzantine-attack-phase 4)",
            ),
        )
        self.assertEqual(plan.rules[0].actions[0].source, "(attack-now)")
        self.assertEqual(plan.rules[1].actions[0].source, "(attack-now)")

        first = compile_strategy_profile(self.profile, self.effective)
        second = compile_strategy_profile(self.profile, self.effective)
        self.assertEqual(first, second)
        self.assertIn("; Native attack lifecycle plan", first)
        self.assertIn("; Native attack rule: byzantine-castle-attack-now-cataphract", first)
        self.assertIn("; Native attack rule: byzantine-castle-attack-now-knight", first)
        self.assertIn("(attack-now)", first)

    def test_runtime_strategy_uses_the_same_default_attack_plan_channel(self):
        snapshot = RuntimeObservationSnapshot(
            previous_posture=StrategyPosture.CASTLE_POWER,
        )
        output = compile_strategy_runtime_profile(
            self.profile,
            self.effective,
            snapshot,
        )
        self.assertIn("; Native attack lifecycle plan", output)
        self.assertIn("; Native attack rule: byzantine-castle-attack-now-cataphract", output)
        self.assertIn("; Native attack rule: byzantine-castle-attack-now-knight", output)
        self.assertIn("(current-age == castle-age)", output)
        self.assertIn("(attack-now)", output)

    def test_stock_strategy_compiles_role_separation_and_role_gated_attack_plan(self):
        output = compile_strategy_profile(
            self.stock_profile,
            self.effective,
        )

        self.assertIn("; Native Byzantine role-separation plan", output)
        self.assertIn("; Native role rule: role-forming-screen", output)
        self.assertIn("; Native role rule: role-recovery-to-idle", output)
        self.assertNotIn("; Native control rule: byzantine-role-recovery-bridge", output)
        self.assertIn(
            "(or (goal byzantine-army-role-state byzantine-army-role-committed) "
            "(goal byzantine-army-role-state byzantine-army-role-raid-split))",
            output,
        )

    def test_strategy_profile_compiles_through_existing_semantic_pipeline(self):
        output = compile_strategy_profile(
            self.profile,
            self.effective,
        )

        self.assertIn("(build castle)", output)
        self.assertIn("(train spearman-line)", output)
        self.assertIn("demand-castle-commitment", output)

    def test_strategy_lowering_does_not_create_second_lifecycle(self):
        compilation = lower_strategy_profile(self.profile, self.effective)

        self.assertEqual(
            len([d for d in compilation.demands if d.name == "castle-commitment"]),
            1,
        )
        self.assertIsNotNone(
            compilation.bindings["castle-commitment"].opportunity_cost
        )


if __name__ == "__main__":
    unittest.main()
