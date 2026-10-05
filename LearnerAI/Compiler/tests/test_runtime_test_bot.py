from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "Byzantine.per"
COMPILER_STRATEGY = ROOT / "LearnerAI" / "Compiler" / "ir" / "strategy.py"
COMPILER_PACK = ROOT / "LearnerAI" / "Compiler" / "ir" / "community_strategy_packs.py"


def defrule_blocks(source: str) -> list[str]:
    blocks: list[str] = []
    cursor = 0
    while True:
        start = source.find("(defrule", cursor)
        if start < 0:
            return blocks
        depth = 0
        end = -1
        for index in range(start, len(source)):
            char = source[index]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end < 0:
            raise AssertionError("unterminated defrule")
        blocks.append(source[start:end])
        cursor = end


class ByzantineRuntimeTestBot(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = RUNTIME.read_text(encoding="utf-8")
        cls.compiler_strategy = COMPILER_STRATEGY.read_text(encoding="utf-8")
        cls.compiler_pack = COMPILER_PACK.read_text(encoding="utf-8")
        cls.rules = defrule_blocks(cls.runtime)

    def test_latest_compiler_endgame_contract_has_runtime_semantic_witness(self) -> None:
        self.assertIn('"byzantine-endgame-push-state"', self.compiler_strategy)
        for identity in (
            '"byzantine-endgame-push-army-ready"',
            '"byzantine-endgame-push-admit"',
            '"byzantine-endgame-push-live-witness"',
            '"byzantine-endgame-push-pulse-expiry"',
            '"byzantine-endgame-push-release"',
            '"byzantine-endgame-push-recovery-release"',
        ):
            self.assertIn(identity, self.compiler_strategy)

        for expr in (
            "(defconst byzantine-endgame-push-state 16190)",
            "(set-strategic-number sn-minimum-attack-group-size 6)",
            "(set-strategic-number sn-maximum-attack-group-size 40)",
            "(attack-soldier-count > 0)",
            "(timer-triggered byzantine-endgame-push-timer)",
        ):
            self.assertIn(expr, self.runtime)

    def test_varangian_floor_matches_current_compiler_pressure_model(self) -> None:
        self.assertIn(
            'reason_ref="strategy-enemy-infantry-pressure"',
            self.compiler_pack,
        )
        self.assertIn(
            'minimum=2,',
            self.compiler_pack[self.compiler_pack.index('identity="castle-varangian-guard-floor"'):
                           self.compiler_pack.index('identity="castle-varangian-guard-floor"') + 700],
        )

        self.assertIn("(players-unit-type-count any-enemy militia-line >= 5)", self.runtime)
        self.assertIn("(goal counter-package-infantry_pressure_castle 1)", self.runtime)

    def test_no_dark_age_stone_camp_issuance(self) -> None:
        for rule in self.rules:
            if "(build mining-camp)" not in rule:
                continue
            if "resource-found stone" in rule:
                self.assertIn("(current-age >= feudal-age)", rule)
                self.assertNotIn("(current-age == dark-age)", rule)

    def test_every_build_train_and_research_action_has_a_capability_guard(self) -> None:
        for rule in self.rules:
            if "=>" not in rule:
                continue
            pre, post = rule.split("=>", 1)

            if "(build " in post or "(build-forward " in post or "(up-build " in post:
                self.assertRegex(
                    pre,
                    r"\(can-build(?:-with-escrow)?\b|\(up-can-build",
                )

            if "(train " in post:
                self.assertRegex(
                    pre,
                    r"\(can-train(?:-with-escrow)?\b",
                )

            if "(research " in post:
                self.assertRegex(
                    pre,
                    r"\(can-research(?:-with-escrow)?\b",
                )

    def test_attack_now_is_not_unconditionally_issued(self) -> None:
        attack_rules = [rule for rule in self.rules if "(attack-now)" in rule]
        self.assertGreater(len(attack_rules), 0)
        for rule in attack_rules:
            pre = rule.split("=>", 1)[0]
            self.assertTrue(
                "(goal byzantine-army-attack-ready " in pre
                or "(attack-soldier-count " in pre,
                rule[:500],
            )

    def test_duplicate_town_under_attack_guard_is_removed(self) -> None:
        self.assertNotIn(
            "(or\n        (town-under-attack)\n        (town-under-attack)\n    )",
            self.runtime,
        )

    def test_runtime_parentheses_and_rule_inventory(self) -> None:
        depth = 0
        for char in self.runtime:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                self.assertGreaterEqual(depth, 0)
        self.assertEqual(depth, 0)
        self.assertGreaterEqual(len(self.rules), 2000)
        self.assertEqual(len(re.findall(r"\(defrule\b", self.runtime)), len(self.rules))


if __name__ == "__main__":
    unittest.main()
