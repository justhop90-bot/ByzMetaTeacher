"""Checked-in Byzantine runtime ordering for compounding Feudal economy research."""

from __future__ import annotations

from pathlib import Path
import unittest


class ByzantineEconomicResearchPriorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.artifact = (
            Path(__file__).resolve().parents[3] / "Byzantine.per"
        ).read_text(encoding="utf-8")

    def test_compounding_feudal_research_runs_before_generic_support(self):
        names = (
            "research-double-bit-axe",
            "research-horse-collar",
            "research-wheelbarrow",
        )
        positions = [
            self.artifact.index(f"; Action issuance: {name}")
            for name in names
        ]
        self.assertEqual(positions, sorted(positions))

    def test_feudal_multipliers_yield_to_feasible_castle(self):
        for name in (
            "research-double-bit-axe",
            "research-horse-collar",
            "research-wheelbarrow",
        ):
            start = self.artifact.index(f"; Action issuance: {name}")
            end = self.artifact.find("; Pending diagnostics:", start + 1)
            if end < 0:
                end = len(self.artifact)
            block = self.artifact[start:end]
            self.assertIn("(can-research-with-escrow", block)
            self.assertIn("(not (can-research-with-escrow castle-age))", block)


if __name__ == "__main__":
    unittest.main()
