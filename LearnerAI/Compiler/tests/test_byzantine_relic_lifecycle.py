import unittest

from Compiler.clients.basilisk import ByzantineProfile, build_byzantine_strategy, compile_strategy_profile, lower_strategy_profile
from Compiler.ir.civ_profile import resolve_effective_civ
from Compiler.ir.native_duc import NativeDucLifecycleStage


class ByzantineRelicLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        self.profile = build_byzantine_strategy(self.effective)

    def test_relic_lifecycle_is_compiler_owned_and_complete(self):
        compilation = lower_strategy_profile(self.profile, self.effective)
        plan = compilation.duc_plan
        self.assertIsNotNone(plan)
        assert plan is not None

        rules = {
            rule.identity: rule
            for rule in plan.rules
            if rule.identity.startswith("byzantine-relic-control-")
        }
        self.assertEqual(
            tuple(rules),
            (
                "byzantine-relic-control-acquire",
                "byzantine-relic-control-pickup-witness",
                "byzantine-relic-control-return",
                "byzantine-relic-control-release-witness",
                "byzantine-relic-control-recovery",
            ),
        )

        self.assertIn(
            NativeDucLifecycleStage.ADMISSIBILITY,
            rules["byzantine-relic-control-acquire"].lifecycle,
        )
        self.assertIn(
            NativeDucLifecycleStage.TARGET,
            rules["byzantine-relic-control-acquire"].lifecycle,
        )
        self.assertIn(
            NativeDucLifecycleStage.DISPATCH,
            rules["byzantine-relic-control-acquire"].lifecycle,
        )
        self.assertIn(
            NativeDucLifecycleStage.PICKUP_WITNESS,
            rules["byzantine-relic-control-pickup-witness"].lifecycle,
        )
        self.assertIn(
            NativeDucLifecycleStage.RETURN,
            rules["byzantine-relic-control-return"].lifecycle,
        )
        self.assertIn(
            NativeDucLifecycleStage.RELEASE_WITNESS,
            rules["byzantine-relic-control-release-witness"].lifecycle,
        )
        self.assertIn(
            NativeDucLifecycleStage.RECOVERY,
            rules["byzantine-relic-control-recovery"].lifecycle,
        )

        acquire = rules["byzantine-relic-control-acquire"]
        acquire_sources = tuple(item.source for item in (*acquire.facts, *acquire.actions))
        self.assertIn("(up-gaia-type-count-total c: 285 > 0)", acquire_sources)
        self.assertIn("(up-modify-sn sn-focus-player-number c:= 0)", acquire_sources)
        self.assertIn("(up-find-remote c: 285 c: 1)", acquire_sources)
        self.assertIn("(up-set-target-object search-remote c: 0)", acquire_sources)
        self.assertIn("(up-find-local c: monk c: 1)", acquire_sources)
        self.assertIn(
            "(up-target-objects 0 0 -1 stance-defensive)",
            acquire_sources,
        )

        pickup = rules["byzantine-relic-control-pickup-witness"]
        self.assertIn(
            "(up-find-local c: 286 c: 1)",
            tuple(item.source for item in pickup.actions),
        )

        control = compilation.control_plan
        self.assertIsNotNone(control)
        assert control is not None
        pickup_control = next(
            rule for rule in control.rules
            if rule.identity == "byzantine-relic-control-pickup-witness"
        )
        self.assertIn(
            "(unit-type-count-total 286 >= 1)",
            tuple(item.source for item in pickup_control.facts),
        )

        return_rule = rules["byzantine-relic-control-return"]
        return_sources = tuple(item.source for item in (*return_rule.facts, *return_rule.actions))
        self.assertIn(
            return_sources,
        )
        self.assertIn("(up-find-local c: 104 c: 1)", return_sources)
        self.assertIn("(up-find-local c: 286 c: 1)", return_sources)
        self.assertIn(
            "(up-target-objects 0 0 -1 stance-defensive)",
            return_sources,
        )

    def test_relic_lifecycle_compiles_deterministically(self):
        first = compile_strategy_profile(self.profile, self.effective)
        second = compile_strategy_profile(self.profile, self.effective)
        self.assertEqual(first, second)

        required = (
            "(defconst byzantine-relic-control-state",
            "(defconst byzantine-relic-control-timer",
            "; Native DUC rule: byzantine-relic-control-acquire",
            "; Native DUC rule: byzantine-relic-control-pickup-witness",
            "; Native DUC rule: byzantine-relic-control-return",
            "(unit-type-count-total 286 >= 1)",
            "(up-find-remote c: 285 c: 1)",
            "(up-find-local c: 286 c: 1)",
        )
        missing = tuple(fragment for fragment in required if fragment not in first)
        self.assertEqual(missing, ())
