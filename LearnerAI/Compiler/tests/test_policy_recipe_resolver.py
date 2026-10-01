import unittest


class ByzantinePolicyRecipeIntegrationTests(unittest.TestCase):
    def test_byzantine_strategy_profile_carries_policy_recipes(self):
        from LearnerAI.Compiler.ir.civ_profile import resolve_effective_civ
        from LearnerAI.Compiler.clients.basilisk import ByzantineProfile, build_byzantine_castle_strategy

        effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        profile = build_byzantine_castle_strategy(effective)

        self.assertTrue(
            hasattr(profile, "policy_recipes"),
            "StrategyProfile must expose typed policy recipes",
        )
        self.assertGreaterEqual(len(profile.policy_recipes), 5)
        self.assertEqual(
            tuple(recipe.identity for recipe in profile.policy_recipes),
            (
                "RANGED_HOLD",
                "MOBILE_LOCAL_DEFENSE",
                "STRICT_RAID",
                "PROTECT_SIEGE",
                "DEER_PUSH",
            ),
        )


if __name__ == "__main__":
    unittest.main()
