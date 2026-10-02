import unittest

from Compiler.semantic.native_tech_catalog import NativeTechIdError, resolve_tech_id


class NativeTechCatalogTests(unittest.TestCase):
    def test_logistica_site_specific_alias_resolves_to_tech_id(self):
        self.assertEqual(resolve_tech_id("ri-logistica"), 61)

    def test_wheelbarrow_alias_resolves_to_tech_id(self):
        self.assertEqual(resolve_tech_id("ri-wheelbarrow"), 213)

    def test_inventory_alias_resolves_to_same_tech_id(self):
        self.assertEqual(resolve_tech_id("ri-wheel-barrow"), 213)

    def test_display_name_resolves_to_tech_id(self):
        self.assertEqual(resolve_tech_id("wheelbarrow"), 213)

    def test_ambiguous_ai_alias_is_rejected(self):
        with self.assertRaisesRegex(NativeTechIdError, "maps to multiple DE technologies"):
            resolve_tech_id("ri-elite-berserk")

    def test_unknown_technology_is_rejected(self):
        with self.assertRaisesRegex(NativeTechIdError, "unknown native TechId"):
            resolve_tech_id("ri-not-a-real-tech")


if __name__ == "__main__":
    unittest.main()
