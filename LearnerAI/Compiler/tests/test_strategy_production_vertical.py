"""Phase 9 (ROADMAP): production acceptance vertical, single chain proof.

Walks one real strategic production demand (early-defensive-spears,
spearman-line TRAIN from the Byzantine castle strategy) through all
nine acceptance links in one test: community pattern -> strategic
demand -> admissibility -> capability -> arbitration -> execution ->
world-state witness -> recovery -> reassessment -> deterministic native
.per (zero-findings covered by assert_strategy_production_vertical_native).

Hard invariants pinned here (not re-proven, referenced):
- can-train-with-escrow stays admission (escrow-aware, same arbitration
  owner as ordinary admission);
- unit-type-count-total stays observation, up-pending-objects stays
  protection, unit-type-count stays the sole witness;
- SN 264 never enters arbitration; DUC-directed trains derive nothing;
- busy/queue/same-pass behavior stays OPEN runtime research.
"""
import unittest

from Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_castle_strategy,
    build_byzantine_stock_strategy,
    compile_strategy_profile,
)
from Compiler.ir.civ_profile import resolve_effective_civ
from Compiler.ir.model import SemanticId
from Compiler.ir.strategy import lower_strategy_profile
from Compiler.ir.strategy_runtime import (
    ReassessmentReason,
    RuntimeObservationSnapshot,
    StrategicDemandRuntimeState,
    StrategyPosture,
    evaluate_strategy_runtime,
)
from Compiler.primitives import default_de_registry
from Compiler.semantic.capability_bridge import project_capability_graph
from Compiler.semantic.capability_validation import validate_capability_graph
from Compiler.semantic.completion_witness import validate_completion_witnesses
from Compiler.semantic.idiom_coverage import IDIOM_COVERAGE_SEED, IdiomStage
from Compiler.semantic.production_arbitration import (
    PRODUCTION_TRAIN_CONFLICT_CLASS,
    derive_production_arbitration,
    production_arbitration_request,
)
from Compiler.semantic.resource_conflicts import validate_resource_conflicts

PROFILE_ID = "byzantine-land-castle-v1"
SPEARS = "early-defensive-spears"


def _snapshot(facts=(), completed=(), previous_states=(), previous_posture=None):
    return RuntimeObservationSnapshot(
        fact_results=tuple(facts),
        completed_demands=frozenset(completed),
        previous_posture=previous_posture,
        previous_demand_states=tuple(previous_states),
    )


def _spears_facts(alive=True):
    return (
        ("(current-age >= feudal-age)", True),
        ("(can-train-with-escrow spearman-line)", alive),
        ("(unit-type-count-total spearman-line < 2)", True),
    )


class StrategyProductionVerticalTests(unittest.TestCase):
    def setUp(self):
        self.effective = resolve_effective_civ(
            ByzantineProfile.for_update_185872()
        )
        self.profile = build_byzantine_castle_strategy(self.effective)
        self.compilation = lower_strategy_profile(self.profile, self.effective)
        self.spears = next(
            demand
            for demand in self.compilation.demands
            if demand.strategic_binding is not None
            and demand.strategic_binding.strategic_id == SPEARS
        )

    def test_link0_community_pattern_ledger_covers_production(self):
        record = next(
            item for item in IDIOM_COVERAGE_SEED if item.idiom_id == "IDIOM-006"
        )
        self.assertGreaterEqual(
            list(IdiomStage).index(record.stage),
            list(IdiomStage).index(IdiomStage.LOWERABLE),
        )

    def test_link1_strategic_demand_carries_train_lifecycle(self):
        binding = self.spears.strategic_binding
        self.assertEqual(binding.capability_intent.kind.value, "TRAIN")
        self.assertEqual(binding.capability_intent.entity_id, "spearman-line")
        lifecycle = self.spears.production_lifecycle
        self.assertIsNotNone(lifecycle)
        self.assertEqual(lifecycle.unit, "spearman-line")
        self.assertEqual(lifecycle.native_unit_id, 93)
        self.assertEqual(lifecycle.target_admission.primitive, "can-train-with-escrow")
        self.assertEqual(self.spears.action.expression.head, "train")

    def test_link2_admissibility_projects_to_capability(self):
        graph = project_capability_graph(
            tuple(self.compilation.demands), default_de_registry()
        )
        providers = graph.providers_for(
            next(
                provider.identity
                for provider in graph.providers
                if provider.identity.local_name == "early-defensive-spears-provider"
            )
        )
        self.assertEqual(len(providers), 1)
        report = validate_capability_graph(graph, default_de_registry())
        self.assertTrue(report.valid, report.diagnostics)

    def test_link3_arbitration_claim_with_strategic_owner(self):
        request = production_arbitration_request(self.spears)
        self.assertIsNotNone(request)
        self.assertEqual(
            request.request_id.purpose,
            "action-claim:%s" % PRODUCTION_TRAIN_CONFLICT_CLASS,
        )
        self.assertEqual(
            request.request_id.owner, SemanticId(PROFILE_ID, "defense")
        )
        derived = derive_production_arbitration(
            tuple(self.compilation.demands)
        )
        graph = project_capability_graph(derived, default_de_registry())
        report = validate_resource_conflicts(graph, default_de_registry())
        self.assertTrue(report.valid, report.diagnostics)
        train_conflicts = tuple(
            conflict
            for conflict in report.conflicts
            if conflict.conflict_class == PRODUCTION_TRAIN_CONFLICT_CLASS
        )
        self.assertEqual(len(train_conflicts), 1)
        self.assertEqual(
            train_conflicts[0].arbitration_owner,
            SemanticId(PROFILE_ID, "defense"),
        )
        self.assertIn(
            SemanticId(PROFILE_ID, "early-defensive-spears-provider"),
            train_conflicts[0].providers,
        )

    def test_link4_execution_issues_train_with_barriers(self):
        artifact = compile_strategy_profile(self.profile, self.effective)
        self.assertIn("(train spearman-line)", artifact)
        self.assertIn(
            "(set-goal production-retry-barrier-early-defensive-spears 1)",
            artifact,
        )
        self.assertIn("(goal action-claim-train-arbitration 0)", artifact)
        self.assertIn("(set-goal action-claim-train-arbitration 1)", artifact)

    def test_link5_witness_is_unit_count_not_admission(self):
        witness = self.spears.completion_witness
        self.assertIsNotNone(witness)
        self.assertEqual(witness.primitive, "unit-type-count")
        self.assertEqual(witness.expression.head, "unit-type-count")
        report = validate_completion_witnesses(
            tuple(self.compilation.demands), default_de_registry()
        )
        self.assertTrue(report.valid, report.diagnostics)

    def test_link6_recovery_preserves_demand_identity(self):
        runtime = evaluate_strategy_runtime(
            self.profile,
            self.effective,
            _snapshot(
                facts=_spears_facts(alive=False),
                previous_states=(
                    (SPEARS, StrategicDemandRuntimeState.STRATEGIC_ACTIVE_EXECUTABLE),
                ),
                previous_posture=StrategyPosture.FLUSH,
            ),
        )
        self.assertEqual(
            runtime.demand_state(SPEARS),
            StrategicDemandRuntimeState.STRATEGIC_ACTIVE_BLOCKED,
        )
        self.assertEqual(runtime.strategic_owner(SPEARS), "defense")

    def test_link7_reassessment_walks_executable_blocked_complete(self):
        alive = evaluate_strategy_runtime(
            self.profile, self.effective, _snapshot(facts=_spears_facts(alive=True))
        )
        self.assertEqual(
            alive.demand_state(SPEARS),
            StrategicDemandRuntimeState.STRATEGIC_ACTIVE_EXECUTABLE,
        )
        self.assertIn(
            ReassessmentReason.DEMAND_ACTIVATION, alive.reassessment_reasons
        )
        blocked = evaluate_strategy_runtime(
            self.profile,
            self.effective,
            _snapshot(
                facts=_spears_facts(alive=False),
                previous_states=(
                    (SPEARS, StrategicDemandRuntimeState.STRATEGIC_ACTIVE_EXECUTABLE),
                ),
            ),
        )
        self.assertEqual(
            blocked.demand_state(SPEARS),
            StrategicDemandRuntimeState.STRATEGIC_ACTIVE_BLOCKED,
        )
        done = evaluate_strategy_runtime(
            self.profile,
            self.effective,
            _snapshot(
                facts=_spears_facts(alive=True),
                completed=(SPEARS,),
                previous_states=(
                    (SPEARS, StrategicDemandRuntimeState.STRATEGIC_ACTIVE_EXECUTABLE),
                ),
            ),
        )
        self.assertEqual(
            done.demand_state(SPEARS),
            StrategicDemandRuntimeState.STRATEGIC_COMPLETE,
        )
        self.assertIn(
            ReassessmentReason.CAPABILITY_COMPLETION, done.reassessment_reasons
        )
        self.assertIn(SPEARS, done.strategically_complete_demands)

    def test_range_depth_uses_native_crossbowman_identifier(self):
        stock_profile = build_byzantine_stock_strategy(self.effective)
        artifact = compile_strategy_profile(stock_profile, self.effective)
        self.assertIn(
            "(or (unit-type-count-total crossbowman >= 6) "
            "(unit-type-count-total 6 >= 6))",
            artifact,
        )
        self.assertNotIn(
            "(unit-type-count-total crossbow-line >= 6)",
            artifact,
        )

    def test_link8_compilation_is_deterministic(self):
        first = compile_strategy_profile(self.profile, self.effective)
        second = compile_strategy_profile(self.profile, self.effective)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
