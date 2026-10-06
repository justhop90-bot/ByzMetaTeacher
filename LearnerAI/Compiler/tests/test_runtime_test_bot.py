from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

import tools.synchronize_byzantine_runtime as sync_runtime


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

    def _assert_named_operands_are_declared(
        self,
        expressions: tuple[str, ...],
        *,
        label: str,
        source: str | None = None,
    ) -> None:
        source = self.runtime if source is None else source
        declared = {
            match.group(1)
            for match in re.finditer(
                r"\(defconst\s+([^\s()]+)\s+([^\s()]+)\)",
                source,
            )
        }
        missing: list[tuple[int, str, str]] = []
        for expression in expressions:
            for match in re.finditer(
                rf"\({expression}\s+([^\s()]+)",
                self.runtime,
            ):
                operand = match.group(1)
                if re.fullmatch(r"-?\d+", operand):
                    continue
                line = source[:match.start()].count("\n") + 1
                if operand not in declared:
                    missing.append((line, expression, operand))
        self.assertEqual(
            missing,
            [],
            f"{label} references undeclared runtime constants: {missing[:25]}",
        )

    def test_named_goal_references_are_declared(self) -> None:
        runtime = self.runtime
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime_path = root / "Byzantine.per"
            generated = sync_runtime.GENERATED
            if generated.exists():
                runtime_path.write_text(runtime, encoding="utf-8")
                original_runtime = sync_runtime.RUNTIME
                sync_runtime.RUNTIME = runtime_path
                try:
                    sync_runtime.synchronize()
                    runtime = runtime_path.read_text(encoding="utf-8")
                finally:
                    sync_runtime.RUNTIME = original_runtime

        self._assert_named_operands_are_declared(
            ("goal", "set-goal", "up-compare-goal", "up-modify-goal"),
            label="goal",
            source=runtime,
        )

    def test_named_timer_references_are_declared(self) -> None:
        self._assert_named_operands_are_declared(
            ("enable-timer", "disable-timer", "timer-triggered"),
            label="timer",
        )

    def test_named_strategic_number_references_are_declared(self) -> None:
        self._assert_named_operands_are_declared(
            (
                "strategic-number",
                "set-strategic-number",
                "up-compare-sn",
                "up-modify-sn",
            ),
            label="strategic-number",
        )

    def test_runtime_defconst_names_are_unique(self) -> None:
        names = [
            match.group(1)
            for match in re.finditer(
                r"\(defconst\s+([^\s()]+)\s+([^\s()]+)\)",
                self.runtime,
            )
        ]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        self.assertEqual(duplicates, [])

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
            "(defconst byzantine-endgame-push-state ",
            "(defconst byzantine-endgame-push-timer 21)",
            "(defconst byzantine-remote-resource-productivity-timer 22)",
            "(set-strategic-number sn-minimum-attack-group-size 6)",
            "(set-strategic-number sn-maximum-attack-group-size 20)",
            "(attack-soldier-count > 0)",
            "(timer-triggered byzantine-endgame-push-timer)",
        ):
            self.assertIn(expr, self.runtime)

    def test_endgame_push_runtime_uses_the_bounded_land_group_policy(self) -> None:
        ready = next(
            rule
            for rule in self.rules
            if "(goal byzantine-endgame-push-state 0)" in rule
            and "(current-age >= imperial-age)" in rule
            and "(set-strategic-number sn-minimum-attack-group-size 6)" in rule
        )
        self.assertIn(
            "(set-strategic-number sn-maximum-attack-group-size 20)",
            ready,
        )
        self.assertNotIn(
            "(set-strategic-number sn-maximum-attack-group-size 40)",
            ready,
        )

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

    def test_hussar_research_uses_light_cavalry_bootstrap_and_both_escrow_resources(self) -> None:
        matching = [
            rule
            for rule in self.rules
            if "(goal demand-research-hussar 1)" in rule
            and "(research hussar)" in rule
            and "(can-research-with-escrow hussar)" in rule
        ]
        self.assertEqual(len(matching), 1)
        rule = matching[0]
        self.assertIn("(current-age >= imperial-age)", rule)
        self.assertIn("(unit-type-count 546 >= 6)", rule)
        self.assertIn("(release-escrow food)", rule)
        self.assertIn("(release-escrow gold)", rule)
        self.assertNotIn("(unit-type-count hussar >= 1)", rule)
        self.assertNotIn("(players-unit-type-count any-enemy mangonel-line >= 2)", rule)
        self.assertNotIn("byzantine-imperial-posture-siege", rule)

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

    def test_open_ground_attack_ready_path_issues_attack_now(self) -> None:
        matching = [
            rule
            for rule in self.rules
            if "(current-age >= castle-age)" in rule
            and "(goal byzantine-army-attack-ready 1)" in rule
            and "(goal byzantine-siege-approach byzantine-siege-approach-normal)" in rule
            and "(goal byzantine-offensive-objective-state "
            "byzantine-offensive-objective-state-idle)" in rule
            and "(goal byzantine-offensive-objective-claim 0)" in rule
            and "(set-strategic-number sn-number-attack-groups 200)" in rule
        ]
        self.assertEqual(len(matching), 1)
        self.assertIn("(attack-now)", matching[0])
        self.assertIn("(set-goal byzantine-army-attack-ready 2)", matching[0])

    def test_imperial_baseline_attack_issues_attack_now_with_minimal_force(self) -> None:
        matching = [
            rule
            for rule in self.rules
            if "(current-age >= imperial-age)" in rule
            and "(military-population >= 4)" in rule
            and "(attack-soldier-count <= 0)" in rule
            and "(attack-now)" in rule
        ]
        self.assertEqual(len(matching), 1)
        self.assertNotIn("(goal byzantine-army-attack-ready 1)", matching[0])
        self.assertIn("(set-strategic-number sn-number-attack-groups 200)", matching[0])
        self.assertIn("(set-strategic-number sn-percent-attack-soldiers 100)", matching[0])
        self.assertIn("(set-strategic-number sn-minimum-attack-group-size 4)", matching[0])
        self.assertIn("(set-strategic-number sn-maximum-attack-group-size 40)", matching[0])

    def test_reposition_controller_has_single_town_under_attack_guard(self) -> None:
        matching = [
            rule
            for rule in self.rules
            if "byzantine-army-reposition-state byzantine-army-reposition-idle" in rule
            and "(town-under-attack)" in rule
        ]
        self.assertTrue(matching)
        for rule in matching:
            self.assertEqual(rule.count("(town-under-attack)"), 1, rule[:600])

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
