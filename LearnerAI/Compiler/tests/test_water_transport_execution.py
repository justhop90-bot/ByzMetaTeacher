import unittest

from Compiler.primitives import default_de_registry
from Compiler.clients.basilisk import (
    ByzantineProfile,
    WaterExecutionPlan,
    WaterExecutionState,
    WaterPosture,
    resolve_effective_civ,
)
from Compiler.ir.strategy import StrategyPosture, build_byzantine_strategy, lower_strategy_profile
from Compiler.ir.strategy_runtime import ReassessmentReason, RuntimeObservationSnapshot, evaluate_strategy_runtime
from Compiler.ir.water import (
    TransportExecutionPhase,
    WaterExecutionState,
    WaterPosture,
    derive_water_posture,
    transition_transport_execution,
)


class WaterTransportExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())

    def test_transport_state_preserves_intent_and_enters_recovery_when_capability_is_lost(self):
        ready = WaterExecutionState(
            water_map=True,
            transport_required=True,
            transport_capable=True,
            transport_phase=TransportExecutionPhase.READY,
        )
        recovered = transition_transport_execution(
            ready,
            water_map=True,
            transport_required=True,
            transport_capable=False,
        )

        self.assertEqual(recovered.transport_phase, TransportExecutionPhase.RECOVER)
        self.assertTrue(recovered.transport_required)
        self.assertFalse(recovered.transport_capable)


    def test_recovery_holds_until_rebuild_authorization(self):
        ready = WaterExecutionState(
            transport_required=True,
            transport_capable=True,
            transport_phase=TransportExecutionPhase.READY,
        )
        recovered = transition_transport_execution(
            ready,
            water_map=True,
            transport_required=True,
            transport_capable=False,
        )
        self.assertEqual(recovered.transport_phase, TransportExecutionPhase.RECOVER)

        held = transition_transport_execution(
            recovered,
            water_map=True,
            transport_required=True,
            transport_capable=False,
        )
        self.assertEqual(held.transport_phase, TransportExecutionPhase.RECOVER)

        reopened = transition_transport_execution(
            held,
            water_map=True,
            transport_required=True,
            transport_capable=False,
            transport_rebuild_open=True,
        )
        self.assertEqual(reopened.transport_phase, TransportExecutionPhase.PREPARE)

    def test_water_map_and_transport_requirement_are_separate_observations(self):
        profile = build_byzantine_strategy(self.effective)
        plan = profile.water_execution_plan
        self.assertIsNotNone(plan)
        assert plan is not None

        self.assertEqual(plan.water_map_observation, "strategy-water-map")
        self.assertEqual(plan.transport_required_observation, "strategy-transport-required")
        self.assertNotEqual(plan.water_map_observation, plan.transport_required_observation)
        self.assertEqual(
            profile.observation("strategy-water-map").expression,
            "(or (map-type islands) (map-type pacific-islands))",
        )
        self.assertEqual(
            profile.observation("strategy-transport-required").expression,
            "(goal water-transport-objective 1)",
        )

    def test_water_posture_transport_requires_both_map_and_objective(self):
        self.assertEqual(
            derive_water_posture(
                water_map=False,
                transport_required=True,
                dock_exists=True,
                naval_pressure=False,
                warboat_floor_met=False,
            ),
            WaterPosture.NONE,
        )
        self.assertEqual(
            derive_water_posture(
                water_map=True,
                transport_required=False,
                dock_exists=True,
                naval_pressure=False,
                warboat_floor_met=False,
            ),
            WaterPosture.FISHING,
        )
        self.assertEqual(
            derive_water_posture(
                water_map=True,
                transport_required=True,
                dock_exists=True,
                naval_pressure=False,
                warboat_floor_met=False,
            ),
            WaterPosture.TRANSPORT_SUPPORT,
        )

    def test_water_posture_precedence_is_transport_then_naval_then_fishing(self):
        self.assertEqual(
            derive_water_posture(
                water_map=True,
                transport_required=True,
                dock_exists=True,
                naval_pressure=True,
                warboat_floor_met=True,
            ),
            WaterPosture.TRANSPORT_SUPPORT,
        )
        self.assertEqual(
            derive_water_posture(
                water_map=True,
                transport_required=False,
                dock_exists=True,
                naval_pressure=True,
                warboat_floor_met=False,
            ),
            WaterPosture.NAVAL_DEFENSE,
        )
        self.assertEqual(
            derive_water_posture(
                water_map=True,
                transport_required=False,
                dock_exists=True,
                naval_pressure=True,
                warboat_floor_met=True,
            ),
            WaterPosture.NAVAL_CONTROL,
        )

    def test_unknown_water_evidence_fails_closed(self):
        self.assertEqual(
            derive_water_posture(
                water_map=None,
                transport_required=False,
                dock_exists=False,
                naval_pressure=False,
                warboat_floor_met=False,
            ),
            WaterPosture.UNKNOWN,
        )
        state = transition_transport_execution(
            WaterExecutionState(),
            water_map=True,
            transport_required=True,
            transport_capable=None,
        )
        self.assertEqual(state.transport_phase, TransportExecutionPhase.UNKNOWN)

    def test_runtime_state_marks_transport_loss_as_recovery(self):
        profile = build_byzantine_strategy(self.effective)
        water_map_expression = profile.observation("strategy-water-map").expression
        transport_required_expression = profile.observation("strategy-transport-required").expression
        transport_expression = profile.observation("strategy-own-transport-capable").expression
        rebuild_expression = profile.observation("strategy-transport-rebuild-open").expression

        previous = WaterExecutionState(
            water_map=True,
            transport_required=True,
            transport_capable=True,
            transport_phase=TransportExecutionPhase.READY,
        )
        snapshot = RuntimeObservationSnapshot(
            previous_posture=StrategyPosture.BOOM,
            previous_water_execution_state=previous,
            fact_results=(
                (water_map_expression, True),
                (transport_required_expression, True),
                (transport_expression, False),
                (rebuild_expression, False),
            ),
        )

        runtime = evaluate_strategy_runtime(profile, self.effective, snapshot)

        self.assertIsNotNone(runtime.water_execution_state)
        self.assertEqual(
            runtime.water_execution_state.transport_phase,
            TransportExecutionPhase.RECOVER,
        )
        self.assertIn(
            ReassessmentReason.TRANSPORT_CAPABILITY_LOSS,
            runtime.reassessment_reasons,
        )

    def test_map_type_is_a_typed_native_profile_fact(self):
        registry = default_de_registry()
        map_assessment = registry.assess_support("map-type")
        warboat_assessment = registry.assess_support("warboat-count")

        self.assertEqual(map_assessment.state.value, "executable-safe")
        self.assertEqual(warboat_assessment.state.value, "executable-safe")

    def test_client_exports_typed_water_execution_surface(self):
        self.assertTrue(WaterExecutionPlan)
        self.assertTrue(WaterExecutionState)
        self.assertTrue(WaterPosture)


    def test_transport_demand_is_objective_driven_not_map_driven(self):
        profile = build_byzantine_strategy(self.effective)
        demand = profile.demand("water-transport-capability")
        req_text = " ".join(demand.execution.requirements)
        self.assertIn(profile.observation("strategy-water-map").expression, req_text)
        self.assertIn(profile.observation("strategy-transport-required").expression, req_text)
        self.assertIn("(building-type-count-total dock >= 1)", req_text)
        invalidation_refs = {
            evidence.observation_ref
            for evidence in demand.invalidation
            if evidence.observation_ref is not None
        }
        self.assertIn("strategy-transport-capability-lost", invalidation_refs)
        self.assertNotIn("strategy-transport-recovery", invalidation_refs)

    def test_water_lowering_has_explicit_map_gate_and_recovery_reopen(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        rules = {rule.identity: rule for rule in control.rules}
        transport = rules["water-posture-transport"]
        transport_facts = tuple(fact.source for fact in transport.facts)
        self.assertIn(profile.observation("strategy-water-map").expression, transport_facts)
        self.assertIn(profile.observation("strategy-transport-required").expression, transport_facts)
        self.assertIn("transport-phase-reopen", rules)

        prepare = rules["transport-phase-prepare"]
        prepare_text = " ".join(fact.source for fact in prepare.facts)
        self.assertNotIn("(goal transport-phase 3)", prepare_text)

    def test_stock_strategy_exposes_typed_water_execution_plan(self):
        profile = build_byzantine_strategy(self.effective)

        self.assertIsNotNone(profile.water_execution_plan)
        self.assertIn("strategy-water-map", {
            item.identity for item in profile.observations
        })
        self.assertIn("strategy-transport-required", {
            item.identity for item in profile.observations
        })

    def test_water_fishing_expansion_is_bounded_and_excludes_pacific(self):
        profile = build_byzantine_strategy(self.effective)
        demand = profile.demand("water-fishing-expansion")
        requirements = tuple(demand.execution.requirements)
        self.assertIn("(unit-type-count-total fishing-ship < 4)", requirements)
        self.assertIn("(current-age >= feudal-age)", requirements)
        self.assertIn(profile.observation("strategy-enemy-naval-pressure").expression, requirements)
        self.assertIn("(building-type-count-total dock >= 1)", requirements)

    def test_pacific_opening_transport_objective_is_dark_age_starting_ship_gated(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None
        rule = next(
            item for item in control.rules
            if item.identity == "pacific-opening-transport-open"
        )
        facts = tuple(fact.source for fact in rule.facts)
        self.assertIn("(map-type pacific-islands)", facts)
        self.assertIn("(current-age == dark-age)", facts)
        self.assertIn("(unit-type-count-total transport-ship >= 1)", facts)

    def test_pacific_opening_transport_does_not_depend_on_army_attack_ready(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None
        rule = next(
            item for item in control.rules
            if item.identity == "pacific-opening-transport-open"
        )
        text = " ".join(fact.source for fact in rule.facts)
        self.assertNotIn("byzantine-army-attack-ready", text)

    def test_transport_capability_is_a_feudal_execution_capability(self):
        profile = build_byzantine_strategy(self.effective)
        demand = profile.demand("water-transport-capability")
        requirements = tuple(demand.execution.requirements)
        self.assertIn("(current-age >= feudal-age)", requirements)
        self.assertNotIn("(current-age >= dark-age)", requirements)

    def test_naval_escalation_consumes_consolidated_enemy_naval_pressure_observation(self):
        profile = build_byzantine_strategy(self.effective)
        for identity in ("water-naval-defense", "water-naval-control"):
            demand = profile.demand(identity)
            requirements = " ".join(demand.execution.requirements)
            self.assertIn(
                profile.observation("strategy-enemy-naval-pressure").expression,
                requirements,
            )

    def test_water_fishing_continuity_starts_in_dark_age_after_dock(self):
        profile = build_byzantine_strategy(self.effective)
        demand = profile.demand("water-fishing-continuity")
        requirements = tuple(demand.execution.requirements)

        self.assertIn("(current-age >= dark-age)", requirements)
        self.assertNotIn("(current-age >= feudal-age)", requirements)
        self.assertIn("(building-type-count-total dock >= 1)", requirements)

    def test_water_plan_enables_native_boat_exploration_after_first_fishing_ship(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        rule = next(
            item for item in control.rules
            if item.identity == "water-boat-exploration-enable"
        )
        facts = tuple(fact.source for fact in rule.facts)
        actions = tuple(action.source for action in rule.actions)

        self.assertIn(profile.observation("strategy-water-map").expression, facts)
        self.assertIn(profile.observation("strategy-dock-exists").expression, facts)
        self.assertIn("(unit-type-count fishing-ship >= 1)", facts)
        self.assertIn("(set-strategic-number sn-number-boat-explore-groups 1)", actions)
        self.assertIn("(disable-self)", actions)

    def test_checked_in_runtime_contains_dark_age_water_continuity(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[3]
        runtime = (root / "Byzantine.per").read_text(encoding="utf-8")

        fishing_start = runtime.index(
            "; Action issuance: water-fishing-continuity | ACTIVE -> ISSUED"
        )
        fishing_end = runtime.index(
            "; Pending diagnostics: water-transport-capability",
            fishing_start,
        )
        fishing_rule = runtime[fishing_start:fishing_end]
        self.assertIn("(current-age >= dark-age)", fishing_rule)
        self.assertNotIn("(current-age >= feudal-age)", fishing_rule)
        self.assertIn("(can-train-with-escrow fishing-ship)", fishing_rule)
        self.assertIn("(defconst sn-number-boat-explore-groups 61)", runtime)
        self.assertIn("(set-strategic-number sn-number-boat-explore-groups 1)", runtime)

    def test_water_plan_lowers_into_persistent_posture_and_transport_state(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)

        self.assertIsNotNone(compilation.control_plan)
        state_ids = {state.identifier for state in compilation.control_plan.states}
        self.assertIn("water-posture", state_ids)
        self.assertIn("transport-phase", state_ids)
        self.assertIn("water-transport-objective", state_ids)
        self.assertIn("water-transport-rebuild", state_ids)
        self.assertIn("pacific-opening-transport-objective", state_ids)

        rule_ids = {rule.identity for rule in compilation.control_plan.rules}
        self.assertIn("transport-phase-recover-on-capability-loss", rule_ids)
        self.assertIn("transport-phase-reopen", rule_ids)
        self.assertIn("transport-rebuild-authorize", rule_ids)
        self.assertIn("pacific-opening-transport-open", rule_ids)
        self.assertIn("pacific-opening-transport-close-at-feudal", rule_ids)
        self.assertIn("pacific-opening-transport-close-on-loss", rule_ids)
        self.assertIn("transport-objective-open", rule_ids)
        self.assertIn("transport-objective-close", rule_ids)
        self.assertIn("transport-phase-ready", rule_ids)
        self.assertIn("water-posture-naval-defense", rule_ids)
        self.assertIn("water-posture-naval-control", rule_ids)

    def test_feudal_resource_island_transport_state_is_feudal_and_fail_closed(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        state_ids = {state.identifier for state in control.states}
        self.assertIn("feudal-resource-island-transport-objective", state_ids)

        open_rule = next(
            rule for rule in control.rules
            if rule.identity == "feudal-resource-island-transport-open"
        )
        open_facts = tuple(fact.source for fact in open_rule.facts)
        self.assertIn("(current-age >= feudal-age)", open_facts)
        self.assertIn("(unit-type-count-total transport-ship >= 1)", open_facts)
        self.assertIn(
            profile.observation("strategy-water-map").expression,
            open_facts,
        )
        self.assertIn(
            f"(not {profile.observation('strategy-enemy-naval-pressure').expression})",
            open_facts,
        )
        self.assertNotIn("byzantine-army-attack-ready", " ".join(open_facts))

        close_rules = {
            rule.identity: rule
            for rule in control.rules
            if rule.identity.startswith("feudal-resource-island-transport-close-")
        }
        self.assertEqual(
            set(close_rules),
            {
                "feudal-resource-island-transport-close-nonwater",
                "feudal-resource-island-transport-close-before-feudal",
                "feudal-resource-island-transport-close-on-loss",
                "feudal-resource-island-transport-close-on-naval-pressure",
            },
        )
        close_text = {
            identity: " ".join(fact.source for fact in rule.facts)
            for identity, rule in close_rules.items()
        }
        self.assertIn("(not (current-age >= feudal-age))", close_text["feudal-resource-island-transport-close-before-feudal"])
        self.assertIn("(not (unit-type-count-total transport-ship >= 1))", close_text["feudal-resource-island-transport-close-on-loss"])
        self.assertIn(
            profile.observation("strategy-enemy-naval-pressure").expression,
            close_text["feudal-resource-island-transport-close-on-naval-pressure"],
        )

    def test_stock_strategy_has_transport_and_naval_execution_demands(self):
        profile = build_byzantine_strategy(self.effective)
        demand_ids = {item.identity for item in profile.demands}

        self.assertIn("water-transport-capability", demand_ids)
        self.assertIn("water-naval-defense", demand_ids)
        self.assertIn("water-naval-control", demand_ids)


if __name__ == "__main__":
    unittest.main()
