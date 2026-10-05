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

    def test_canonical_build_fails_closed_without_declared_runtime_overlay(self):
        import tempfile
        from pathlib import Path

        from tools import build_byzantine_bot

        original_root = build_byzantine_bot.ROOT
        original_overlay = Path("runtime/byzantine/Byzantine.runtime-overlay.per")
        try:
            self.assertFalse(
                original_overlay.is_file(),
                "main is expected to remain fail-closed until the canonical overlay is extracted",
            )
            with self.assertRaisesRegex(RuntimeError, r"BYZ-ASSEMBLY-003"):
                build_byzantine_bot.build(Path("dist/byzantine"))
        finally:
            build_byzantine_bot.ROOT = original_root

    def test_canonical_builder_no_longer_uses_old_dist_artifact_name(self):
        from pathlib import Path

        source = Path("tools/build_byzantine_bot.py").read_text(encoding="utf-8")
        self.assertNotIn('output_dir / "Byzantine.per"', source)
        self.assertIn('output_dir / "Byzantine.compiler.per"', source)


if __name__ == "__main__":
    unittest.main()
