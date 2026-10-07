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
from LearnerAI.Compiler.ir.model import GoalSpanKind
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

    def test_stock_strategy_lowers_feudal_resource_island_duc_target_handoff(self):
        compilation = lower_strategy_profile(self.stock_profile, self.effective)
        plan = compilation.duc_plan
        self.assertIsNotNone(plan)
        assert plan is not None

        rule_ids = tuple(rule.identity for rule in plan.rules)
        self.assertIn("byzantine-feudal-resource-island-search-reset", rule_ids)
        self.assertIn("byzantine-feudal-resource-island-gold", rule_ids)

        discover = next(
            rule for rule in plan.rules
            if rule.identity == "byzantine-feudal-resource-island-gold"
        )
        facts = tuple(fact.source for fact in discover.facts)
        actions = tuple(action.source for action in discover.actions)
        self.assertIn("(current-age >= feudal-age)", facts)
        self.assertIn("(goal feudal-resource-island-transport-objective 1)", facts)
        self.assertIn("(unit-type-count-total transport-ship >= 1)", facts)
        self.assertIn("(goal feudal-resource-island-target-state 0)", facts)
        self.assertIn("(up-find-resource c: gold c: 40)", facts)
        self.assertIn(
            "(up-set-target-object search-remote c: 0)",
            actions,
        )
        self.assertIn(
            "(up-get-point position-object feudal-resource-island-gold-point)",
            actions,
        )
        self.assertIn(
            "(set-goal feudal-resource-island-target-state 1)",
            actions,
        )
        self.assertNotIn("up-target-objects", " ".join(actions))

        point_outputs = tuple(
            request for request in plan.output_requests
            if request.rule_identity == discover.identity
            and request.command == "up-get-point"
        )
        self.assertEqual(len(point_outputs), 1)
        self.assertEqual(point_outputs[0].expression_index, 1)
        self.assertEqual(point_outputs[0].argument_index, 1)
        self.assertEqual(point_outputs[0].request.width, 2)
        self.assertEqual(point_outputs[0].request.shape, GoalSpanKind.POINT_PAIR)
        self.assertEqual(point_outputs[0].request.contract_id, "up-get-point.Point")

        transport = self.stock_profile.demand("water-transport-capability")
        self.assertIn("(can-train-with-escrow transport-ship)", transport.execution.requirements)

        first = compile_strategy_profile(self.stock_profile, self.effective)
        second = compile_strategy_profile(self.stock_profile, self.effective)
        self.assertEqual(first, second)
    def test_strategy_compiler_emits_native_strategos_voice_plan(self):
        first = compile_strategy_profile(self.stock_profile, self.effective)
        second = compile_strategy_profile(self.stock_profile, self.effective)

        self.assertEqual(first, second)
        voice_start = first.index("; Native Strategos voice plan")
        voice = first[voice_start:]
        self.assertIn("(defconst voice-global-lock ", voice)
        self.assertIn("(defconst voice-match-count ", voice)
        self.assertIn("(defconst voice-global-cooldown ", voice)
        self.assertIn(
            '(chat-to-player focus-player "The army is ready. I am going in.")',
            voice,
        )
        self.assertIn("(up-jump-rule 13)", voice)
        self.assertNotIn("chat-local-to-self", voice)
        self.assertIn("(goal voice-latch-attack-issued 0)", voice)
        self.assertIn("(goal voice-latch-attack-issued 2)", voice)
        self.assertIn(
            "(up-compare-goal voice-match-count g:< 48)",
            voice,
        )
        self.assertNotIn("(goal voice-match-count < 48)", voice)

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
            "byzantine-fortification-threat",
            "byzantine-offensive-objective-target-latch",
            "byzantine-offensive-objective-target-siege",
            "byzantine-offensive-objective-target-defense",
            "byzantine-offensive-objective-target-production",
            "byzantine-offensive-objective-target-town-center",
            "byzantine-offensive-objective-witness-target",
            "byzantine-offensive-objective-release-reason",
            "byzantine-offensive-objective-release-search",
            "byzantine-offensive-objective-timer",
        ):
            self.assertIn(expected, state_ids)

        constants = dict(control.constants)
        self.assertEqual(constants["byzantine-offensive-objective-state-idle"], 0)
        self.assertEqual(constants["byzantine-offensive-objective-state-witness"], 6)
        self.assertEqual(constants["byzantine-offensive-objective-class-town-center"], 4)
        self.assertEqual(constants["byzantine-offensive-objective-release-reason-none"], 0)
        self.assertEqual(constants["byzantine-offensive-objective-release-reason-completed"], 1)
        self.assertEqual(constants["byzantine-offensive-objective-release-reason-lost-out-of-bounds"], 2)
        self.assertEqual(constants["byzantine-offensive-objective-release-reason-failed-execution"], 3)
        self.assertEqual(constants["byzantine-offensive-objective-release-reason-fortification-abort"], 4)
        self.assertEqual(constants["byzantine-offensive-objective-release-reason-tc-exhausted"], 5)

        initialize = next(
            rule for rule in control.rules
            if rule.identity == "byzantine-endgame-objective-initialize"
        )
        self.assertIn(
            "(set-goal byzantine-offensive-objective-claim 0)",
            tuple(action.source for action in initialize.actions),
        )
        self.assertIn(
            "(set-goal byzantine-offensive-objective-release-reason 0)",
            tuple(action.source for action in initialize.actions),
        )
        states_by_id = {state.identifier: state for state in control.states}
        self.assertEqual(states_by_id["byzantine-offensive-objective-witness-target"].request.role.value, "NATIVE_OUTPUT")
        self.assertEqual(states_by_id["byzantine-offensive-objective-release-search"].request.width, 4)
        self.assertEqual(states_by_id["byzantine-offensive-objective-release-search"].request.role.value, "NATIVE_OUTPUT")
        self.assertEqual(states_by_id["byzantine-offensive-objective-release-reason"].request.role.value, "PERSISTENT_STATE")

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
        self.assertEqual(
            output.count("(up-target-objects 1 action-attack-move -1 -1)"),
            4,
        )
        self.assertEqual(output.count("(defconst action-attack-move 19)"), 1)

    def test_byzantine_endgame_objective_target_control_is_class_priority_and_fail_closed(self):
        compilation = lower_strategy_profile(self.stock_profile, self.effective)
        control = compilation.control_plan
        duc = compilation.duc_plan
        assert control is not None
        assert duc is not None

        admit = next(rule for rule in control.rules if rule.identity == "byzantine-endgame-objective-admit")
        admit_facts = tuple(fact.source for fact in admit.facts)
        admit_actions = tuple(action.source for action in admit.actions)
        self.assertIn("(current-age >= castle-age)", admit_facts)
        self.assertIn(
            "(goal byzantine-endgame-push-state 1)",
            admit_facts,
        )
        self.assertIn("(goal byzantine-army-attack-ready 1)", admit_facts)
        self.assertIn("(goal byzantine-siege-approach byzantine-siege-approach-normal)", admit_facts)
        self.assertIn("(set-goal byzantine-offensive-objective-claim 1)", admit_actions)
        self.assertIn(
            "(set-goal byzantine-offensive-objective-state "
            "byzantine-offensive-objective-state-siege)",
            admit_actions,
        )

        target_rules = {
            rule.identity: rule
            for rule in duc.rules
            if rule.identity.startswith("byzantine-endgame-objective-target-")
        }
        expected = {
            "byzantine-endgame-objective-target-siege": (36, 331, 42, 913),
            "byzantine-endgame-objective-target-defense": (82, 235, 236, 952, 927),
            "byzantine-endgame-objective-target-production": (49, 12, 87, 101, 104, 83),
            "byzantine-endgame-objective-target-town-center": (109, 71, 141, 142),
        }
        for identity, native_ids in expected.items():
            self.assertIn(identity, target_rules)
            facts = tuple(fact.source for fact in target_rules[identity].facts)
            self.assertIn(
                "(goal byzantine-offensive-objective-claim 1)",
                facts,
            )
            self.assertIn(
                "(goal byzantine-offensive-objective-claim 1)",
                facts,
            )
            actions = tuple(action.source for action in target_rules[identity].actions)
            self.assertIn("(up-set-target-point byzantine-offensive-objective-point)", actions)
            self.assertIn("(up-filter-distance c: -1 c: 40)", actions)
            remote = tuple(
                int(action.split("c: ", 1)[1].split(" ", 1)[0])
                for action in actions
                if action.startswith("(up-find-remote c: ")
            )
            self.assertEqual(remote, native_ids)
            self.assertEqual(actions[-2:], (
                "(up-set-target-object search-remote c: 0)",
                "(up-get-object-data id 0)",
            ))
            matching_outputs = tuple(
                request
                for request in duc.output_requests
                if request.rule_identity == identity
            )
            self.assertEqual(len(matching_outputs), 1)
            self.assertEqual(matching_outputs[0].command, "up-get-object-data")
            self.assertEqual(
                matching_outputs[0].expression_index,
                4 + len(native_ids),
            )

        misses = {
            rule.identity: tuple(action.source for action in rule.actions)
            for rule in control.rules
            if rule.identity.startswith("byzantine-endgame-objective-target-miss-")
        }
        self.assertIn(
            "(set-goal byzantine-offensive-objective-release-reason "
            "byzantine-offensive-objective-release-reason-tc-exhausted)",
            misses["byzantine-endgame-objective-target-miss-town-center"],
        )
        dispatch_rules = {
            rule.identity: rule
            for rule in duc.rules
            if rule.identity.startswith("byzantine-endgame-objective-dispatch-")
        }
        self.assertEqual(
            set(dispatch_rules),
            {
                "byzantine-endgame-objective-dispatch-siege",
                "byzantine-endgame-objective-dispatch-defense",
                "byzantine-endgame-objective-dispatch-production",
                "byzantine-endgame-objective-dispatch-town-center",
            },
        )
        for identity, target_goal in (
            (
                "byzantine-endgame-objective-dispatch-siege",
                "byzantine-offensive-objective-target-siege",
            ),
            (
                "byzantine-endgame-objective-dispatch-defense",
                "byzantine-offensive-objective-target-defense",
            ),
            (
                "byzantine-endgame-objective-dispatch-production",
                "byzantine-offensive-objective-target-production",
            ),
            (
                "byzantine-endgame-objective-dispatch-town-center",
                "byzantine-offensive-objective-target-town-center",
            ),
        ):
            facts = tuple(fact.source for fact in dispatch_rules[identity].facts)
            actions = tuple(action.source for action in dispatch_rules[identity].actions)
            self.assertIn(
                f"(up-compare-goal {target_goal} >= 1)",
                facts,
            )
            self.assertIn(
                "(goal byzantine-army-attack-ready 1)",
                facts,
            )
            self.assertIn(
                "(goal byzantine-offensive-objective-state "
                "byzantine-offensive-objective-state-executing)",
                facts,
            )
            self.assertIn(
                "(up-target-objects 1 action-attack-move -1 -1)",
                actions,
            )
            self.assertNotIn("up-modify-sn sn-focus-player-number", " ".join(actions))
            self.assertNotIn("(disable-timer ", " ".join(actions))
            self.assertNotIn("(enable-timer ", " ".join(actions))
            point_outputs = tuple(
                request
                for request in duc.output_requests
                if request.rule_identity == identity
                and request.command == "up-get-point"
            )
            self.assertEqual(len(point_outputs), 1)
            self.assertEqual(point_outputs[0].expression_index, 1)
            self.assertEqual(point_outputs[0].argument_index, 1)
            self.assertEqual(point_outputs[0].request.width, 2)
            self.assertEqual(point_outputs[0].request.shape, GoalSpanKind.POINT_PAIR)
            self.assertEqual(point_outputs[0].request.contract_id, "up-get-point.Point")

    def test_byzantine_endgame_objective_witness_release_lifecycle(self):
        compilation = lower_strategy_profile(self.stock_profile, self.effective)
        control = compilation.control_plan
        duc = compilation.duc_plan
        assert control is not None
        assert duc is not None

        rules = {rule.identity: rule for rule in control.rules}
        dispatch_rules = {rule.identity: rule for rule in duc.rules}
        for identity in (
            "byzantine-endgame-objective-dispatch-siege",
            "byzantine-endgame-objective-dispatch-defense",
            "byzantine-endgame-objective-dispatch-production",
            "byzantine-endgame-objective-dispatch-town-center",
        ):
            self.assertIn(identity, dispatch_rules)
            self.assertIn(
                "(up-target-objects 1 action-attack-move -1 -1)",
                tuple(action.source for action in dispatch_rules[identity].actions),
            )
        for identity in (
            "byzantine-endgame-objective-enter-executing-siege",
            "byzantine-endgame-objective-enter-executing-defense",
            "byzantine-endgame-objective-enter-executing-production",
            "byzantine-endgame-objective-enter-executing-town-center",
        ):
            self.assertIn(identity, rules)
        for identity in (
            "byzantine-endgame-objective-admit",
            "byzantine-endgame-objective-target-miss-siege",
            "byzantine-endgame-objective-target-miss-defense",
            "byzantine-endgame-objective-target-miss-production",
            "byzantine-endgame-objective-target-miss-town-center",
            "byzantine-endgame-objective-executing-to-witness",
            "byzantine-endgame-objective-witness-live-rearm",
            "byzantine-endgame-objective-witness-failed-execution",
            "byzantine-endgame-objective-witness-town-center-exhausted",
            "byzantine-endgame-objective-witness-lost-out-of-bounds",
            "byzantine-endgame-objective-fortification-abort",
        ):
            self.assertIn(identity, rules)

        release_actions = {
            identity: tuple(action.source for action in rules[identity].actions)
            for identity in (
                "byzantine-endgame-objective-witness-failed-execution",
                "byzantine-endgame-objective-witness-town-center-exhausted",
                "byzantine-endgame-objective-witness-lost-out-of-bounds",
                "byzantine-endgame-objective-fortification-abort",
            )
        }
        self.assertIn(
            "(set-goal byzantine-offensive-objective-release-reason "
            "byzantine-offensive-objective-release-reason-failed-execution)",
            release_actions["byzantine-endgame-objective-witness-failed-execution"],
        )
        self.assertIn(
            "(set-goal byzantine-offensive-objective-release-reason "
            "byzantine-offensive-objective-release-reason-tc-exhausted)",
            release_actions["byzantine-endgame-objective-witness-town-center-exhausted"],
        )
        self.assertIn(
            "(set-goal byzantine-offensive-objective-release-reason "
            "byzantine-offensive-objective-release-reason-lost-out-of-bounds)",
            release_actions["byzantine-endgame-objective-witness-lost-out-of-bounds"],
        )
        self.assertIn(
            "(set-goal byzantine-offensive-objective-release-reason "
            "byzantine-offensive-objective-release-reason-fortification-abort)",
            release_actions["byzantine-endgame-objective-fortification-abort"],
        )

        witness_search = tuple(
            rule for rule in duc.rules
            if rule.identity.startswith("byzantine-endgame-objective-witness-")
            and rule.identity.endswith("-search")
        )
        self.assertEqual(len(witness_search), 4)
        for rule in witness_search:
            facts = tuple(fact.source for fact in rule.facts)
            actions = tuple(action.source for action in rule.actions)
            self.assertIn(
                "(goal byzantine-offensive-objective-state "
                "byzantine-offensive-objective-state-witness)",
                facts,
            )
            self.assertIn(
                "(goal byzantine-offensive-objective-claim 1)",
                facts,
            )
            self.assertIn(
                "(up-filter-distance c: 0 c: 60)",
                actions,
            )
            self.assertIn("(up-find-remote", " ".join(actions))
            self.assertNotIn("up-modify-sn sn-focus-player-number", " ".join(actions))
            self.assertNotIn("(up-target-objects", " ".join(actions))

        consumer = next(
            rule for rule in duc.rules
            if rule.identity == "byzantine-endgame-objective-witness-consume"
        )
        self.assertIn(
            "(up-set-target-object search-remote c: 0)",
            tuple(fact.source for fact in consumer.facts),
        )
        consumer_actions = tuple(action.source for action in consumer.actions)
        self.assertEqual(
            consumer_actions,
            (
                "(up-get-object-data id 0)",
                "(up-get-search-state byzantine-offensive-objective-release-search)",
                "(up-reset-search 0 0 1 1)",
            ),
        )
        output_sites = {
            (request.rule_identity, request.section, request.expression_index, request.command)
            for request in duc.output_requests
            if request.rule_identity == "byzantine-endgame-objective-witness-consume"
        }
        self.assertEqual(
            output_sites,
            {
                (
                    "byzantine-endgame-objective-witness-consume",
                    "ACTION",
                    0,
                    "up-get-object-data",
                ),
                (
                    "byzantine-endgame-objective-witness-consume",
                    "ACTION",
                    1,
                    "up-get-search-state",
                ),
            },
        )

        output = compile_strategy_profile(self.stock_profile, self.effective)
        self.assertIn(
            "; Native DUC rule: byzantine-endgame-objective-witness-consume",
            output,
        )
        self.assertIn(
            "(up-get-search-state ",
            output,
        )
        self.assertNotIn(
            "(set-goal byzantine-offensive-objective-state "
            "byzantine-offensive-objective-state-executing)",
            output.split("; Native DUC execution plan", 1)[1].split(
                "; Native attack lifecycle plan", 1
            )[0],
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
        self.assertEqual(len(target_rules), 19)
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


    def test_byzantine_stock_lowers_imperial_band_controller_and_attack_floor(self):
        compilation = lower_strategy_profile(self.stock_profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        state_ids = {state.identifier for state in control.states}
        for expected in (
            "byzantine-imperial-band-state",
            "byzantine-imperial-band-candidate",
            "byzantine-imperial-band-rearm",
            "byzantine-imperial-band-reason",
            "byzantine-imperial-band-dwell-timer",
            "byzantine-imperial-band-guard-timer",
            "byzantine-imperial-band-rearm-timer",
        ):
            self.assertIn(expected, state_ids)

        constants = dict(control.constants)
        self.assertEqual(constants["bt-imp-band-standing"], 0)
        self.assertEqual(constants["bt-imp-band-open"], 1)
        self.assertEqual(constants["bt-imp-band-fortified"], 2)
        self.assertEqual(constants["bt-imp-band-trash"], 3)

        rules = {rule.identity: rule for rule in control.rules}
        open_candidate_facts = tuple(
            fact.source for fact in rules["byzantine-imperial-band-standing-open-candidate"].facts
        )
        self.assertIn("(goal byzantine-offensive-objective-claim 1)", open_candidate_facts)

        trash_open_candidate_facts = tuple(
            fact.source for fact in rules["byzantine-imperial-band-trash-open-candidate"].facts
        )
        self.assertIn("(goal byzantine-offensive-objective-claim 1)", trash_open_candidate_facts)

        standing_trash_candidate_facts = tuple(
            fact.source
            for fact in rules["byzantine-imperial-band-standing-trash-candidate"].facts
        )
        self.assertIn("(gold-amount <= 800)", standing_trash_candidate_facts)
        self.assertNotIn("(gold-amount >= 1600)", standing_trash_candidate_facts)

        transition_trash_facts = tuple(
            fact.source
            for fact in rules["byzantine-imperial-band-transition-trash"].facts
        )
        self.assertIn("(gold-amount <= 800)", transition_trash_facts)
        self.assertNotIn("(gold-amount >= 1600)", transition_trash_facts)

        trash_clear_facts = tuple(
            fact.source
            for identity, rule in rules.items()
            if identity.startswith("byzantine-imperial-band-clear-trash-candidate")
            for fact in rule.facts
        )
        self.assertNotIn("(gold-amount < 1600)", trash_clear_facts)

        fortified_open_candidate_facts = tuple(
            fact.source for fact in rules["byzantine-imperial-band-fortified-open-candidate"].facts
        )
        self.assertIn(
            "(not (goal byzantine-offensive-objective-class "
            "byzantine-offensive-objective-class-siege))",
            fortified_open_candidate_facts,
        )
        self.assertNotIn(
            "(goal byzantine-offensive-objective-claim 0)",
            fortified_open_candidate_facts,
        )

        fortified_candidate_facts = tuple(
            fact.source
            for fact in rules["byzantine-imperial-band-fortified-candidate"].facts
        )
        fortified_siege_guard = next(
            fact for fact in fortified_candidate_facts
            if "unit-type-count-total mangonel-line" in fact
        )
        self.assertIn("(unit-type-count-total mangonel-line >= 2)", fortified_siege_guard)
        self.assertIn("(unit-type-count-total trebuchet >= 2)", fortified_siege_guard)
        self.assertIn("(unit-type-count-total bombard-cannon >= 2)", fortified_siege_guard)
        self.assertNotIn("unit-type-count-total trebuchet-line", fortified_siege_guard)
        self.assertNotIn("unit-type-count-total bombard-cannon-line", fortified_siege_guard)

        for identity in (
            "byzantine-imperial-band-floor-break-open",
            "byzantine-imperial-band-floor-break-fortified",
            "byzantine-imperial-band-floor-break-trash",
            "byzantine-imperial-band-fortified-candidate",
            "byzantine-imperial-band-standing-open-candidate",
            "byzantine-imperial-band-standing-trash-candidate",
            "byzantine-imperial-band-trash-open-candidate",
            "byzantine-imperial-band-fortified-open-candidate",
            "byzantine-imperial-band-transition-open",
            "byzantine-imperial-band-transition-fortified",
            "byzantine-imperial-band-transition-trash",
            "byzantine-imperial-band-transition-economic",
        ):
            self.assertIn(identity, rules)

        output = compile_strategy_profile(self.stock_profile, self.effective)
        self.assertIn("(defconst bt-imp-band-standing 0)", output)
        self.assertIn("(enable-timer byzantine-imperial-band-guard-timer 15)", output)
        self.assertIn("(enable-timer byzantine-imperial-band-dwell-timer 90)", output)
        self.assertIn("(enable-timer byzantine-imperial-band-rearm-timer 45)", output)

    def test_byzantine_endgame_push_uses_mature_attack_package_and_band(self):
        compilation = lower_strategy_profile(self.stock_profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        rule = next(
            item for item in control.rules
            if item.identity == "byzantine-endgame-push-admit"
        )
        facts = tuple(fact.source for fact in rule.facts)
        self.assertIn(
            "(up-compare-goal byzantine-imperial-band-state >= 1)",
            facts,
        )
        self.assertTrue(any("(unit-type-count cataphract >= 8)" in fact for fact in facts))
        self.assertTrue(any("(unit-type-count-total battering-ram-line >= 4)" in fact for fact in facts))
        self.assertFalse(any("(unit-type-count halberdier >= 18)" in fact for fact in facts))
        self.assertFalse(any("(unit-type-count 6 >= 18)" in fact for fact in facts))
        self.assertFalse(any("(unit-type-count hussar >= 12)" in fact for fact in facts))

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

        admit_facts = tuple(fact.source for fact in rules["byzantine-endgame-push-admit"].facts)
        self.assertIn(
            "(goal byzantine-offensive-objective-claim 0)",
            admit_facts,
        )
        admit_actions = tuple(action.source for action in rules["byzantine-endgame-push-admit"].actions)
        self.assertNotIn("sn-native-36", " ".join(admit_actions))
        self.assertNotIn("sn-native-227", " ".join(admit_actions))
        ready_actions = tuple(action.source for action in rules["byzantine-endgame-push-imperial-ready"].actions)
        push_contract = self.stock_profile.endgame_plan.push_contract
        self.assertIsNotNone(push_contract)
        assert push_contract is not None
        self.assertIn(
            f"(set-strategic-number sn-native-16 {push_contract.minimum_group_size})",
            ready_actions,
        )
        self.assertIn(
            f"(set-strategic-number sn-native-26 {push_contract.maximum_group_size})",
            ready_actions,
        )
        self.assertIn(
            "(set-strategic-number sn-native-16 6)",
            ready_actions,
        )
        self.assertIn(
            "(set-strategic-number sn-native-26 20)",
            ready_actions,
        )
        self.assertIn("(enable-timer byzantine-endgame-push-timer 20)", admit_actions)
        self.assertIn(
            "(up-compare-goal byzantine-imperial-band-state != 2)",
            admit_facts,
        )
        fortified_admit = rules["byzantine-endgame-push-admit-fortified"]
        fortified_facts = tuple(fact.source for fact in fortified_admit.facts)
        self.assertIn(
            "(goal byzantine-imperial-band-state 2)",
            fortified_facts,
        )
        self.assertIn(
            "(or (unit-type-count trebuchet >= 6) "
            "(or (unit-type-count bombard-cannon >= 6) "
            "(or (unit-type-count-total mangonel-line >= 6) "
            "(unit-type-count-total battering-ram-line >= 6))))",
            fortified_facts,
        )

        live_actions = tuple(action.source for action in rules["byzantine-endgame-push-live-witness"].actions)
        self.assertNotIn("sn-native-36", " ".join(live_actions))
        self.assertNotIn("sn-native-227", " ".join(live_actions))
        self.assertIn("(disable-timer byzantine-endgame-push-timer)", live_actions)
        self.assertIn("(set-goal byzantine-endgame-push-state 3)", live_actions)

        expiry_actions = tuple(action.source for action in rules["byzantine-endgame-push-pulse-expiry"].actions)
        self.assertNotIn("sn-native-36", " ".join(expiry_actions))
        self.assertNotIn("sn-native-227", " ".join(expiry_actions))
        self.assertIn("(disable-timer byzantine-endgame-push-timer)", expiry_actions)
        self.assertIn("(set-goal byzantine-endgame-push-state 3)", expiry_actions)

        sn_controllers = {
            rule.identity: rule
            for rule in control.rules
            if rule.identity.startswith("sn-controller-byz-push-")
        }
        self.assertIn(
            "sn-controller-byz-push-227-activate",
            sn_controllers,
        )
        for identity in (
            "sn-controller-byz-push-36-activate",
            "sn-controller-byz-push-227-activate",
        ):
            self.assertIn(
                "(goal byzantine-endgame-push-state 2)",
                " ".join(fact.source for fact in sn_controllers[identity].facts),
            )

        for identity in (
            "sn-controller-byz-push-36-release",
            "sn-controller-byz-push-227-release",
        ):
            release_facts = tuple(fact.source for fact in sn_controllers[identity].facts)
            joined_release_facts = " ".join(release_facts)
            self.assertIn(
                "(goal byzantine-endgame-push-state 3)",
                joined_release_facts,
            )
            self.assertIn(
                "(goal byzantine-endgame-push-state 5)",
                joined_release_facts,
            )
            self.assertNotIn(
                "(timer-triggered byzantine-endgame-push-timer)",
                joined_release_facts,
            )

        release_facts = tuple(fact.source for fact in rules["byzantine-endgame-push-release"].facts)
        self.assertIn("(goal byzantine-endgame-push-state 3)", release_facts)
        self.assertIn(
            "(goal byzantine-offensive-objective-claim 0)",
            release_facts,
        )
        self.assertIn("(attack-soldier-count <= 0)", release_facts)
        self.assertIn("(unit-type-count cataphract >= 8)", " ".join(release_facts))

        release_actions = tuple(action.source for action in rules["byzantine-endgame-push-release"].actions)
        self.assertIn("(set-goal byzantine-endgame-push-state 1)", release_actions)

        output = compile_strategy_profile(self.stock_profile, self.effective)
        self.assertIn("(enable-timer byzantine-endgame-push-timer 20)", output)
        self.assertIn(
            "; Native control rule: sn-controller-byz-push-227-activate",
            output,
        )

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
