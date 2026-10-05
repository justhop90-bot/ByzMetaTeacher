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

    def test_sn4_has_one_semantic_writer(self) -> None:
        writers_by_id: dict[int, set[str]] = {}
        for match in SN_WRITE_RE.finditer(self.runtime):
            name = match.group(1)
            if name not in self.definitions:
                continue
            native_id = self.definitions[name][0]
            if name.startswith("sn-") or name.startswith("sn-native-"):
                writers_by_id.setdefault(native_id, set()).add(name)

        self.assertEqual(
            writers_by_id.get(4, set()),
            {"sn-cap-civilian-builders"},
            "SN4 must be owned by the runtime civilian-builder cap controller; "
            f"observed writers={writers_by_id.get(4, set())}",
        )


if __name__ == "__main__":
    unittest.main()
