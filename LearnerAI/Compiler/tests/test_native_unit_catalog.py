import unittest

from Compiler.errors import CompileError
from Compiler.semantic.native_unit_catalog import NativeUnitIdError, resolve_unit_id


class NativeUnitCatalogTests(unittest.TestCase):
    def test_concrete_unit_symbol_resolves_to_native_object_id(self):
        self.assertEqual(resolve_unit_id("spearman"), 93)

    def test_unit_line_resolves_to_lowest_age_native_object(self):
        self.assertEqual(resolve_unit_id("spearman-line"), 93)

    def test_unknown_unit_symbol_is_rejected(self):
        with self.assertRaisesRegex(NativeUnitIdError, "unknown native UnitId"):
            resolve_unit_id("not-a-real-unit")


if __name__ == "__main__":
    unittest.main()
