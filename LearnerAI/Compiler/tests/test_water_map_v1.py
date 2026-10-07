from __future__ import annotations

import unittest

from Compiler.clients.basilisk import ByzantineProfile, resolve_effective_civ
from Compiler.ir.strategy import build_byzantine_strategy, lower_strategy_profile


class ByzantineWaterMapV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())

    def test_compiler_owns_authoritative_water_classification(self):
        profile = build_byzantine_strategy(self.effective)
        self.assertEqual(
            profile.observation("strategy-water-map").expression,
            "(or (map-type islands) (map-type pacific-islands))",
        )
        self.assertEqual(
            profile.observation("strategy-pacific-islands").expression,
            "(map-type pacific-islands)",
        )

    def test_water_arbitration_is_compiler_owned_and_pacific_is_land_first(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        self.assertIsNotNone(control)
        assert control is not None
        rules = {rule.identity: rule for rule in control.rules}

        enable = rules["strategic-arbitration-observation-enable-strategy-water-islands"]
        disable = rules["strategic-arbitration-observation-disable-strategy-water-islands"]
        enable_text = " ".join(fact.source for fact in enable.facts)
        disable_text = " ".join(fact.source for fact in disable.facts)
        self.assertIn("(or (map-type islands) (map-type pacific-islands))", enable_text)
        self.assertIn("(not (or (map-type islands) (map-type pacific-islands)))", disable_text)

        water_candidate = rules["strategic-arbitration-candidate-enable-water-investment"]
        water_candidate_text = " ".join(fact.source for fact in water_candidate.facts)
        self.assertIn("(goal arb-o01 1)", water_candidate_text)
        self.assertIn("(not (map-type pacific-islands))", water_candidate_text)

        castle_candidate = rules["strategic-arbitration-candidate-enable-castle-trajectory"]
        castle_candidate_text = " ".join(fact.source for fact in castle_candidate.facts)
        self.assertIn("(or (not (goal arb-o01 1)) (map-type pacific-islands))", castle_candidate_text)

    def test_pacific_water_support_does_not_consume_primary_land_intent(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None
        rules = {rule.identity: rule for rule in control.rules}

        select_water = rules["strategic-primary-intent-select-water-investment-from-0"]
        select_castle = rules["strategic-primary-intent-select-castle-trajectory-from-0"]

        water_guard = " ".join(fact.source for fact in select_water.facts)
        castle_guard = " ".join(fact.source for fact in select_castle.facts)
        self.assertIn("(goal arb-c01 1)", water_guard)
        self.assertIn("(goal arb-c02 1)", castle_guard)
        self.assertIn("(not (goal arb-c01 1))", castle_guard)

    def test_runtime_sync_replaces_stale_water_opening_selector_from_generated_artifact(self):
        from pathlib import Path
        import tools.synchronize_byzantine_runtime as sync_runtime

        generated = sync_runtime.GENERATED.read_text(encoding="utf-8")
        runtime = sync_runtime.RUNTIME.read_text(encoding="utf-8")
        generated_selector = sync_runtime._block(
            generated,
            "; Native control rule: opening-selector-water-control",
            "; Native control rule: opening-selector-fast-castle",
        )
        self.assertIn("(map-type pacific-islands)", generated_selector)

        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime_path = root / "Byzantine.per"
            generated_path = root / "generated.per"
            runtime_path.write_text(runtime, encoding="utf-8")
            generated_path.write_text(generated, encoding="utf-8")
            original_runtime = sync_runtime.RUNTIME
            original_generated = sync_runtime.GENERATED
            sync_runtime.RUNTIME = runtime_path
            sync_runtime.GENERATED = generated_path
            try:
                sync_runtime.synchronize()
                synchronized = runtime_path.read_text(encoding="utf-8")
            finally:
                sync_runtime.RUNTIME = original_runtime
                sync_runtime.GENERATED = original_generated

        synchronized_selector = sync_runtime._block(
            synchronized,
            "; Native control rule: opening-selector-water-control",
            "; Native control rule: opening-selector-fast-castle",
        )
        self.assertIn("(map-type pacific-islands)", synchronized_selector)
        self.assertNotIn(
            "    (map-type islands)\n    (or (players-unit-type-count any-enemy galley-line >= 2)",
            synchronized_selector,
        )


if __name__ == "__main__":
    unittest.main()
