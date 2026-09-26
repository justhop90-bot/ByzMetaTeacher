import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.parser import parse
from Compiler.primitives import default_de_registry
from Compiler.semantic import analyze
from Compiler.semantic.capability_bridge import (
    project_capability_graph,
    validate_projected_capabilities,
)
from Compiler.ir.capability import CapabilityKind, PredicateKind, ProviderKind


VALID = """
demand castle {
    require (building-available castle)
    require (can-afford-building castle)
    require (can-build castle)
    action (build castle)
    witness (building-type-count castle > 0)
    release (building-type-count castle > 0)
}
"""


class CapabilityBridgeTests(unittest.TestCase):
    def test_projects_current_demand_ir_to_one_capability_provider_chain(self):
        registry = default_de_registry()
        ir = analyze(parse(VALID), registry, source_unit="test")
        graph = project_capability_graph(ir, registry)

        self.assertEqual(len(graph.demands), 1)
        self.assertEqual(len(graph.capabilities), 1)
        self.assertEqual(len(graph.providers), 1)
        self.assertEqual(len(graph.witnesses), 1)

        capability = graph.capabilities[0]
        provider = graph.providers[0]
        witness = graph.witnesses[0]

        self.assertEqual(capability.kind, CapabilityKind.CONSTRUCTION)
        self.assertEqual(provider.kind, ProviderKind.CONSTRUCTION)
        self.assertEqual(provider.capability, capability.identity)
        self.assertEqual(provider.witness, witness.identity)
        self.assertEqual(witness.establishes, capability.identity)

    def test_preserves_admissibility_feasibility_and_resource_roles(self):
        registry = default_de_registry()
        ir = analyze(parse(VALID), registry, source_unit="test")
        graph = project_capability_graph(ir, registry)
        provider = graph.providers[0]

        self.assertIsNotNone(provider.admissibility)
        kinds = {
            atom.kind
            for atom in _atoms(provider.admissibility)
        }
        self.assertEqual(
            kinds,
            {
                PredicateKind.ADMISSIBILITY,
                PredicateKind.RESOURCE,
                PredicateKind.FEASIBILITY,
            },
        )

    def test_projected_valid_demand_has_no_capability_diagnostics(self):
        registry = default_de_registry()
        ir = analyze(parse(VALID), registry, source_unit="test")

        first = validate_projected_capabilities(ir, registry)
        second = validate_projected_capabilities(ir, registry)

        self.assertTrue(first.valid)
        self.assertEqual(first.diagnostics, ())
        self.assertEqual(first.diagnostics, second.diagnostics)


def _atoms(node):
    from Compiler.ir.capability import Predicate, PredicateAtom

    if isinstance(node, PredicateAtom):
        return (node,)
    result = []
    for child in node.all_of:
        result.extend(_atoms(child))
    for child in node.any_of:
        result.extend(_atoms(child))
    return tuple(result)


if __name__ == "__main__":
    unittest.main()
