import unittest

from Compiler.ast import Expression
from Compiler.ir import (
    GoalRole,
    GoalSlotRequest,
    LifecycleStorage,
    SemanticId,
    StorageRequestId,
)
from Compiler.ir.capability import (
    ActionSpec,
    Capability,
    CapabilityDemand,
    CapabilityGraphBuilder,
    CapabilityId,
    CapabilityKind,
    CapabilityProvider,
    CompletionWitness,
    DemandId,
    Predicate,
    PredicateAtom,
    PredicateKind,
    ProviderId,
    ProviderKind,
    WitnessId,
    WitnessKind,
)
from Compiler.primitives import default_de_registry
from Compiler.semantic.capability_validation import (
    CapabilityDiagnosticCode,
    DiagnosticSeverity,
    GraphStatus,
    validate_capability_graph,
)


def expr(head, *args):
    return Expression(
        source=f"({head} {' '.join(map(str, args))})",
        head=head,
        args=tuple(args),
    )


def atom(kind, primitive, *args):
    return PredicateAtom(
        kind=kind,
        primitive=primitive,
        arguments=tuple(args),
        expression=expr(primitive, *args),
    )


def lifecycle(name="castle"):
    semantic = SemanticId("test", name)
    return LifecycleStorage(
        GoalSlotRequest(
            StorageRequestId(semantic, "lifecycle"),
            GoalRole.LIFECYCLE_STATE,
        )
    )


def demand(name, capability, *, release=True):
    return CapabilityDemand(
        identity=DemandId("test", name),
        target=capability,
        lifecycle=lifecycle(name),
        release=(atom(PredicateKind.OBSERVATION, "building-type-count", "castle", ">", "0"),)
        if release
        else (),
        owner=SemanticId("test", name),
    )


def build_provider(
    capability,
    *,
    name="build-castle",
    prerequisites=(),
    witness=None,
    admissibility=None,
    action=True,
    provider_kind=ProviderKind.CONSTRUCTION,
    arbitration=True,
):
    provider_id = ProviderId("test", name)
    action_spec = None
    if action:
        action_spec = ActionSpec(
            primitive="build",
            arguments=("castle",),
            conflict_class="BUILD_PASS_SINGLETON",
            arbitration=(SemanticId("test", "build"),) if arbitration else (),
        )
    witness_id = None
    if witness is not None:
        witness_id = witness.identity
    return CapabilityProvider(
        identity=provider_id,
        capability=capability,
        kind=provider_kind,
        prerequisites=tuple(prerequisites),
        admissibility=admissibility,
        action=action_spec,
        witness=witness_id,
    )


def witness_for(capability, *, name="castle-built", kind=WitnessKind.COUNT_STATE):
    return CompletionWitness(
        identity=WitnessId("test", name),
        kind=kind,
        predicate=atom(
            PredicateKind.OBSERVATION,
            "building-type-count",
            "castle",
            ">",
            "0",
        ),
        establishes=capability,
    )


class CapabilityValidationTests(unittest.TestCase):
    def _validate(self, builder):
        return validate_capability_graph(builder.build(), default_de_registry())

    def test_valid_castle_provider_is_connected(self):
        capability = CapabilityId("test", "castle-exists")
        witness = witness_for(capability)
        provider = build_provider(
            capability,
            witness=witness,
            prerequisites=(
                CapabilityId("test", "market-exists"),
            ),
            admissibility=Predicate(
                all_of=(
                    atom(PredicateKind.FEASIBILITY, "can-build", "castle"),
                    atom(PredicateKind.RESOURCE, "can-afford-building", "castle"),
                )
            ),
        )

        builder = CapabilityGraphBuilder()
        builder.add_capability(Capability(capability, CapabilityKind.CONSTRUCTION))
        builder.add_capability(
            Capability(
                CapabilityId("test", "market-exists"),
                CapabilityKind.OBSERVED,
            )
        )
        market_witness = witness_for(
            CapabilityId("test", "market-exists"),
            name="market-existing-witness",
        )
        builder.add_provider(
            CapabilityProvider(
                identity=ProviderId("test", "market-existing"),
                capability=CapabilityId("test", "market-exists"),
                kind=ProviderKind.OBSERVATION,
                admissibility=None,
                witness=market_witness.identity,
            )
        )
        builder.add_witness(witness)
        builder.add_witness(market_witness)
        builder.add_provider(provider)
        builder.add_demand(demand("castle", capability))

        report = self._validate(builder)
        self.assertTrue(report.valid)
        self.assertFalse(report.diagnostics)

    def test_structural_unknown_prerequisite_is_diagnosed(self):
        capability = CapabilityId("test", "castle-exists")
        missing = CapabilityId("test", "blacksmith-exists")
        witness = witness_for(capability)
        provider = build_provider(
            capability,
            witness=witness,
            prerequisites=(missing,),
            admissibility=atom(PredicateKind.FEASIBILITY, "can-build", "castle"),
        )

        builder = CapabilityGraphBuilder()
        builder.add_capability(Capability(capability, CapabilityKind.CONSTRUCTION))
        builder.add_witness(witness)
        builder.add_provider(provider)
        builder.add_demand(demand("castle", capability))

        report = self._validate(builder)
        codes = {item.code for item in report.diagnostics}
        self.assertIn(CapabilityDiagnosticCode.UNKNOWN_PREREQUISITE, codes)

    def test_provider_contract_requires_witness_for_action(self):
        capability = CapabilityId("test", "castle-exists")
        builder = CapabilityGraphBuilder()
        builder.add_capability(Capability(capability, CapabilityKind.CONSTRUCTION))
        builder.add_provider(
            build_provider(
                capability,
                witness=None,
                admissibility=atom(PredicateKind.FEASIBILITY, "can-build", "castle"),
            )
        )
        builder.add_demand(demand("castle", capability))

        report = self._validate(builder)
        self.assertIn(
            CapabilityDiagnosticCode.PROVIDER_NO_WITNESS,
            {item.code for item in report.diagnostics},
        )

    def test_observation_provider_may_have_no_action(self):
        capability = CapabilityId("test", "market-exists")
        witness = witness_for(capability, name="market-observed")
        provider = build_provider(
            capability,
            name="market-existing",
            witness=witness,
            provider_kind=ProviderKind.OBSERVATION,
            action=False,
            admissibility=None,
        )
        builder = CapabilityGraphBuilder()
        builder.add_capability(Capability(capability, CapabilityKind.OBSERVED))
        builder.add_witness(witness)
        builder.add_provider(provider)
        builder.add_demand(demand("market", capability))

        report = self._validate(builder)
        self.assertTrue(report.valid)

    def test_witness_must_establish_provider_capability(self):
        capability = CapabilityId("test", "castle-exists")
        other = CapabilityId("test", "market-exists")
        witness = witness_for(other)

        builder = CapabilityGraphBuilder()
        builder.add_capability(Capability(capability, CapabilityKind.CONSTRUCTION))
        builder.add_capability(Capability(other, CapabilityKind.OBSERVED))
        builder.add_witness(witness)
        builder.add_provider(
            build_provider(
                capability,
                witness=witness,
                admissibility=atom(PredicateKind.FEASIBILITY, "can-build", "castle"),
            )
        )
        builder.add_demand(demand("castle", capability))

        report = self._validate(builder)
        self.assertIn(
            CapabilityDiagnosticCode.WITNESS_NOT_ESTABLISHING,
            {item.code for item in report.diagnostics},
        )

    def test_timing_only_witness_is_rejected(self):
        capability = CapabilityId("test", "castle-exists")
        witness = CompletionWitness(
            identity=WitnessId("test", "castle-time"),
            kind=WitnessKind.WORLD_STATE,
            predicate=atom(PredicateKind.TIMING, "game-time", ">=", "600"),
            establishes=capability,
        )
        builder = CapabilityGraphBuilder()
        builder.add_capability(Capability(capability, CapabilityKind.CONSTRUCTION))
        builder.add_witness(witness)
        builder.add_provider(
            build_provider(
                capability,
                witness=witness,
                admissibility=atom(PredicateKind.FEASIBILITY, "can-build", "castle"),
            )
        )
        builder.add_demand(demand("castle", capability))

        report = self._validate(builder)
        self.assertIn(
            CapabilityDiagnosticCode.TIMING_CANNOT_WITNESS,
            {item.code for item in report.diagnostics},
        )

    def test_provider_requires_feasibility_evidence(self):
        capability = CapabilityId("test", "castle-exists")
        witness = witness_for(capability)
        builder = CapabilityGraphBuilder()
        builder.add_capability(Capability(capability, CapabilityKind.CONSTRUCTION))
        builder.add_witness(witness)
        builder.add_provider(
            build_provider(
                capability,
                witness=witness,
                admissibility=atom(
                    PredicateKind.OBSERVATION,
                    "building-available",
                    "castle",
                ),
            )
        )
        builder.add_demand(demand("castle", capability))

        report = self._validate(builder)
        self.assertIn(
            CapabilityDiagnosticCode.FEASIBILITY_MISSING,
            {item.code for item in report.diagnostics},
        )

    def test_timing_only_admissibility_is_rejected(self):
        capability = CapabilityId("test", "castle-exists")
        witness = witness_for(capability)
        builder = CapabilityGraphBuilder()
        builder.add_capability(Capability(capability, CapabilityKind.CONSTRUCTION))
        builder.add_witness(witness)
        builder.add_provider(
            build_provider(
                capability,
                witness=witness,
                admissibility=atom(PredicateKind.TIMING, "game-time", ">=", "600"),
            )
        )
        builder.add_demand(demand("castle", capability))

        report = self._validate(builder)
        self.assertIn(
            CapabilityDiagnosticCode.TIMING_ONLY_ADMISSIBILITY,
            {item.code for item in report.diagnostics},
        )

    def test_conflicting_action_class_requires_arbitration(self):
        capability = CapabilityId("test", "castle-exists")
        witness = witness_for(capability)
        builder = CapabilityGraphBuilder()
        builder.add_capability(Capability(capability, CapabilityKind.CONSTRUCTION))
        builder.add_witness(witness)
        builder.add_provider(
            build_provider(
                capability,
                witness=witness,
                admissibility=atom(PredicateKind.FEASIBILITY, "can-build", "castle"),
                arbitration=False,
            )
        )
        builder.add_demand(demand("castle", capability))

        report = self._validate(builder)
        self.assertIn(
            CapabilityDiagnosticCode.CONFLICT_NO_ARBITRATION,
            {item.code for item in report.diagnostics},
        )

    def test_rooted_scc_is_not_reported_as_cycle(self):
        a = CapabilityId("test", "a")
        b = CapabilityId("test", "b")
        seed_witness = witness_for(a, name="a-seed")
        b_witness = witness_for(b, name="b-witness")

        builder = CapabilityGraphBuilder()
        builder.add_capability(Capability(a, CapabilityKind.CONSTRUCTION))
        builder.add_capability(Capability(b, CapabilityKind.CONSTRUCTION))
        builder.add_witness(seed_witness)
        builder.add_witness(b_witness)

        builder.add_provider(
            build_provider(
                a,
                name="a-seed",
                prerequisites=(),
                witness=seed_witness,
                admissibility=atom(PredicateKind.FEASIBILITY, "can-build", "castle"),
            )
        )
        builder.add_provider(
            build_provider(
                a,
                name="a-from-b",
                prerequisites=(b,),
                witness=seed_witness,
                admissibility=atom(PredicateKind.FEASIBILITY, "can-build", "castle"),
            )
        )
        builder.add_provider(
            build_provider(
                b,
                name="b-from-a",
                prerequisites=(a,),
                witness=b_witness,
                admissibility=atom(PredicateKind.FEASIBILITY, "can-build", "castle"),
            )
        )
        builder.add_demand(demand("a-demand", a))

        report = self._validate(builder)
        self.assertNotIn(
            CapabilityDiagnosticCode.CYCLE,
            {d.code for d in report.diagnostics},
        )

    def test_unrooted_two_node_scc_reports_cycle_and_dead_end(self):
        a = CapabilityId("test", "a")
        b = CapabilityId("test", "b")
        wa = witness_for(a, name="a-witness")
        wb = witness_for(b, name="b-witness")

        builder = CapabilityGraphBuilder()
        builder.add_capability(Capability(a, CapabilityKind.CONSTRUCTION))
        builder.add_capability(Capability(b, CapabilityKind.CONSTRUCTION))
        builder.add_witness(wa)
        builder.add_witness(wb)
        builder.add_provider(build_provider(
            a,
            name="build-a",
            prerequisites=(b,),
            witness=wa,
            admissibility=atom(PredicateKind.FEASIBILITY, "can-build", "castle"),
        ))
        builder.add_provider(build_provider(
            b,
            name="build-b",
            prerequisites=(a,),
            witness=wb,
            admissibility=atom(PredicateKind.FEASIBILITY, "can-build", "castle"),
        ))
        builder.add_demand(demand("a-demand", a))

        report = self._validate(builder)
        codes = {item.code for item in report.diagnostics}
        self.assertIn(CapabilityDiagnosticCode.CYCLE, codes)
        self.assertIn(CapabilityDiagnosticCode.DEAD_END, codes)

        cycle = next(item for item in report.diagnostics if item.code is CapabilityDiagnosticCode.CYCLE)
        self.assertEqual(tuple(sorted(node.local_name for node in cycle.related)), ("a", "b"))

    def test_providerless_demand_is_unfed(self):
        capability = CapabilityId("test", "castle-exists")
        builder = CapabilityGraphBuilder()
        builder.add_capability(Capability(capability, CapabilityKind.CONSTRUCTION))
        builder.add_demand(demand("castle", capability))

        report = self._validate(builder)
        codes = {item.code for item in report.diagnostics}
        self.assertIn(CapabilityDiagnosticCode.PROVIDERLESS_CAPABILITY, codes)

    def test_missing_release_is_unfinished(self):
        capability = CapabilityId("test", "castle-exists")
        witness = witness_for(capability)
        builder = CapabilityGraphBuilder()
        builder.add_capability(Capability(capability, CapabilityKind.CONSTRUCTION))
        builder.add_witness(witness)
        builder.add_provider(
            build_provider(
                capability,
                witness=witness,
                admissibility=atom(PredicateKind.FEASIBILITY, "can-build", "castle"),
            )
        )
        builder.add_demand(demand("castle", capability, release=False))

        report = self._validate(builder)
        self.assertIn(
            CapabilityDiagnosticCode.RELEASE_NO_COMPLETION_PATH,
            {item.code for item in report.diagnostics},
        )

    def test_diagnostics_are_deterministically_sorted(self):
        capability = CapabilityId("test", "castle-exists")
        builder = CapabilityGraphBuilder()
        builder.add_capability(Capability(capability, CapabilityKind.CONSTRUCTION))
        builder.add_provider(
            build_provider(
                capability,
                witness=None,
                admissibility=atom(PredicateKind.TIMING, "game-time", ">=", "600"),
                arbitration=False,
            )
        )
        builder.add_demand(demand("castle", capability, release=False))

        first = self._validate(builder)
        second = self._validate(builder)
        first_view = [(d.code.value, d.message) for d in first.diagnostics]
        second_view = [(d.code.value, d.message) for d in second.diagnostics]
        self.assertEqual(first_view, second_view)
        self.assertEqual(first.diagnostics, tuple(sorted(
            first.diagnostics,
            key=lambda d: (
                d.location.line if d.location else 0,
                d.location.column if d.location else 0,
                d.code.value,
                d.node.local_name if d.node else "",
                d.message,
            ),
        )))


if __name__ == "__main__":
    unittest.main()
