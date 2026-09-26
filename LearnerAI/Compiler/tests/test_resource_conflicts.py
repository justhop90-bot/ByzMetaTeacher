import unittest
from unittest.mock import patch
from pathlib import Path
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.ir.capability import (
    ActionSpec,
    Capability,
    CapabilityGraphBuilder,
    CapabilityId,
    CapabilityKind,
    CapabilityProvider,
    CompletionWitness,
    ProviderId,
    ProviderKind,
    PredicateAtom,
    PredicateKind,
    WitnessId,
    WitnessKind,
)
from Compiler.ir.model import SemanticId
from Compiler.compiler import compile_source
from Compiler.parser import parse
from Compiler.semantic import analyze
from Compiler.semantic.capability_bridge import project_capability_graph
from Compiler.diagnostics import DiagnosticSeverity
from Compiler.errors import CompileError
from Compiler.primitives import default_de_registry
from Compiler.semantic.resource_conflicts import (
    ResourceDiagnostic,
    ResourceDiagnosticCode,
    ResourceStatus,
    ResourceValidationReport,
    validate_resource_conflicts,
)


def witness_for(capability, name="built"):
    return CompletionWitness(
        identity=WitnessId("test", name),
        kind=WitnessKind.WORLD_STATE,
        predicate=PredicateAtom(
            kind=PredicateKind.OBSERVATION,
            primitive="building-type-count",
            arguments=("castle", ">", "0"),
            expression=None,
        ),
        establishes=capability,
    )


def provider(
    capability,
    *,
    name,
    conflict_class="BUILD_PASS_SINGLETON",
    arbitration=("__execution_memory__",),
):
    return CapabilityProvider(
        identity=ProviderId("test", name),
        capability=capability,
        kind=ProviderKind.CONSTRUCTION,
        admissibility=PredicateAtom(
            kind=PredicateKind.FEASIBILITY,
            primitive="can-build",
            arguments=("castle",),
            expression=None,
        ),
        action=ActionSpec(
            primitive="build",
            arguments=("castle",),
            conflict_class=conflict_class,
            arbitration=tuple(
                SemanticId("test", owner)
                for owner in arbitration
            ),
        ),
        witness=WitnessId("test", "built"),
    )


def graph_for(*providers):
    capability = CapabilityId("test", "castle")
    builder = CapabilityGraphBuilder()
    builder.add_capability(
        Capability(capability, CapabilityKind.CONSTRUCTION)
    )
    builder.add_witness(witness_for(capability))
    for item in providers:
        builder.add_provider(item)
    return builder.build()


class ResourceConflictTests(unittest.TestCase):
    def _validate(self, graph):
        return validate_resource_conflicts(
            graph,
            default_de_registry(),
        )

    def test_demand_bridge_materializes_typed_resource_claim(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        registry = default_de_registry()
        ir = analyze(parse(source), registry, source_unit="test")
        graph = project_capability_graph(ir, registry)
        claim = graph.providers[0].resource_claim

        self.assertIsNotNone(claim)
        self.assertEqual(
            claim.claimant,
            SemanticId("test", "castle-provider"),
        )
        self.assertEqual(claim.conflict_class, "BUILD_PASS_SINGLETON")
        self.assertEqual(
            claim.arbitration_owner,
            SemanticId("test", "__execution_memory__"),
        )

    def test_compile_pipeline_uses_resource_validation_gate(self):
        diagnostic = ResourceDiagnostic(
            code=ResourceDiagnosticCode.CONFLICT_WITHOUT_OWNER,
            severity=DiagnosticSeverity.ERROR,
            message="provider 'castle-provider' conflict class "
                    "'BUILD_PASS_SINGLETON' has no arbitration owner",
            status=ResourceStatus.BLOCKED,
            provider=SemanticId("test", "castle-provider"),
            conflict_class="BUILD_PASS_SINGLETON",
        )
        report = ResourceValidationReport(
            diagnostics=(diagnostic,),
            claims=(),
            conflicts=(),
        )

        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        with patch(
            "Compiler.compiler.validate_resource_conflicts",
            return_value=report,
        ) as validator:
            with self.assertRaisesRegex(
                CompileError,
                r"RES-003: provider 'castle-provider' conflict class "
                r"'BUILD_PASS_SINGLETON' has no arbitration owner",
            ):
                compile_source(source)
            validator.assert_called_once()


    def test_existing_build_claim_projects_to_typed_transient_resource(self):
        report = self._validate(
            graph_for(
                provider(
                    CapabilityId("test", "castle"),
                    name="castle-builder",
                )
            )
        )

        self.assertTrue(report.valid)
        self.assertEqual(report.diagnostics, ())
        self.assertEqual(len(report.claims), 1)
        claim = report.claims[0]
        self.assertEqual(claim.scope.value, "TRANSIENT")
        self.assertEqual(claim.kind.value, "ACTION_EXCLUSION")
        self.assertEqual(claim.conflict_class, "BUILD_PASS_SINGLETON")
        self.assertEqual(
            claim.arbitration_owner,
            SemanticId("test", "__execution_memory__"),
        )

    def test_missing_arbitration_owner_has_exact_diagnostic(self):
        report = self._validate(
            graph_for(
                provider(
                    CapabilityId("test", "castle"),
                    name="castle-builder",
                    arbitration=(),
                )
            )
        )

        self.assertEqual(
            tuple(
                (
                    item.code.value,
                    item.severity.value,
                    item.status.value,
                    item.message,
                )
                for item in report.diagnostics
            ),
            (
                (
                    "RES-003",
                    "error",
                    "BLOCKED",
                    "provider 'castle-builder' conflict class "
                    "'BUILD_PASS_SINGLETON' has no arbitration owner",
                ),
            ),
        )

    def test_multiple_arbitration_owners_have_exact_diagnostic(self):
        report = self._validate(
            graph_for(
                provider(
                    CapabilityId("test", "castle"),
                    name="castle-builder",
                    arbitration=("owner-a", "owner-b"),
                )
            )
        )

        self.assertEqual(
            tuple(
                (
                    item.code.value,
                    item.severity.value,
                    item.status.value,
                    item.message,
                )
                for item in report.diagnostics
            ),
            (
                (
                    "RES-004",
                    "error",
                    "CONFLICTING",
                    "provider 'castle-builder' conflict class "
                    "'BUILD_PASS_SINGLETON' has multiple arbitration owners: "
                    "test:owner-a, test:owner-b",
                ),
            ),
        )

    def test_conflict_class_with_different_arbitrators_has_exact_diagnostic(self):
        graph = graph_for(
            provider(
                CapabilityId("test", "castle"),
                name="castle-builder",
                arbitration=("owner-a",),
            ),
            provider(
                CapabilityId("test", "castle"),
                name="castle-builder-2",
                arbitration=("owner-b",),
            ),
        )
        report = self._validate(graph)

        self.assertEqual(
            tuple(
                (
                    item.code.value,
                    item.severity.value,
                    item.status.value,
                    item.message,
                )
                for item in report.diagnostics
            ),
            (
                (
                    "RES-006",
                    "error",
                    "CONFLICTING",
                    "conflict class 'BUILD_PASS_SINGLETON' has "
                    "incompatible arbitration owners: test:owner-a, "
                    "test:owner-b",
                ),
            ),
        )

    def test_arbitration_without_conflict_class_has_exact_diagnostic(self):
        report = self._validate(
            graph_for(
                provider(
                    CapabilityId("test", "castle"),
                    name="castle-builder",
                    conflict_class=None,
                    arbitration=("owner",),
                )
            )
        )

        self.assertEqual(
            tuple(
                (
                    item.code.value,
                    item.severity.value,
                    item.status.value,
                    item.message,
                )
                for item in report.diagnostics
            ),
            (
                (
                    "RES-002",
                    "error",
                    "BLOCKED",
                    "provider 'castle-builder' declares arbitration "
                    "without a conflict class",
                ),
            ),
        )

    def test_diagnostics_are_deterministic(self):
        graph = graph_for(
            provider(
                CapabilityId("test", "castle"),
                name="a-builder",
                arbitration=(),
            ),
            provider(
                CapabilityId("test", "castle"),
                name="b-builder",
                arbitration=("owner-a",),
            ),
            provider(
                CapabilityId("test", "castle"),
                name="c-builder",
                arbitration=("owner-b",),
            ),
        )
        first = self._validate(graph)
        second = self._validate(graph)

        self.assertEqual(first.diagnostics, second.diagnostics)
        self.assertEqual(
            tuple(item.code.value for item in first.diagnostics),
            ("RES-003", "RES-006"),
        )


if __name__ == "__main__":
    unittest.main()
