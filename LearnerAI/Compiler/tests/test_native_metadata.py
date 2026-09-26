import unittest

from LearnerAI.Compiler.ir.native_metadata import (
    NativeEngineProfile,
    default_de_native_profile,
)


class NativeMetadataTests(unittest.TestCase):
    def test_default_profile_contains_separate_goal_sn_and_timer_ranges(self):
        profile = default_de_native_profile()

        self.assertEqual(profile.goal_range, (1, 16000))
        self.assertEqual(profile.strategic_number_range, (0, 511))
        self.assertEqual(profile.timer_range, (1, 50))

    def test_site_specific_logistica_alias_is_not_treated_as_builtin(self):
        profile = default_de_native_profile()
        symbol = profile.identifier("ri-logistica")

        self.assertEqual(symbol.numeric_id, 61)
        self.assertFalse(symbol.built_in)
        self.assertTrue(symbol.local_alias_required)

        with self.assertRaisesRegex(ValueError, "local alias"):
            profile.require_symbol("ri-logistica")

        resolved = profile.require_symbol("ri-logistica", local_aliases={"ri-logistica"})
        self.assertIsNotNone(resolved)

    def test_profile_is_immutable(self):
        profile = default_de_native_profile()
        self.assertIsInstance(profile, NativeEngineProfile)
        with self.assertRaises(Exception):
            profile.goal_range = (1, 10)


if __name__ == "__main__":
    unittest.main()
