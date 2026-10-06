#!/usr/bin/env python3
"""Synchronize compiler-owned opening recovery into the checked-in Byzantine runtime artifact.

The checked-in Byzantine.per is a controlled hybrid: the canonical compiler owns the
strategy core, while the file also contains runtime-only repairs that are not yet
compiler policy. This script ports only the opening-recovery/economy-control slice
from the freshly generated canonical artifact and preserves the runtime overlay.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "Byzantine.per"
GENERATED = ROOT / "dist" / "byzantine" / "Byzantine.per"

RECOVERY_NAMES = (
    "opening-recovery",
    "opening-recovery-cause",
    "opening-recovery-defense-clear",
    "opening-recovery-gold-proven",
    "opening-recovery-origin",
    "opening-recovery-water-proven",
)

ECONOMY_RULES = (
    "economy-controller-select-counter-pressure",
    "economy-controller-select-fast-castle",
    "economy-controller-select-counter-feudal",
    "economy-controller-select-water-economy",
    "economy-controller-select-water-control",
    "economy-controller-select-base",
)


def _rule_block(source: str, identity: str) -> str:
    marker = f"; Native control rule: {identity}"
    start = source.find(marker)
    if start < 0:
        raise RuntimeError(f"generated artifact is missing rule marker: {identity}")
    rule_start = source.find("(defrule", start)
    if rule_start < 0:
        raise RuntimeError(f"generated artifact is missing defrule: {identity}")

    depth = 0
    in_string = False
    escape = False
    for index in range(rule_start, len(source)):
        char = source[index]
        if in_string:
            if escape:
                escape = False
            elif char == chr(92):
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return source[start : index + 1].rstrip() + "\n"
    raise RuntimeError(f"unterminated generated rule: {identity}")


def _block(source: str, start_marker: str, end_marker: str) -> str:
    start = source.find(start_marker)
    if start < 0:
        raise RuntimeError(f"generated artifact is missing start marker: {start_marker}")
    end = source.find(end_marker, start)
    if end < 0:
        raise RuntimeError(f"generated artifact is missing end marker: {end_marker}")
    return source[start:end].rstrip() + "\n"


def _install_once(source: str, marker: str, block: str) -> str:
    if block.strip() in source:
        return source
    position = source.find(marker)
    if position < 0:
        raise RuntimeError(f"runtime artifact is missing insertion marker: {marker}")
    return source[:position] + block + "\n" + source[position:]


def _storage_intervals(source: str) -> list[tuple[int, int, str]]:
    definitions: dict[str, int] = {
        match.group(1): int(match.group(2))
        for match in re.finditer(
            r"\(defconst\\s+([^\\s()]+)\\s+(-?\\d+)\\)",
            source,
        )
    }
    patterns = (
        (re.compile(r"\((?:goal|set-goal|up-compare-goal|up-modify-goal)\\s+([^\\s()]+)"), 1, "GOAL_SLOT"),
        (re.compile(r"\(up-get-point\\s+position-object\\s+([^\\s()]+)"), 2, "POINT_PAIR"),
        (re.compile(r"\(up-get-search-state\\s+([^\\s()]+)"), 4, "SEARCH_STATE"),
    )
    intervals: list[tuple[int, int, str]] = []
    for pattern, width, kind in patterns:
        for match in pattern.finditer(source):
            name = match.group(1)
            if name in definitions and not re.fullmatch(r"-?\d+", name):
                value = definitions[name]
                intervals.append((value, value + width - 1, kind))
    return list(dict.fromkeys(intervals))


def _choose_goal_slots(runtime: str, count: int) -> list[int]:
    recovery_names = set(RECOVERY_NAMES)
    used: set[int] = set()
    for start, end, _kind in _storage_intervals(runtime):
        if any(start <= 16_000 and end >= 1 for _ in (0,)):
            for value in range(max(1, start), min(16_000, end) + 1):
                used.add(value)

    # The recovery slots themselves are relocatable, so remove their current
    # intervals from the exclusion set before selecting replacement slots.
    definitions = {
        match.group(1): int(match.group(2))
        for match in re.finditer(
            r"\(defconst\\s+([^\\s()]+)\\s+(-?\\d+)\\)",
            runtime,
        )
    }
    for name in recovery_names:
        current = definitions.get(name)
        if current is not None and 1 <= current <= 16_000:
            used.discard(current)

    chosen: list[int] = []
    for candidate in range(16_000, 0, -1):
        if candidate in used:
            continue
        chosen.append(candidate)
        if len(chosen) == count:
            return chosen
    raise RuntimeError("no free native Goal slots remain in 1..16000")


def _ensure_defconsts(runtime: str, generated: str) -> str:
    generated_values: dict[str, int] = {}
    for name in RECOVERY_NAMES:
        match = re.search(
            rf"^\(defconst {re.escape(name)} (-?\d+)\)$",
            generated,
            flags=re.MULTILINE,
        )
        if not match:
            raise RuntimeError(f"generated artifact is missing defconst: {name}")
        generated_values[name] = int(match.group(1))

    definitions = {
        match.group(1): int(match.group(2))
        for match in re.finditer(
            r"\(defconst\\s+([^\\s()]+)\\s+(-?\\d+)\\)",
            runtime,
        )
    }
    current = {name: definitions.get(name) for name in RECOVERY_NAMES}
    intervals = _storage_intervals(runtime)

    def valid_current() -> bool:
        if any(value is None or not 1 <= value <= 16_000 for value in current.values()):
            return False
        for name, value in current.items():
            assert value is not None
            for start, end, _kind in intervals:
                if start <= value <= end:
                    other_is_same_slot = (
                        start == value
                        and end == value
                        and name in recovery_names_by_slot
                    )
                    if not other_is_same_slot:
                        return False
        return len(set(current.values())) == len(current)

    recovery_names_by_slot = {
        value: name for name, value in current.items() if value is not None
    }
    if valid_current():
        return runtime

    chosen = _choose_goal_slots(runtime, len(RECOVERY_NAMES))
    replacements = dict(zip(RECOVERY_NAMES, chosen))
    for name, value in replacements.items():
        old_pattern = re.compile(
            rf"^\(defconst {re.escape(name)} -?\d+\)$",
            flags=re.MULTILINE,
        )
        new_line = f"(defconst {name} {value})"
        runtime, replaced = old_pattern.subn(new_line, runtime, count=1)
        if replaced == 0:
            marker = "(defconst opening-plan "
            position = runtime.find(marker)
            if position < 0:
                raise RuntimeError("runtime artifact is missing opening-plan defconst")
            line_end = runtime.find("\n", position)
            runtime = runtime[: line_end + 1] + new_line + "\n" + runtime[line_end + 1 :]
    return runtime


def _replace_rule(runtime: str, generated: str, identity: str) -> str:
    generated_block = _rule_block(generated, identity)
    marker = f"; Native control rule: {identity}"
    start = runtime.find(marker)
    if start < 0:
        raise RuntimeError(f"runtime artifact is missing economy rule: {identity}")
    rule_start = runtime.find("(defrule", start)
    if rule_start < 0:
        raise RuntimeError(f"runtime artifact is missing defrule: {identity}")

    depth = 0
    in_string = False
    escape = False
    for index in range(rule_start, len(runtime)):
        char = runtime[index]
        if in_string:
            if escape:
                escape = False
            elif char == chr(92):
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return runtime[:start] + generated_block + runtime[index + 1 :]
    raise RuntimeError(f"runtime artifact has unterminated rule: {identity}")


def synchronize() -> bool:
    runtime = RUNTIME.read_text(encoding="utf-8")
    generated = GENERATED.read_text(encoding="utf-8")
    before = runtime

    runtime = _add_defconsts(runtime, generated)

    defense_block = _block(
        generated,
        "; Native control rule: opening-recovery-defense-clear-initialize",
        "; Native control rule: opening-selector-water-control",
    )
    recovery_block = _block(
        generated,
        "; Native control rule: opening-recovery-prove-gold",
        "; Native control rule: economy-controller-select-counter-pressure",
    )

    runtime = _install_once(
        runtime,
        "; Native control rule: opening-selector-water-control",
        defense_block,
    )
    runtime = _install_once(
        runtime,
        "; Native economy rule: byzantine-community-economy-initialize",
        recovery_block,
    )

    for identity in ECONOMY_RULES:
        runtime = _replace_rule(runtime, generated, identity)

    if runtime == before:
        return False
    RUNTIME.write_text(runtime, encoding="utf-8", newline="")
    return True


if __name__ == "__main__":
    print("updated" if synchronize() else "already synchronized")
