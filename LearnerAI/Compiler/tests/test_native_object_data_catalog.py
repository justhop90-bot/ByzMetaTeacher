import unittest

from Compiler.semantic.native_object_data_catalog import (
    NativeObjectDataError,
    resolve_object_data_id,
)


class NativeObjectDataCatalogTests(unittest.TestCase):
    def test_object_data_id_resolves(self):
        self.assertEqual(resolve_object_data_id("0"), 0)

    def test_last_checked_in_object_data_id_resolves(self):
        self.assertEqual(resolve_object_data_id("90"), 90)

    def test_negative_index_is_not_valid_for_get_object_data(self):
        with self.assertRaisesRegex(NativeObjectDataError, "not valid for up-get-object-data"):
            resolve_object_data_id("-1")

    def test_out_of_inventory_id_is_rejected(self):
        with self.assertRaisesRegex(NativeObjectDataError, "not present"):
            resolve_object_data_id("91")

    def test_symbolic_identifier_is_rejected(self):
        with self.assertRaisesRegex(NativeObjectDataError, "must be a numeric"):
            resolve_object_data_id("object-data-id")


if __name__ == "__main__":
    unittest.main()
