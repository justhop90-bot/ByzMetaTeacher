"""Semantic isolation gates for the checked-in Byzantine runtime artifact."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "Byzantine.per"

DEFCONST_RE = re.compile(r"\(defconst\s+([^\s()]+)\s+(-?\d+)\)")
GOAL_OP_RE = re.compile(
    r"\((?:goal|set-goal|up-compare-goal|up-modify-goal)\s+([^\s()]+)"
)
POINT_RE = re.compile(r"\(up-get-point\s+position-object\s+([^\s()]+)")
SEARCH_RE = re.compile(r"\(up-get-search-state\s+([^\s()]+)")
TIMER_RE = re.compile(
    r"\((?:enable-timer|disable-timer|timer-triggered)\s+([^\s()]+)"
)
SN_WRITE_RE = re.compile(
    r"\((?:set-strategic-number|up-modify-sn)\s+([^\s()]+)"
)


def _defs(source: str) -> dict[str, tuple[int, int]]:
    return {
        match.group(1): (int(match.group(2)), source[: match.start()].count("\n") + 1)
        for match in DEFCONST_RE.finditer(source)
    }


def _storage_intervals(source: str):
    definitions = _defs(source)
    intervals = []

    def add(name: str, width: int, kind: str, line: int) -> None:
        value, definition_line = definitions[name]
        intervals.append(
            {
                "name": name,
                "start": value,
                "end": value + width - 1,
                "width": width,
                "kind": kind,
                "line": definition_line,
                "use_line": line,
            }
        )

    lines = source.splitlines()
    for line_number, line in enumerate(lines, start=1):
        for match in GOAL_OP_RE.finditer(line):
            name = match.group(1)
            if name in definitions and not name.isdigit() and not re.fullmatch(
                r"-?\d+", name
            ):
                add(name, 1, "GOAL_SLOT", line_number)
        for match in POINT_RE.finditer(line):
            name = match.group(1)
            if name in definitions:
                add(name, 2, "POINT_PAIR", line_number)
        for match in SEARCH_RE.finditer(line):
            name = match.group(1)
            if name in definitions:
                add(name, 4, "SEARCH_STATE", line_number)

    dedup = {}
    for interval in intervals:
        key = (interval["name"], interval["kind"], interval["width"])
        dedup[key] = interval
    return tuple(dedup.values())


class ByzantineRuntimeSemanticIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = RUNTIME.read_text(encoding="utf-8")
        cls.definitions = _defs(cls.runtime)
        cls.intervals = _storage_intervals(cls.runtime)

    def test_live_goal_storage_stays_inside_native_goal_range(self) -> None:
        failures = [
            interval
            for interval in self.intervals
            if interval["start"] < 1 or interval["end"] > 16_000
        ]
        self.assertEqual(
            failures,
            [],
            "live Goal storage escapes native 1..16000: "
            + repr(failures[:20]),
        )

    def test_live_goal_storage_is_pairwise_disjoint(self) -> None:
        failures = []
        ordered = sorted(self.intervals, key=lambda item: (item["start"], item["end"], item["name"]))
        for index, first in enumerate(ordered):
            for second in ordered[index + 1 :]:
                if second["start"] > first["end"]:
                    break
                if first["name"] == second["name"]:
                    continue
                failures.append((first, second))
        self.assertEqual(
            failures,
            [],
            "live Goal/GoalSpan storage overlaps: " + repr(failures[:20]),
        )

    def test_live_timer_storage_is_unique_and_in_range(self) -> None:
        timer_names: dict[int, list[str]] = {}
        for match in TIMER_RE.finditer(self.runtime):
            name = match.group(1)
            if name not in self.definitions:
                continue
            timer_id = self.definitions[name][0]
            timer_names.setdefault(timer_id, []).append(name)

        duplicates = {
            timer_id: sorted(set(names))
            for timer_id, names in timer_names.items()
            if len(set(names)) > 1
        }
        out_of_range = sorted(
            (timer_id, sorted(set(names)))
            for timer_id, names in timer_names.items()
            if not 1 <= timer_id <= 50
        )
        self.assertEqual(duplicates, {}, f"Timer slots have multiple owners: {duplicates}")
        self.assertEqual(out_of_range, [], f"Timer slots out of native range: {out_of_range}")
        self.assertIn(
            "(defconst byzantine-offensive-objective-timer 8)",
            self.runtime,
        )
        self.assertIn(
            "(defconst byzantine-remote-resource-productivity-timer 22)",
            self.runtime,
        )
        self.assertIn("(defconst bt-offensive-objective-witness-seconds 20)", self.runtime)
        self.assertIn("(defconst bt-resource-productivity-seconds 30)", self.runtime)

    def test_imperial_elite_skirmisher_production_is_upgrade_gated(self) -> None:
        demand_ids = (
            "imperial-elite-skirmisher-floor",
            "imperial-open-elite-skirmisher-standard",
            "imperial-open-elite-skirmisher-pressure",
            "imperial-open-elite-skirmisher-severe",
            "imperial-fortified-elite-skirmisher",
            "imperial-trash-elite-skirmisher-standard",
            "imperial-trash-elite-skirmisher-high",
        )
        for demand_id in demand_ids:
            start = self.runtime.index(f"; Action issuance: {demand_id}")
            end = self.runtime.find("; Pending diagnostics:", start)
            self.assertGreater(end, start, demand_id)
            block = self.runtime[start:end]
            self.assertIn("(up-research-status c: 98 >= 3)", block, demand_id)

    def test_runtime_sync_accepts_action_rule_markers(self) -> None:
        from tools.synchronize_byzantine_runtime import _rule_block

        source = (
            "; Action issuance: test-demand | ACTIVE -> ISSUED\\n"
            "(defrule\\n"
            "    (true)\\n"
            "=>\\n"
            "    (disable-self)\\n"
            ")\\n"
        )
        block = _rule_block(
            source,
            "test-demand",
            marker_prefix="; Action issuance:",
        )
        self.assertIn("(defrule", block)
        self.assertIn("(disable-self)", block)

    def test_endgame_runtime_states_are_compiler_compatible(self) -> None:
        from Compiler.ir.endgame import EndgamePushState

        compiler_states = set(range(len(EndgamePushState)))
        emitted_states = {
            int(match.group(1))
            for match in re.finditer(
                r"\(set-goal byzantine-endgame-push-state (\d+)\)",
                self.runtime,
            )
        }
        self.assertTrue(compiler_states.issuperset(emitted_states))
        self.assertIn(4, compiler_states)
        state_match = re.search(
            r"\(defconst byzantine-endgame-push-state (\d+)\)",
            self.runtime,
        )
        self.assertIsNotNone(state_match)
        assert state_match is not None
        runtime_storage_id = int(state_match.group(1))
        self.assertGreaterEqual(runtime_storage_id, 1)
        self.assertLessEqual(runtime_storage_id, 16_000)

    def test_strategic_number_writer_ownership_is_explicit(self) -> None:
        writers_by_id: dict[int, set[str]] = {}
        for match in SN_WRITE_RE.finditer(self.runtime):
            name = match.group(1)
            if name not in self.definitions:
                continue
            native_id = self.definitions[name][0]
            if name.startswith("sn-") or name.startswith("sn-native-"):
                writers_by_id.setdefault(native_id, set()).add(name)

        expected = {
            4: {"sn-cap-civilian-builders"},
            36: {"sn-native-36", "sn-number-attack-groups"},
            227: {"sn-native-227", "sn-percent-attack-soldiers"},
        }
        observed = {
            native_id: names
            for native_id, names in writers_by_id.items()
            if len(names) > 1 or native_id in expected
        }
        self.assertEqual(
            observed,
            expected,
            "Strategic Number ownership drifted without an explicit arbitration "
            f"contract: observed={observed}",
        )


if __name__ == "__main__":
    unittest.main()
