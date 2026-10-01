"""Phase 1 (ROADMAP): production/train arbitration over ResourceClaim.

Covers the required production tests:
- stable claim identity;
- same-owner conflict;
- distinct-owner separation;
- no claim from can-train alone;
- pending cannot satisfy arbitration;
- escrowed train preserves ownership;
- DUC train remains separate;
- military composition consumes the shared claim;
- deterministic repeated compilation.

Hard invariants pinned here (PROJECT_STATE / ROADMAP Phase 1 contract):
- owner comes from the strategic identity when strategy-bound unless an
  explicit production-arbitration group is declared; otherwise the shared
  unit execution-memory owner applies; the provider UnitId is never an owner;
- can-train stays admission only; train stays issuance only;
- up-pending-objects stays duplicate-queue protection;
- unit-type-count-total stays observation only;
- SN 264 stays OPEN evidence and never enters arbitration;
- no native train conflict class is invented (the `train` Primitive keeps
  `conflict_class=None`; the claim is compiler policy only).
"""
import unittest
from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.ast import Expression
from Compiler.compiler import compile_source
from Compiler.errors import CompileError
from Compiler.ir.model import SemanticId
from Compiler.ir.strategy import (
    CapabilityIntent,
    CapabilityIntentKind,
    StrategicBinding,
    StrategicPriority,
    StrategicTarget,
    StrategicTargetKind,
    StrategyPosture,
)
from Compiler.parser import parse
from Compiler.primitives import default_de_registry
from Compiler.primitives.engine_semantics import _DUC_COMMAND_SPECS
from Compiler.semantic import analyze
from Compiler.semantic.capability_bridge import project_capability_graph
from Compiler.semantic.production_arbitration import (
    DUC_DIRECTED_COMMAND_HEADS,
    PRODUCTION_ARBITRATION_EXECUTION_OWNER,
    PRODUCTION_TRAIN_CLAIM_PURPOSE,
    PRODUCTION_TRAIN_CONFLICT_CLASS,
    derive_production_arbitration,
    is_duc_directed_train,
    production_arbitration_owner,
    production_arbitration_request,
)
from Compiler.semantic.resource_conflicts import (
    ResourceDiagnosticCode,
    validate_resource_conflicts,
)


def _train_source(unit="spearman", admission="can-train", extra=()):
    lines = [
        "demand spears {",
        "    require (unit-type-count-total %s < 5)" % unit,
        "    require (%s %s)" % (admission, unit),
    ]
    lines.extend("    require %s" % requirement for requirement in extra)
    lines.extend(
        [
            "    action (train %s)" % unit,
            "    witness (unit-type-count %s >= 2)" % unit,
            "    release (unit-type-count %s >= 2)" % unit,
            "}",
        ]
    )
    return "\n".join(lines)


def _analyze(source, unit="test"):
    return analyze(parse(source), default_de_registry(), source_unit=unit)


def _binding(strategic_id, production_arbitration_group=None):
    return StrategicBinding(
        strategic_id=strategic_id,
        owner="war-council",
        posture=StrategyPosture.BOOM,
        priority=StrategicPriority.CORE,
        reason=(),
        target=StrategicTarget(
            kind=StrategicTargetKind.EXACT,
            entity_type="unit-line",
            entity_id="spearman-line",
        ),
        capability_intent=CapabilityIntent(
            kind=CapabilityIntentKind.TRAIN,
            entity_type="unit-line",
            entity_id="spearman-line",
        ),
        opportunity_cost=None,
        production_arbitration_group=production_arbitration_group,
    )


def _duc_expression():
    return Expression(
        source="(up-can-search search-local)",
        head="up-can-search",
        args=("search-local",),
    )


class ProductionArbitrationDerivationTests(unittest.TestCase):
    def test_ordinary_train_derives_stable_policy_claim(self):
        demand = _analyze(_train_source())[0]
        request = production_arbitration_request(demand)

        self.assertIsNotNone(request)
        self.assertEqual(
            request.request_id.purpose, PRODUCTION_TRAIN_CLAIM_PURPOSE
        )
        self.assertEqual(
            request.request_id.purpose,
            "action-claim:%s" % PRODUCTION_TRAIN_CONFLICT_CLASS,
        )
        self.assertEqual(request.role.value, "EXECUTION_MEMORY")
        # Shared unit execution-memory owner: ordinary multi-train programs
        # arbitrate under one deterministic contract.
        self.assertEqual(
            request.request_id.owner,
            SemanticId("test", PRODUCTION_ARBITRATION_EXECUTION_OWNER),
        )
        # The provider UnitId is never the owner.
        self.assertNotIn("93", request.request_id.owner.local_name)

    def test_derivation_is_idempotent_and_deterministic(self):
        first = derive_production_arbitration(_analyze(_train_source()))
        second = derive_production_arbitration(first)
        repeat = derive_production_arbitration(_analyze(_train_source()))

        self.assertEqual(
            first[0].action.arbitration_request,
            second[0].action.arbitration_request,
        )
        self.assertEqual(
            first[0].action.arbitration_request,
            repeat[0].action.arbitration_request,
        )

    def test_derivation_never_overwrites_existing_request(self):
        demand = _analyze(_train_source())[0]
        existing = demand.action.arbitration_request
        self.assertIsNone(existing)
        pinned = replace(
            demand.action,
            arbitration_request="pinned",
        )
        pinned_demand = replace(demand, action=pinned)
        derived = derive_production_arbitration([pinned_demand])
        self.assertEqual(
            derived[0].action.arbitration_request, "pinned"
        )

    def test_can_train_alone_derives_no_claim(self):
        build = """
        demand castle {
            require (can-build castle)
            require (can-train spearman)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        demand = _analyze(build)[0]
        self.assertIsNone(production_arbitration_request(demand))

    def test_train_without_admission_derives_no_claim(self):
        source = """
        demand lone-spears {
            require (unit-type-count-total spearman < 5)
            action (train spearman)
            witness (unit-type-count spearman >= 2)
            release (unit-type-count spearman >= 2)
        }
        """
        demand = _analyze(source)[0]
        self.assertIsNone(demand.production_lifecycle)
        self.assertIsNone(production_arbitration_request(demand))

    def test_non_train_lifecycles_derive_no_claim(self):
        research = """
        demand wheelbarrow {
            require (can-research ri-wheelbarrow)
            action (research ri-wheelbarrow)
            witness (research-completed ri-wheelbarrow)
            release (research-completed ri-wheelbarrow)
        }
        """
        demand = _analyze(research)[0]
        self.assertIsNotNone(demand.research_lifecycle)
        self.assertIsNone(production_arbitration_request(demand))

    def test_escrowed_train_preserves_arbitration_ownership(self):
        ordinary = _analyze(_train_source())[0]
        escrowed = _analyze(
            _train_source(admission="can-train-with-escrow")
        )[0]

        ordinary_request = production_arbitration_request(ordinary)
        escrowed_request = production_arbitration_request(escrowed)

        self.assertIsNotNone(ordinary_request)
        self.assertIsNotNone(escrowed_request)
        # Escrow-aware admission keeps the same semantic arbitration owner:
        # escrow changes the resource view, not the arbitration identity.
        self.assertEqual(
            escrowed_request.request_id.owner,
            ordinary_request.request_id.owner,
        )
        self.assertEqual(
            escrowed_request.request_id.purpose,
            ordinary_request.request_id.purpose,
        )

    def test_sn264_never_enters_arbitration(self):
        low = _analyze(
            _train_source(
                extra=("(up-compare-sn sn-enable-training-queue == 3)",),
            )
        )[0]
        high = _analyze(
            _train_source(
                extra=("(up-compare-sn sn-enable-training-queue == 5)",),
            )
        )[0]

        low_request = production_arbitration_request(low)
        high_request = production_arbitration_request(high)

        self.assertIsNotNone(low_request)
        self.assertEqual(low_request, high_request)
        self.assertNotIn("264", low_request.request_id.purpose)
        self.assertNotIn("264", low_request.request_id.owner.local_name)

    def test_pending_values_never_shape_the_claim(self):
        demand = _analyze(_train_source())[0]
        request = production_arbitration_request(demand)

        self.assertIsNotNone(request)
        self.assertEqual(
            request.request_id.purpose, PRODUCTION_TRAIN_CLAIM_PURPOSE
        )
        pending = demand.production_lifecycle.queue_protection.pending_fact
        self.assertEqual(pending.head, "up-pending-objects")
        # Pending stays protection: it is referenced by the lifecycle, never
        # by the arbitration request.
        self.assertNotIn(
            pending.head, request.request_id.purpose
        )

    def test_explicit_production_group_selects_shared_claim_owner(self):
        demand = _analyze(_train_source())[0]
        bound = replace(
            demand,
            strategic_binding=_binding(
                "counter-mounted-spears",
                production_arbitration_group="defense",
            ),
        )

        self.assertEqual(
            production_arbitration_owner(bound),
            SemanticId("test", "defense"),
        )
        request = production_arbitration_request(bound)
        self.assertIsNotNone(request)
        self.assertEqual(request.request_id.owner, SemanticId("test", "defense"))

    def test_strategic_binding_selects_strategic_owner(self):
        demand = _analyze(_train_source())[0]
        bound = replace(demand, strategic_binding=_binding("war-plan"))

        self.assertEqual(
            production_arbitration_owner(bound),
            SemanticId("test", "war-plan"),
        )
        request = production_arbitration_request(bound)
        self.assertIsNotNone(request)
        self.assertEqual(
            request.request_id.owner, SemanticId("test", "war-plan")
        )


class DucDirectedTrainTests(unittest.TestCase):
    def test_duc_head_inventory_matches_pinned_specs(self):
        pinned = frozenset(
            command for command, _ in _DUC_COMMAND_SPECS
        ) | {"up-target-point"}
        self.assertEqual(DUC_DIRECTED_COMMAND_HEADS, pinned)

    def test_duc_directed_train_derives_no_claim(self):
        demand = _analyze(_train_source())[0]
        directed = replace(
            demand,
            requirements=demand.requirements
            + (
                replace(
                    demand.requirements[0],
                    expression=_duc_expression(),
                ),
            ),
        )

        self.assertTrue(is_duc_directed_train(directed))
        self.assertFalse(is_duc_directed_train(demand))
        self.assertIsNone(production_arbitration_request(directed))
        derived = derive_production_arbitration([directed])
        self.assertIsNone(derived[0].action.arbitration_request)

    def test_nested_duc_reference_marks_duc_direction(self):
        demand = _analyze(_train_source())[0]
        nested = Expression(
            source="(and (up-can-search search-local) (can-train spearman))",
            head="and",
            args=(
                _duc_expression(),
                demand.requirements[1].expression,
            ),
        )
        directed = replace(
            demand,
            requirements=(
                replace(
                    demand.requirements[1],
                    expression=nested,
                ),
            )
            + tuple(
                requirement
                for requirement in demand.requirements[2:]
            ),
        )
        self.assertTrue(is_duc_directed_train(directed))
        self.assertIsNone(production_arbitration_request(directed))


class ProductionArbitrationGraphTests(unittest.TestCase):
    def _validated(self, demands):
        derived = derive_production_arbitration(demands)
        graph = project_capability_graph(
            derived, default_de_registry()
        )
        return validate_resource_conflicts(
            graph, default_de_registry()
        )

    def test_same_strategic_owner_conflicts_under_one_contract(self):
        spear_demands = _analyze(_train_source())
        archer_source = _train_source(unit="archer").replace(
            "demand spears {", "demand archers {"
        )
        archer_demands = _analyze(archer_source)
        bound = [
            replace(demand, strategic_binding=_binding("war-plan"))
            for demand in (spear_demands[0], archer_demands[0])
        ]

        report = self._validated(bound)

        self.assertTrue(report.valid, report.diagnostics)
        self.assertEqual(len(report.claims), 2)
        self.assertEqual(len(report.conflicts), 1)
        contract = report.conflicts[0]
        self.assertEqual(
            contract.conflict_class, PRODUCTION_TRAIN_CONFLICT_CLASS
        )
        self.assertEqual(
            contract.arbitration_owner, SemanticId("test", "war-plan")
        )
        self.assertEqual(
            tuple(sorted(provider.local_name for provider in contract.providers)),
            ("archers-provider", "spears-provider"),
        )
        for claim in report.claims:
            self.assertEqual(
                claim.arbitration_owner, SemanticId("test", "war-plan")
            )
            # Claimant stays the provider identity, never the UnitId owner.
            self.assertTrue(claim.claimant.local_name.endswith("-provider"))

    def test_distinct_owners_stay_separated_with_exact_diagnostic(self):
        spear_demands = _analyze(_train_source())
        archer_source = _train_source(unit="archer").replace(
            "demand spears {", "demand archers {"
        )
        archer_demands = _analyze(archer_source)
        bound = [
            replace(spear_demands[0], strategic_binding=_binding("war-plan")),
            replace(
                archer_demands[0],
                strategic_binding=_binding("castle-watch"),
            ),
        ]

        first = self._validated(bound)
        second = self._validated(bound)

        self.assertFalse(first.valid)
        codes = tuple(
            diagnostic.code for diagnostic in first.diagnostics
        )
        self.assertIn(
            ResourceDiagnosticCode.CONFLICT_INCOMPATIBLE_ARBITRATORS, codes
        )
        messages = " ".join(
            diagnostic.message for diagnostic in first.diagnostics
        )
        # No silent merge: both owners are named deterministically.
        self.assertIn("war-plan", messages)
        self.assertIn("castle-watch", messages)
        self.assertEqual(
            tuple(
                (diagnostic.code, diagnostic.message)
                for diagnostic in first.diagnostics
            ),
            tuple(
                (diagnostic.code, diagnostic.message)
                for diagnostic in second.diagnostics
            ),
        )

    def test_pending_alone_satisfies_no_arbitration(self):
        demand = _analyze(_train_source())[0]
        graph = project_capability_graph([demand], default_de_registry())
        report = validate_resource_conflicts(
            graph, default_de_registry()
        )

        self.assertTrue(report.valid)
        self.assertEqual(report.claims, ())
        self.assertEqual(report.conflicts, ())
        provider = graph.providers[0]
        self.assertIsNone(provider.action.conflict_class)
        self.assertIsNone(provider.resource_claim)

    def test_ordinary_multi_train_program_shares_one_contract(self):
        sources = []
        for index, unit in enumerate(("spearman", "archer", "knight")):
            sources.append(
                _train_source(unit=unit).replace(
                    "demand spears {", "demand force-%d {" % index
                )
            )
        demands = [
            demand
            for source in sources
            for demand in _analyze(source)
        ]

        report = self._validated(demands)

        self.assertTrue(report.valid, report.diagnostics)
        self.assertEqual(len(report.claims), 3)
        self.assertEqual(len(report.conflicts), 1)
        self.assertEqual(
            report.conflicts[0].arbitration_owner,
            SemanticId("test", PRODUCTION_ARBITRATION_EXECUTION_OWNER),
        )

    def test_build_and_train_arbitration_coexist(self):
        mixed = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        demand spears {
            require (can-train spearman)
            action (train spearman)
            witness (unit-type-count spearman >= 2)
            release (unit-type-count spearman >= 2)
        }
        """
        report = self._validated(_analyze(mixed))

        self.assertTrue(report.valid, report.diagnostics)
        by_class = {
            contract.conflict_class for contract in report.conflicts
        }
        self.assertEqual(
            by_class,
            {"BUILD_PASS_SINGLETON", PRODUCTION_TRAIN_CONFLICT_CLASS},
        )

    def test_military_composition_consumes_shared_claim_without_conflation(self):
        demand = derive_production_arbitration(_analyze(_train_source()))[0]
        report = self._validated([demand])

        self.assertTrue(report.valid, report.diagnostics)
        production_claim = report.claims[0]
        self.assertEqual(
            production_claim.conflict_class,
            PRODUCTION_TRAIN_CONFLICT_CLASS,
        )
        self.assertEqual(
            production_claim.claimant,
            SemanticId("test", "spears-provider"),
        )

        # The composition proof path (semantic/military_composition.py) names
        # its own claim identity, claimant, class, and owner: consuming the
        # shared production demand never conflates the two claims.
        composition = SemanticId("test", "military-composition")
        composition_claim_tuple = (
            production_claim.identity.source_unit,
            "%s-military-composition-resource"
            % demand.identity.local_name,
        )
        self.assertNotEqual(
            (production_claim.identity.source_unit,
             production_claim.identity.local_name),
            composition_claim_tuple,
        )
        self.assertNotEqual(production_claim.claimant, demand.identity)
        self.assertNotEqual(
            production_claim.conflict_class,
            "military-composition:%s" % composition.local_name,
        )
        self.assertNotEqual(production_claim.arbitration_owner, composition)
        # MIL-PROOF-003 precondition: the composed demand carries a
        # ProductionLifecycle for the composed UnitId.
        self.assertIsNotNone(demand.production_lifecycle)
        self.assertEqual(demand.production_lifecycle.native_unit_id, 93)

    def test_can_train_is_not_completion(self):
        demand = derive_production_arbitration(_analyze(_train_source()))[0]

        self.assertEqual(demand.completion_witness.primitive, "unit-type-count")
        self.assertEqual(demand.witness.head, "unit-type-count")
        self.assertIsNotNone(demand.action.arbitration_request)


class ProductionArbitrationPipelineTests(unittest.TestCase):
    def test_pipeline_emits_deterministic_arbitration(self):
        first = compile_source(_train_source())
        second = compile_source(_train_source())

        self.assertEqual(first, second)
        self.assertIn("(defconst action-claim-train-arbitration", first)
        self.assertIn("(goal action-claim-train-arbitration 0)", first)
        self.assertIn("(set-goal action-claim-train-arbitration 1)", first)
        # Admission stays admission; issuance stays issuance; the witness
        # stays the world-state witness.
        self.assertIn("(can-train spearman)", first)
        self.assertIn("(train spearman)", first)
        self.assertIn("(unit-type-count spearman >= 2)", first)

    def test_pipeline_rejects_distinct_owner_merge(self):
        spear_demands = _analyze(_train_source())
        archer_source = _train_source(unit="archer").replace(
            "demand spears {", "demand archers {"
        )
        from Compiler.compiler import compile_semantic_demands

        bound = [
            replace(spear_demands[0], strategic_binding=_binding("war-plan")),
            replace(
                _analyze(archer_source)[0],
                strategic_binding=_binding("castle-watch"),
            ),
        ]
        with self.assertRaisesRegex(CompileError, "RES-006"):
            compile_semantic_demands(bound)


if __name__ == "__main__":
    unittest.main()
