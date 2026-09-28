import unittest

from Compiler.primitives.native_hygiene import AIRefVersionFamily, EngineVersionScope
from Compiler.primitives.native_hygiene import PerformanceClass
from Compiler.semantic.community_engine import EvidenceClass, PracticeStatus
from Compiler.semantic.native_controller import (
    NativeController,
    NativeControllerCatalog,
    NativeControllerDomain,
    NativeControlSurface,
    NativeControlSurfaceKind,
    default_native_controller_catalog,
)
from Compiler.semantic.native_controller_interactions import (
    NativeControllerInteraction,
    NativeControllerInteractionCatalog,
    NativeControllerInteractionKind,
    NativeInteractionCardinality,
    NativeInteractionEndpoint,
    NativeInteractionEndpointKind,
    NativeInteractionLifetime,
    NativeInteractionMutationOwner,
    NativeInteractionSupportState,
    NativeInteractionVisibility,
    default_native_controller_interaction_catalog,
)


class NativeControllerInteractionTests(unittest.TestCase):
    def setUp(self):
        self.controllers = default_native_controller_catalog()
        self.engine_scope = EngineVersionScope(
            source_families=(AIRefVersionFamily.DE,),
            engine_targets=(AIRefVersionFamily.DE,),
            introduced_family=AIRefVersionFamily.DE,
        )

    def controller(self, identity):
        return NativeInteractionEndpoint(
            NativeInteractionEndpointKind.CONTROLLER, identity
        )

    def surface(self, identity):
        return NativeInteractionEndpoint(
            NativeInteractionEndpointKind.CONTROL_SURFACE, identity
        )

    def interaction(self, identity, source, target, relation, **kwargs):
        return NativeControllerInteraction(
            identity=identity,
            source=source,
            target=target,
            relation=relation,
            evidence=kwargs.pop('evidence', EvidenceClass.COMMUNITY_PRACTICE),
            status=kwargs.pop('status', NativeInteractionSupportState.EVIDENCE_ONLY),
            lifetime=kwargs.pop('lifetime', NativeInteractionLifetime.PERSISTENT),
            visibility=kwargs.pop('visibility', NativeInteractionVisibility.RUNTIME_DEPENDENT),
            mutation_owner=kwargs.pop('mutation_owner', NativeInteractionMutationOwner.NONE),
            sources=kwargs.pop('sources', ('test',)),
            engine_version_scope=kwargs.pop('engine_version_scope', self.engine_scope),
            description=kwargs.pop('description', 'test interaction'),
            performance_class=kwargs.pop('performance_class', None),
            cardinality=kwargs.pop('cardinality', None),
        )

    def test_controller_to_controller_gating_is_typed(self):
        item = self.interaction(
            'attack-gates-exploration',
            self.controller('attack-group-control'),
            self.controller('exploration-control'),
            NativeControllerInteractionKind.GATES,
        )
        catalog = NativeControllerInteractionCatalog((item,))
        catalog.validate(self.controllers)
        self.assertEqual(item.source.kind, NativeInteractionEndpointKind.CONTROLLER)
        self.assertEqual(item.target.kind, NativeInteractionEndpointKind.CONTROLLER)

    def test_surface_to_controller_ownership_is_cross_checked(self):
        surface = self.surface('exploration-control:strategic_number:sn-number-explore-groups')
        item = self.interaction(
            'exploration-sn-controlled-by-exploration-controller',
            surface,
            self.controller('exploration-control'),
            NativeControllerInteractionKind.CONTROLLED_BY,
        )
        catalog = NativeControllerInteractionCatalog((item,))
        catalog.validate(self.controllers)

    def test_unknown_controller_endpoint_is_rejected(self):
        item = self.interaction(
            'bad-controller',
            self.controller('missing-controller'),
            self.controller('exploration-control'),
            NativeControllerInteractionKind.GATES,
        )
        with self.assertRaises(ValueError):
            NativeControllerInteractionCatalog((item,)).validate(self.controllers)

    def test_unknown_surface_endpoint_is_rejected(self):
        item = self.interaction(
            'bad-surface',
            self.surface('missing-surface'),
            self.controller('exploration-control'),
            NativeControllerInteractionKind.CONTROLLED_BY,
        )
        with self.assertRaises(ValueError):
            NativeControllerInteractionCatalog((item,)).validate(self.controllers)

    def test_duplicate_interaction_identity_is_rejected(self):
        item = self.interaction(
            'dup',
            self.controller('attack-group-control'),
            self.controller('exploration-control'),
            NativeControllerInteractionKind.GATES,
        )
        with self.assertRaises(ValueError):
            NativeControllerInteractionCatalog((item, item)).validate(self.controllers)

    def test_self_interaction_is_rejected(self):
        with self.assertRaises(ValueError):
            self.interaction(
                'self',
                self.controller('attack-group-control'),
                self.controller('attack-group-control'),
                NativeControllerInteractionKind.GATES,
            )

    def test_contradictory_reverse_gating_is_rejected(self):
        a = self.interaction(
            'a-gates-b',
            self.controller('attack-group-control'),
            self.controller('exploration-control'),
            NativeControllerInteractionKind.GATES,
        )
        b = self.interaction(
            'b-gates-a',
            self.controller('exploration-control'),
            self.controller('attack-group-control'),
            NativeControllerInteractionKind.GATES,
        )
        with self.assertRaises(ValueError):
            NativeControllerInteractionCatalog((a, b)).validate(self.controllers)

    def test_feedback_is_allowed_bidirectionally_and_not_a_dependency_edge(self):
        a = self.interaction(
            'a-feedback-b',
            self.controller('attack-group-control'),
            self.controller('exploration-control'),
            NativeControllerInteractionKind.FEEDBACK,
        )
        b = self.interaction(
            'b-feedback-a',
            self.controller('exploration-control'),
            self.controller('attack-group-control'),
            NativeControllerInteractionKind.FEEDBACK,
        )
        catalog = NativeControllerInteractionCatalog((a, b))
        catalog.validate(self.controllers)
        self.assertEqual(catalog.dependency_edges(), ())

    def test_evidence_only_interaction_cannot_promote(self):
        item = self.interaction(
            'evidence-only',
            self.controller('attack-group-control'),
            self.controller('exploration-control'),
            NativeControllerInteractionKind.GATES,
        )
        catalog = NativeControllerInteractionCatalog((item,))
        catalog.validate(self.controllers)
        with self.assertRaises(ValueError):
            catalog.require_engine_semantics_mapped('evidence-only')

    def test_engine_semantics_mapped_requires_engine_fact(self):
        item = self.interaction(
            'mapped-community',
            self.controller('attack-group-control'),
            self.controller('exploration-control'),
            NativeControllerInteractionKind.GATES,
            status=NativeInteractionSupportState.ENGINE_SEMANTICS_MAPPED,
        )
        with self.assertRaises(ValueError):
            NativeControllerInteractionCatalog((item,)).validate(self.controllers)

    def test_version_scope_mismatch_is_rejected(self):
        up_only = EngineVersionScope(
            source_families=(AIRefVersionFamily.UP,),
            engine_targets=(AIRefVersionFamily.UP,),
            introduced_family=AIRefVersionFamily.UP,
        )
        item = self.interaction(
            'wrong-version',
            self.controller('attack-group-control'),
            self.controller('exploration-control'),
            NativeControllerInteractionKind.GATES,
            engine_version_scope=up_only,
        )
        with self.assertRaises(ValueError):
            NativeControllerInteractionCatalog((item,)).validate(self.controllers)

    def test_auto_mutation_requires_engine_automatic_owner(self):
        item = self.interaction(
            'compiler-mutation-lie',
            self.surface('exploration-control:strategic_number:sn-number-explore-groups'),
            self.surface('exploration-control:strategic_number:sn-total-number-explorers'),
            NativeControllerInteractionKind.AUTO_MUTATES,
            mutation_owner=NativeInteractionMutationOwner.COMPILER_ACTION,
        )
        with self.assertRaises(ValueError):
            NativeControllerInteractionCatalog((item,)).validate(self.controllers)

    def test_auto_mutation_can_target_a_control_surface(self):
        item = self.interaction(
            'engine-mutates-search-index',
            self.surface('duc-search-state:command:up-filter-include'),
            self.surface('duc-search-state:duc_search_index:local'),
            NativeControllerInteractionKind.AUTO_MUTATES,
            mutation_owner=NativeInteractionMutationOwner.ENGINE_AUTOMATIC,
            visibility=NativeInteractionVisibility.SAME_RULE,
            lifetime=NativeInteractionLifetime.PERSISTENT,
        )
        catalog = NativeControllerInteractionCatalog((item,))
        catalog.validate(self.controllers)

    def test_deterministic_ordering_and_fingerprint(self):
        items = (
            self.interaction(
                'z',
                self.controller('attack-group-control'),
                self.controller('exploration-control'),
                NativeControllerInteractionKind.GATES,
            ),
            self.interaction(
                'a',
                self.controller('exploration-control'),
                self.controller('attack-group-control'),
                NativeControllerInteractionKind.FEEDS,
            ),
        )
        first = NativeControllerInteractionCatalog(items)
        second = NativeControllerInteractionCatalog(tuple(reversed(items)))
        first.validate(self.controllers)
        second.validate(self.controllers)
        self.assertEqual(first.fingerprint(), second.fingerprint())
        self.assertEqual(tuple(i.identity for i in first.interactions), ('a', 'z'))

    def test_invalid_cardinality_range_is_rejected(self):
        with self.assertRaises(ValueError):
            NativeInteractionCardinality(10, 1)


    def test_wrong_control_surface_owner_is_rejected(self):
        item = self.interaction(
            "wrong-owner",
            self.surface("exploration-control:strategic_number:sn-number-explore-groups"),
            self.controller("attack-group-control"),
            NativeControllerInteractionKind.CONTROLLED_BY,
        )
        with self.assertRaises(ValueError):
            NativeControllerInteractionCatalog((item,)).validate(self.controllers)

    def test_seeded_interaction_corpus_is_explicit_and_evidence_bearing(self):
        catalog = default_native_controller_interaction_catalog(self.controllers)
        expected = {
            "attack-groups-gated-by-exploration",
            "town-size-affects-attack-targeting",
            "civilian-allocation-coupled-with-resource-escrow",
            "escrow-gates-production-admission",
            "escrow-gates-research-admission",
            "duc-local-search-feeds-target-control",
            "duc-remote-search-feeds-target-control",
            "duc-filter-include-auto-resets-local-index",
            "duc-filter-include-auto-resets-remote-index",
            "duc-filter-exclude-auto-resets-local-index",
            "duc-filter-exclude-auto-resets-remote-index",
            "duc-filter-range-auto-resets-local-index",
            "duc-filter-range-auto-resets-remote-index",
            "duc-reset-filters-auto-resets-local-index",
            "duc-reset-filters-auto-resets-remote-index",
        }
        self.assertEqual(
            {item.identity for item in catalog.interactions},
            expected,
        )
        self.assertTrue(
            all(
                item.status is NativeInteractionSupportState.EVIDENCE_ONLY
                for item in catalog.interactions
            )
        )

    def test_seeded_duc_interactions_carry_cardinality_and_performance_metadata(self):
        catalog = default_native_controller_interaction_catalog(self.controllers)
        local = catalog.resolve("duc-local-search-feeds-target-control")
        remote = catalog.resolve("duc-remote-search-feeds-target-control")
        self.assertEqual((local.cardinality.minimum, local.cardinality.maximum), (0, 240))
        self.assertEqual((remote.cardinality.minimum, remote.cardinality.maximum), (0, 40))
        self.assertIs(local.performance_class, PerformanceClass.MEDIUM)
        self.assertIs(remote.performance_class, PerformanceClass.FAST)

    def test_feedback_relations_are_not_in_seeded_dependency_edges(self):
        catalog = default_native_controller_interaction_catalog(self.controllers)
        self.assertTrue(
            all(
                item.relation is not NativeControllerInteractionKind.FEEDBACK
                for item in catalog.dependency_edges()
            )
        )

    def test_performance_metadata_is_advisory(self):
        item = self.interaction(
            'search-cost',
            self.controller('duc-search-state'),
            self.controller('attack-group-control'),
            NativeControllerInteractionKind.COSTS,
            performance_class=PerformanceClass.SLOW,
            cardinality=NativeInteractionCardinality(0, 240),
        )
        catalog = NativeControllerInteractionCatalog((item,))
        catalog.validate(self.controllers)
        self.assertIs(item.performance_class, PerformanceClass.SLOW)

    def test_mapped_interaction_requires_version_scope_and_engine_fact(self):
        item = self.interaction(
            'mapped-ok',
            self.controller('attack-group-control'),
            self.controller('exploration-control'),
            NativeControllerInteractionKind.GATES,
            evidence=EvidenceClass.ENGINE_FACT,
            status=NativeInteractionSupportState.ENGINE_SEMANTICS_MAPPED,
        )
        catalog = NativeControllerInteractionCatalog((item,))
        catalog.validate(self.controllers)
        self.assertIs(catalog.resolve('mapped-ok').status, NativeInteractionSupportState.ENGINE_SEMANTICS_MAPPED)


if __name__ == '__main__':
    unittest.main()