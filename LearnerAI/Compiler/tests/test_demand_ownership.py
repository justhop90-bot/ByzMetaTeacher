import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.parser import parse
from Compiler.primitives import default_de_registry
from Compiler.semantic import analyze

SOURCE = """
demand castle {
    require (can-build castle)
    action (build castle)
    witness (building-type-count castle > 0)
    release (building-type-count castle > 0)
}
"""


class DemandOwnershipTests(unittest.TestCase):
    def test_semantic_demand_has_explicit_typed_owner_contract(self):
        demand = analyze(
            parse(SOURCE),
            default_de_registry(),
            source_unit="test",
        )[0]
        ownership = getattr(demand, "ownership", None)

        self.assertIsNotNone(ownership)
        self.assertEqual(ownership.owner.source_unit, "test")
        self.assertEqual(ownership.owner.local_name, "castle")
        self.assertEqual(ownership.demand.source_unit, "test")
        self.assertEqual(ownership.demand.local_name, "castle")


if __name__ == "__main__":
    unittest.main()

# TDD RED verification marker
