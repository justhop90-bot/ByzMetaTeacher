"""Canonical Byzantine build lineage contract tests."""

from __future__ import annotations

import unittest

from tools.build_byzantine_bot import (
    NATIVE_PARSER_REVISION,
    ByzantineProfile,
    build_byzantine_strategy,
    compile_strategy_profile,
)
from LearnerAI.Compiler.ir.civ_profile import resolve_effective_civ


class ByzantineBotBuildTests(unittest.TestCase):
    def test_strategy_compilation_is_byte_deterministic(self):
        effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        profile = build_byzantine_strategy(effective, include_water_continuity=True)
        first = compile_strategy_profile(profile, effective)
        second = compile_strategy_profile(profile, effective)
        self.assertEqual(first, second)
        self.assertGreater(first.count("(defrule"), 0)
        self.assertGreater(len(first.encode("utf-8")), 0)
        self.assertEqual(len(NATIVE_PARSER_REVISION), 40)

    def test_canonical_builder_uses_woven_runtime_contract(self):
        from pathlib import Path

        source = Path("tools/build_byzantine_bot.py").read_text(encoding="utf-8")
        self.assertIn('runtime_artifact = output_dir / "Byzantine.runtime.per"', source)
        self.assertIn("verify_woven_runtime_lineage", source)
        self.assertNotIn("canonical Byzantine runtime overlay is missing", source)

    def test_canonical_builder_retains_authoritative_root_artifact(self):
        from pathlib import Path

        source = Path("tools/build_byzantine_bot.py").read_text(encoding="utf-8")
        self.assertIn('root_runtime = root / PROMOTED_ARTIFACT', source)
        self.assertIn('"runtime_order_owned_by": "checked-in Byzantine.per"', source)


if __name__ == "__main__":
    unittest.main()
