import unittest

from Compiler.semantic.community_engine import EvidenceClass, PracticeStatus
from Compiler.semantic.native_controller import (
    NativeControllerDomain,
    NativeControllerRelation,
    NativeControlSurfaceKind,
    default_native_controller_catalog,
    NativeController,
    NativeControllerEdge,
    NativeControlSurface,
    NativeControllerCatalog,
)


class NativeControllerSemanticsTests(unittest.TestCase):
    def test_seeded_strategic_number_surface_resolves(self):
        catalog = default_native_controller_catalog()
        surface = catalog.resolve_surface(
            NativeControlSurfaceKind.STRATEGIC_NUMBER,
            "sn-number-explore-groups",
        )
        self.assertEqual(surface.controller_id, "exploration-control")

    def test_duplicate_controller_ids_are_rejected(self):
        controller = NativeController(
            identity="duplicate",
            domain=NativeControllerDomain.ECONOMY,
            evidence=EvidenceClass.COMMUNITY_PRACTICE,
            status=PracticeStatus.EVIDENCE_ONLY,
            sources=("test",),
            description="duplicate test controller",
        )
        catalog = NativeControllerCatalog(
            controllers=(controller, controller),
            surfaces=(),
            edges=(),
        )
        with self.assertRaises(ValueError):
            catalog.validate()

    def test_duplicate_surface_ids_are_rejected(self):
        surface = NativeControlSurface(
            identity="duplicate-surface",
            controller_id="economy",
            kind=NativeControlSurfaceKind.STRATEGIC_NUMBER,
            native_identifier="sn-test",
            evidence=EvidenceClass.COMMUNITY_PRACTICE,
            status=PracticeStatus.EVIDENCE_ONLY,
            sources=("test",),
        )
        controller = NativeController(
            identity="economy",
            domain=NativeControllerDomain.ECONOMY,
            evidence=EvidenceClass.COMMUNITY_PRACTICE,
            status=PracticeStatus.EVIDENCE_ONLY,
            sources=("test",),
            description="duplicate surface owner",
        )
        catalog = NativeControllerCatalog(
            controllers=(controller,),
            surfaces=(surface, surface),
            edges=(),
        )
        with self.assertRaises(ValueError):
            catalog.validate()

    def test_edge_referencing_unknown_controller_is_rejected(self):
        edge = NativeControllerEdge(
            source_controller="attack",
            target_controller="missing",
            relation=NativeControllerRelation.COUPLED_WITH,
            evidence=EvidenceClass.COMMUNITY_PRACTICE,
            status=PracticeStatus.EVIDENCE_ONLY,
            sources=("test",),
        )
        controller = NativeController(
            identity="attack",
            domain=NativeControllerDomain.ATTACK,
            evidence=EvidenceClass.COMMUNITY_PRACTICE,
            status=PracticeStatus.EVIDENCE_ONLY,
            sources=("test",),
            description="edge owner",
        )
        catalog = NativeControllerCatalog(
            controllers=(controller,),
            surfaces=(),
            edges=(edge,),
        )
        with self.assertRaises(ValueError):
            catalog.validate()

    def test_self_interaction_is_rejected(self):
        with self.assertRaises(ValueError):
            NativeControllerEdge(
                source_controller="attack",
                target_controller="attack",
                relation=NativeControllerRelation.COUPLED_WITH,
                evidence=EvidenceClass.COMMUNITY_PRACTICE,
                status=PracticeStatus.EVIDENCE_ONLY,
                sources=("test",),
            )

    def test_evidence_only_surface_cannot_promote_to_executable(self):
        catalog = default_native_controller_catalog()
        with self.assertRaises(ValueError):
            catalog.require_executable_surface(
                NativeControlSurfaceKind.STRATEGIC_NUMBER,
                "sn-number-explore-groups",
            )

    def test_seeded_controller_relations_are_present(self):
        catalog = default_native_controller_catalog()
        relations = {
            (edge.source_controller, edge.relation, edge.target_controller)
            for edge in catalog.edges
        }
        self.assertIn(
            (
                "attack-group-control",
                NativeControllerRelation.REQUIRES_EXPLORATION,
                "exploration-control",
            ),
            relations,
        )
        self.assertIn(
            (
                "town-size-defense-targeting",
                NativeControllerRelation.AFFECTS_TARGETING,
                "attack-group-control",
            ),
            relations,
        )

    def test_catalog_order_is_deterministic(self):
        first = default_native_controller_catalog()
        second = default_native_controller_catalog()
        self.assertEqual(first.fingerprint(), second.fingerprint())
        self.assertEqual(
            tuple(item.identity for item in first.controllers),
            tuple(sorted(item.identity for item in first.controllers)),
        )


    def test_seeded_controller_corpus_is_explicitly_evidence_only(self):
        catalog = default_native_controller_catalog()
        expected = {
            "civilian-task-allocation",
            "duc-search-state",
            "exploration-control",
            "attack-group-control",
            "resource-escrow-control",
            "town-size-defense-targeting",
        }
        self.assertEqual(
            {controller.identity for controller in catalog.controllers},
            expected,
        )
        self.assertTrue(
            all(
                controller.status is PracticeStatus.EVIDENCE_ONLY
                for controller in catalog.controllers
            )
        )

    def test_representative_control_surfaces_are_seeded(self):
        catalog = default_native_controller_catalog()
        for identifier, controller_id in (
            ("sn-food-gatherer-percentage", "civilian-task-allocation"),
            ("sn-number-explore-groups", "exploration-control"),
            ("sn-number-attack-groups", "attack-group-control"),
            ("sn-maximum-town-size", "town-size-defense-targeting"),
            ("set-escrow-percentage", "resource-escrow-control"),
            ("up-find-local", "duc-search-state"),
        ):
            kind = (
                NativeControlSurfaceKind.STRATEGIC_NUMBER
                if identifier.startswith("sn-")
                else NativeControlSurfaceKind.COMMAND
            )
            self.assertEqual(
                catalog.resolve_surface(kind, identifier).controller_id,
                controller_id,
            )

    def test_executable_surface_requires_contractual_status(self):
        catalog = NativeControllerCatalog(
            controllers=(
                NativeController(
                    identity="engine",
                    domain=NativeControllerDomain.ECONOMY,
                    evidence=EvidenceClass.ENGINE_FACT,
                    status=PracticeStatus.CONTRACTED,
                    sources=("native",),
                    description="test",
                ),
            ),
            surfaces=(
                NativeControlSurface(
                    identity="surface",
                    controller_id="engine",
                    kind=NativeControlSurfaceKind.STRATEGIC_NUMBER,
                    native_identifier="sn-test",
                    evidence=EvidenceClass.ENGINE_FACT,
                    status=PracticeStatus.PARTIAL,
                    sources=("native",),
                ),
            ),
            edges=(),
        )
        with self.assertRaises(ValueError):
            catalog.require_executable_surface(
                NativeControlSurfaceKind.STRATEGIC_NUMBER,
                "sn-test",
            )


if __name__ == "__main__":
    unittest.main()
