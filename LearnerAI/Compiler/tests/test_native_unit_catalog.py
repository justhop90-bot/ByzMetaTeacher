import unittest

from Compiler.compiler import compile_source
from Compiler.errors import CompileError
from Compiler.semantic.native_unit_catalog import (
    NATIVE_UNIT_ALIASES,
    NativeUnitIdError,
    _unit_ids_for,
    resolve_unit_id,
)


class NativeUnitCatalogTests(unittest.TestCase):
    def test_concrete_unit_symbol_resolves_to_native_object_id(self):
        self.assertEqual(resolve_unit_id("spearman"), 93)

    def test_unit_line_resolves_to_lowest_age_native_object(self):
        self.assertEqual(resolve_unit_id("spearman-line"), 93)

    def test_unknown_unit_symbol_is_rejected(self):
        with self.assertRaisesRegex(NativeUnitIdError, "unknown native UnitId"):
            resolve_unit_id("not-a-real-unit")

    def test_inventory_gap_aliases_resolve_by_manifest_evidence(self):
        self.assertEqual(resolve_unit_id("demolition-raft"), 1104)
        self.assertEqual(resolve_unit_id("carrack"), 2628)

    def test_alias_backed_numeric_ids_resolve(self):
        self.assertEqual(resolve_unit_id("1104"), 1104)
        self.assertEqual(resolve_unit_id("2628"), 2628)

    def test_aliases_never_shadow_inventory(self):
        for symbol, _ in NATIVE_UNIT_ALIASES:
            self.assertEqual(_unit_ids_for(symbol), ())
        # Inventory precedence is structural: resolution consults aliases
        # only after inventory lookup fails.
        self.assertEqual(resolve_unit_id("spearman"), 93)
        self.assertEqual(resolve_unit_id("man-at-arms"), 75)

    def test_alias_resolution_normalizes_case(self):
        self.assertEqual(resolve_unit_id("Demolition-Raft"), 1104)
        self.assertEqual(resolve_unit_id("Carrack"), 2628)

    def test_aliased_unit_compiles_production_lifecycle(self):
        source = """
        demand demolition-raft-line {
            require (unit-type-count-total demolition-raft < 2)
            require (can-train demolition-raft)
            action (train demolition-raft)
            witness (unit-type-count demolition-raft >= 2)
            release (unit-type-count demolition-raft >= 2)
        }
        """
        output = compile_source(source)
        self.assertIn("(train demolition-raft)", output)
        self.assertIn("(can-train demolition-raft)", output)
        self.assertIn("(up-pending-objects c: 1104 >= 1)", output)


if __name__ == "__main__":
    unittest.main()
