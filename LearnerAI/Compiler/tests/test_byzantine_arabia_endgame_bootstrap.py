import unittest

from LearnerAI.Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_strategy,
    compile_strategy_profile,
    lower_strategy_profile,
    resolve_effective_civ,
)


class ByzantineArabiaEndgameBootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        cls.profile = build_byzantine_strategy(cls.effective)
        cls.compilation = lower_strategy_profile(cls.profile, cls.effective)
        cls.output = compile_strategy_profile(cls.profile, cls.effective)

    def test_castle_military_seed_demands_bootstrap_upgrade_paths(self):
        demands = {item.identity: item for item in self.profile.demands}
        for identity, line, minimum in (
            ("castle-spearman-seed", "spearman-line", 6),
            ("castle-skirmisher-seed", "skirmisher-line", 6),
            ("castle-scout-cavalry-seed", "scout-cavalry-line", 6),
        ):
            self.assertIn(identity, demands)
            demand = demands[identity]
            self.assertEqual(demand.target.unit_id, line)
            self.assertEqual(demand.target.minimum, minimum)
            self.assertIn("(current-age >= castle-age)", demand.execution.requirements)
            self.assertIn(
                f"(unit-type-count-total {line} < {minimum})",
                demand.execution.requirements,
            )

    def test_imperial_ram_upgrade_chain_is_persistent_and_bootstrapped(self):
        demands = {item.identity: item for item in self.profile.demands}
        for identity in ("research-capped-ram", "research-siege-ram"):
            self.assertIn(identity, demands)
            demand = demands[identity]
            self.assertTrue(
                any("ram-line" in requirement for requirement in demand.execution.requirements)
            )
            self.assertTrue(
                any("can-research-with-escrow" in requirement for requirement in demand.execution.requirements)
            )

    def test_endgame_admission_accepts_ram_siege_and_mature_attack_force(self):
        start = self.output.index("byzantine-endgame-push-admit")
        end = self.output.index("byzantine-endgame-push-live-witness", start)
        admit = self.output[start:end]
        self.assertIn("(unit-type-count-total battering-ram-line >= 4)", admit)
        self.assertIn("(unit-type-count cataphract >= 8)", admit)
        self.assertNotIn("(unit-type-count halberdier >= 18)", admit)
        self.assertNotIn("(unit-type-count 6 >= 18)", admit)
        self.assertNotIn("(unit-type-count hussar >= 12)", admit)

    def test_endgame_attack_package_nested_or_lowers_into_army_ready_rule(self):
        start = self.output.index("byzantine-endgame-push-army-ready")
        end = self.output.index("byzantine-endgame-push-army-not-ready", start)
        army_ready = self.output[start:end]
        self.assertIn("(unit-type-count cataphract >= 8)", army_ready)
        self.assertIn("(unit-type-count varangian-guard >= 8)", army_ready)
        self.assertIn("(unit-type-count knight >= 8)", army_ready)
        self.assertIn("(unit-type-count halberdier >= 8)", army_ready)
        self.assertIn("(unit-type-count hussar >= 8)", army_ready)
        self.assertIn("(unit-type-count 6 >= 8)", army_ready)

    def test_endgame_push_owns_attack_readiness_and_siege_approach_writers(self):
        self.assertIn(
            "(set-goal byzantine-army-attack-ready 1)",
            self.output,
        )
        self.assertIn(
            "(set-goal byzantine-siege-approach byzantine-siege-approach-normal)",
            self.output,
        )
        self.assertIn(
            "(set-goal byzantine-army-attack-ready 0)",
            self.output,
        )

    def test_endgame_push_release_uses_attack_package_instead_of_exact_trash_snapshot(self):
        start = self.output.index("byzantine-endgame-push-release")
        end = self.output.index("byzantine-endgame-push-release-trash", start)
        release = self.output[start:end]
        self.assertIn("(unit-type-count cataphract >= 8)", release)
        self.assertNotIn("(unit-type-count halberdier >= 18)", release)
        self.assertNotIn("(unit-type-count 6 >= 18)", release)
        self.assertNotIn("(unit-type-count hussar >= 12)", release)

    def test_endgame_recovery_no_longer_reasserts_exact_trash_floors(self):
        self.assertNotIn("byzantine-endgame-push-recover-halberdier-floor", self.output)
        self.assertNotIn("byzantine-endgame-push-recover-elite-skirmisher-floor", self.output)
        self.assertNotIn("byzantine-endgame-push-recover-hussar-floor", self.output)
        self.assertNotIn("byzantine-endgame-push-recover-premium", self.output)
        self.assertIn("byzantine-endgame-push-recover-army-package", self.output)
        self.assertIn("byzantine-endgame-push-recover-siege-package", self.output)
        self.assertIn("byzantine-endgame-push-siege-not-ready", self.output)


if __name__ == "__main__":
    unittest.main()
