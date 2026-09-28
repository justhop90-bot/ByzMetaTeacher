import unittest

from Compiler.primitives.strategic_number_catalog import (
    STRATEGIC_NUMBER_CATALOG_VERSION,
    default_strategic_number_catalog,
)


class StrategicNumberCatalogTests(unittest.TestCase):
    def test_catalog_is_versioned_and_covers_exact_engine_namespace(self):
        catalog = default_strategic_number_catalog()
        self.assertEqual(
            catalog.version,
            STRATEGIC_NUMBER_CATALOG_VERSION,
        )
        self.assertEqual(
            catalog.all_ids,
            frozenset(range(512)),
        )
        self.assertEqual(
            catalog.de_documented_ids.isdisjoint(catalog.compiler_candidate_ids),
            True,
        )

    def test_catalog_excludes_sn_511_from_compiler_candidates(self):
        catalog = default_strategic_number_catalog()
        self.assertNotIn(511, catalog.compiler_candidate_ids)
        self.assertGreaterEqual(len(catalog.compiler_candidate_ids), 1)

    def test_catalog_source_fingerprint_is_stable(self):
        first = default_strategic_number_catalog()
        second = default_strategic_number_catalog()
        self.assertEqual(first.source_sha256, second.source_sha256)
        self.assertEqual(first.inventory.inventory_sha, second.inventory.inventory_sha)


if __name__ == "__main__":
    unittest.main()
