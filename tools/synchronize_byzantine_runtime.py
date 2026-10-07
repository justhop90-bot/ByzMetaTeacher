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

ELITE_SKIRMISHER_PRODUCTION_RULES = (
    "imperial-elite-skirmisher-floor",
    "imperial-open-elite-skirmisher-standard",
    "imperial-open-elite-skirmisher-pressure",
    "imperial-open-elite-skirmisher-severe",
    "imperial-fortified-elite-skirmisher",
    "imperial-trash-elite-skirmisher-standard",
    "imperial-trash-elite-skirmisher-high",
)

CIVILIAN_VILLAGER_SECTION_START = "; Persistent civilian production"
CIVILIAN_VILLAGER_SECTION_END = "; Pending diagnostics: early-defensive-spears"
WATER_DOCK_DEMAND = "water-dock-capability"
WATER_DOCK_GOAL_NAMES = (
    "demand-water-dock-capability",
    "issued-water-dock-capability",
    "pending-water-dock-capability",
    "complete-water-dock-capability",
    "construction-retry-barrier-water-dock-capability",
)


ECONOMY_RULES = (
    "economy-controller-select-counter-pressure",
    "economy-controller-select-fast-castle",
    "economy-controller-select-counter-feudal",
    "economy-controller-select-water-economy",
    "economy-controller-select-water-control",
    "economy-controller-select-base",
)


def _rule_block(
    source: str,
    identity: str,
    *,
    marker_prefix: str = "; Native control rule:",
) -> str:
    marker = f"{marker_prefix} {identity}"
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


def _sync_civilian_villager_castle_admission(
    runtime: str,
    generated: str,
) -> str:
    demand_marker = "; Action issuance: civilian-villager-continuity"
    demand_start = generated.find(demand_marker)
    if demand_start < 0:
        raise RuntimeError(
            "generated artifact is missing civilian-villager-continuity action issuance"
        )
    demand_end = generated.find("; Pending diagnostics:", demand_start)
    if demand_end < 0:
        raise RuntimeError(
            "generated artifact is missing civilian-villager-continuity pending diagnostics"
        )
    generated_block = generated[demand_start:demand_end]
    if "(can-afford-research castle-age)" not in generated_block:
        raise RuntimeError(
            "generated civilian villager lifecycle is missing Castle affordability admission"
        )
    if "(can-research-with-escrow castle-age)" in generated_block:
        raise RuntimeError(
            "generated civilian villager lifecycle still couples admission to research provider readiness"
        )

    start = runtime.find(CIVILIAN_VILLAGER_SECTION_START)
    if start < 0:
        raise RuntimeError(
            f"runtime artifact is missing section: {CIVILIAN_VILLAGER_SECTION_START}"
        )
    end = runtime.find(CIVILIAN_VILLAGER_SECTION_END, start)
    if end < 0:
        raise RuntimeError(
            f"runtime artifact is missing section end: {CIVILIAN_VILLAGER_SECTION_END}"
        )

    section = runtime[start:end]
    old = "(can-research-with-escrow castle-age)"
    new = "(can-afford-research castle-age)"
    if new in section and old not in section:
        return runtime
    if old not in section:
        raise RuntimeError(
            "runtime civilian villager lifecycle is missing both Castle admission predicates"
        )
    patched_section = section.replace(old, new, 1)
    return runtime[:start] + patched_section + runtime[end:]


def _first_rule_block(source: str, marker: str) -> tuple[int, int, str]:
    start = source.find(marker)
    if start < 0:
        raise RuntimeError(f"source is missing section marker: {marker}")
    rule_start = source.find("(defrule", start)
    if rule_start < 0:
        raise RuntimeError(f"source is missing defrule after marker: {marker}")

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
                return start, index + 1, source[rule_start:index + 1]
    raise RuntimeError(f"source has unterminated defrule after marker: {marker}")


def _demand_lifecycle_block(source: str, identity: str) -> str:
    start_marker = f"; Pending diagnostics: {identity}"
    start = source.find(start_marker)
    if start < 0:
        raise RuntimeError(f"generated artifact is missing demand lifecycle: {identity}")

    candidates = []
    for marker in ("; Invalidation: ", "; Pending diagnostics: "):
        cursor = source.find(marker, start + len(start_marker))
        if cursor >= 0:
            candidates.append(cursor)
    if not candidates:
        raise RuntimeError(f"generated artifact has no following demand boundary: {identity}")
    end = min(candidates)
    return source[start:end].rstrip() + "\n"


def _ensure_water_dock_defconsts(
    runtime: str,
    generated: str,
) -> tuple[str, dict[str, int]]:
    runtime = _ensure_reserved_water_goal_defconsts(runtime)
    return (
        runtime,
        {
            name: WATER_RUNTIME_RESERVED_GOALS[name]
            for name in (
                WATER_DOCK_DEMAND,
                f"construction-retry-barrier-{WATER_DOCK_DEMAND}",
            )
        },
    )

def _sync_first_dock_lifecycle(runtime: str, generated: str) -> str:
    identity = WATER_DOCK_DEMAND
    runtime, dock_constants = _ensure_water_dock_defconsts(runtime, generated)
    action_block = _rule_block(
        generated,
        identity,
        marker_prefix="; Action issuance:",
    )
    lifecycle_block = _demand_lifecycle_block(generated, identity)
    if "(build dock)" not in action_block:
        raise RuntimeError("generated first-dock action is not a dock build")
    if "(building-type-count dock >= 1)" not in lifecycle_block:
        raise RuntimeError("generated first-dock lifecycle is missing its dock witness")

    install_block = lifecycle_block
    if f"; Action issuance: {identity} | ACTIVE -> ISSUED" not in install_block:
        install_block += "\n" + action_block
    start_marker = f"; Pending diagnostics: {identity}"
    end_marker = "; Native Strategos voice plan"
    start = runtime.find(start_marker)
    end = runtime.find(end_marker, start + len(start_marker)) if start >= 0 else -1
    if start >= 0 and end >= 0:
        runtime = runtime[:start] + install_block.rstrip() + "\n\n" + runtime[end:]
    else:
        runtime = _install_once(
            runtime,
            end_marker,
            install_block,
        )

    init_start, init_end, init_rule = _first_rule_block(
        runtime,
        "; Demand initialization",
    )
    init_line = f"    (set-goal demand-{identity} 1)"
    if init_line not in init_rule:
        disable_line = "    (disable-self)"
        if disable_line not in init_rule:
            raise RuntimeError("runtime demand initialization rule is missing disable-self")
        patched_rule = init_rule.replace(
            disable_line,
            init_line + "\n" + disable_line,
            1,
        )
        runtime = runtime[:init_start] + runtime[init_start:init_end].replace(init_rule, patched_rule, 1) + runtime[init_end:]

    retry_reset = (
        "; Native control rule: water-dock-capability-construction-retry-reset\n"
        "(defrule\n"
        "    (true)\n"
        "=>\n"
        "    (set-goal construction-retry-barrier-water-dock-capability 0)\n"
        ")\n"
    )
    runtime = _install_once(
        runtime,
        "; Per-pass production retry barriers",
        retry_reset,
    )
    return runtime


def _replace_tail_section(source: str, marker: str, block: str) -> str:
    position = source.find(marker)
    if position < 0:
        return source.rstrip() + "\n\n" + block.rstrip() + "\n"

    prefix = source[:position].rstrip()
    normalized_block = block.rstrip()
    current_tail = source[position:].rstrip()
    if current_tail == normalized_block:
        return source

    return prefix + "\n\n" + normalized_block + "\n"


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
            r"\(defconst\s+([^\s()]+)\s+(-?\d+)\)",
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


def _choose_voice_goal_slots(runtime: str, count: int) -> list[int]:
    """Choose deterministic Goal ids that are free in the non-voice runtime overlay."""
    occupied = set()
    for start, end, _kind in _storage_intervals(runtime):
        occupied.update(range(max(1, start), min(16_000, end) + 1))

    # Avoid reusing any named constant already present in the hybrid runtime,
    # even if that constant is not currently exercised by a storage operation.
    definitions = {
        match.group(1): int(match.group(2))
        for match in re.finditer(
            r"\(defconst\s+([^\s()]+)\s+(-?\d+)\)",
            runtime,
        )
    }
    occupied.update(value for value in definitions.values() if 1 <= value <= 16_000)

    chosen: list[int] = []
    for candidate in range(16_000, 0, -1):
        if candidate in occupied:
            continue
        chosen.append(candidate)
        if len(chosen) == count:
            return chosen
    raise RuntimeError("no free native Goal slots remain for Strategos voice")


def _timer_ids(source: str) -> set[int]:
    definitions = {
        match.group(1): int(match.group(2))
        for match in re.finditer(
            r"\(defconst\s+([^\s()]+)\s+(-?\d+)\)",
            source,
        )
    }
    used: set[int] = set()
    timer_re = re.compile(
        r"\((?:enable-timer|disable-timer|timer-triggered)\s+([^\s()]+)"
    )
    for match in timer_re.finditer(source):
        name = match.group(1)
        value = definitions.get(name)
        if value is not None and 1 <= value <= 50:
            used.add(value)
    return used


def _choose_voice_timer_slots(runtime: str, count: int) -> list[int]:
    """Choose deterministic Timer ids free in the non-voice runtime overlay."""
    used = _timer_ids(runtime)

    chosen: list[int] = []
    for candidate in range(50, 0, -1):
        if candidate in used:
            continue
        chosen.append(candidate)
        if len(chosen) == count:
            return chosen
    raise RuntimeError("no free native Timer ids remain for Strategos voice")


def _replace_defconst_values(
    source: str,
    replacements: dict[str, int],
) -> str:
    for name, value in replacements.items():
        pattern = re.compile(
            rf"^\(defconst {re.escape(name)} -?\d+\)$",
            flags=re.MULTILINE,
        )
        source, replaced = pattern.subn(
            f"(defconst {name} {value})",
            source,
            count=1,
        )
        if replaced != 1:
            raise RuntimeError(
                f"voice artifact is missing defconst: {name}"
            )
    return source


def _remap_voice_storage(runtime: str, generated_voice: str) -> str:
    """Reconcile generated voice storage with the hybrid runtime overlay."""
    voice_base = runtime.split("; Native Strategos voice plan", 1)[0]

    generated_definitions = {
        match.group(1): int(match.group(2))
        for match in re.finditer(
            r"^\(defconst\s+([^\s()]+)\s+(-?\d+)\)$",
            generated_voice,
            flags=re.MULTILINE,
        )
    }
    goal_names = tuple(
        name
        for name in generated_definitions
        if name == "voice-global-lock"
        or name == "voice-match-count"
        or name.startswith("voice-latch-")
    )
    timer_names = tuple(
        name
        for name in generated_definitions
        if name == "voice-global-cooldown"
        or name.startswith("voice-rearm-")
    )

    goal_values = [generated_definitions[name] for name in goal_names]
    goal_intervals = _storage_intervals(voice_base)
    goal_occupied = {
        value
        for start, end, _kind in goal_intervals
        for value in range(max(1, start), min(16_000, end) + 1)
    }
    goal_occupied.update(
        value
        for name, value in _defconst_values(voice_base).items()
        if 1 <= value <= 16_000
    )
    goals_valid = (
        len(goal_values) == len(set(goal_values))
        and all(1 <= value <= 16_000 and value not in goal_occupied for value in goal_values)
    )

    timer_values = [generated_definitions[name] for name in timer_names]
    timer_occupied = _timer_ids(voice_base)
    timer_occupied.update(
        value
        for name, value in _defconst_values(voice_base).items()
        if 1 <= value <= 50
    )
    timers_valid = (
        len(timer_values) == len(set(timer_values))
        and all(1 <= value <= 50 and value not in timer_occupied for value in timer_values)
    )

    if goals_valid and timers_valid:
        return generated_voice

    goal_replacements = dict(zip(goal_names, _choose_voice_goal_slots(voice_base, len(goal_names))))
    timer_replacements = dict(zip(timer_names, _choose_voice_timer_slots(voice_base, len(timer_names))))
    return _replace_defconst_values(
        _replace_defconst_values(generated_voice, goal_replacements),
        timer_replacements,
    )


def _defconst_values(source: str) -> dict[str, int]:
    return {
        match.group(1): int(match.group(2))
        for match in re.finditer(
            r"\(defconst\s+([^\s()]+)\s+(-?\d+)\)",
            source,
        )
    }


def _choose_goal_slots(
    runtime: str,
    count: int,
    *,
    relocatable_names: tuple[str, ...] = (),
    reserved_source: str = "",
) -> list[int]:
    if count <= 0:
        return []
    relocatable_names_set = set(relocatable_names)
    occupants = _goal_slot_occupants(runtime)
    if reserved_source:
        for value, names in _goal_slot_occupants(reserved_source).items():
            occupants.setdefault(value, set()).update(names)
    used: set[int] = {
        value
        for value, names in occupants.items()
        if not (names & relocatable_names_set)
    }

    chosen: list[int] = []
    for candidate in range(16_000, 0, -1):
        if candidate in used:
            continue
        chosen.append(candidate)
        if len(chosen) == count:
            return chosen
    raise RuntimeError("no free native Goal slots remain in 1..16000")


def _goal_slot_occupants(source: str) -> dict[int, set[str]]:
    """Return Goal-slot users keyed by resolved native Goal id."""
    definitions = _defconst_values(source)
    occupants: dict[int, set[str]] = {}
    pattern = re.compile(
        r"\((?:goal|set-goal|up-compare-goal|up-modify-goal)\s+([^\s()]+)"
    )
    for match in pattern.finditer(source):
        name = match.group(1)
        value = definitions.get(name)
        if value is None or not 1 <= value <= 16_000:
            continue
        occupants.setdefault(value, set()).add(name)
    return occupants


def _ensure_named_defconsts(
    runtime: str,
    generated: str,
    names: tuple[str, ...],
) -> str:
    for name in names:
        match = re.search(
            rf"^\(defconst {re.escape(name)} (-?\d+)\)$",
            generated,
            flags=re.MULTILINE,
        )
        if not match:
            raise RuntimeError(f"generated artifact is missing defconst: {name}")

    definitions = {
        match.group(1): int(match.group(2))
        for match in re.finditer(
            r"\(defconst\s+([^\s()]+)\s+(-?\d+)\)",
            runtime,
        )
    }
    current = {name: definitions.get(name) for name in names}
    occupants = _goal_slot_occupants(runtime)

    def valid_current() -> bool:
        values = [value for value in current.values() if value is not None]
        if len(values) != len(names) or any(not 1 <= value <= 16_000 for value in values):
            return False
        if len(set(values)) != len(values):
            return False
        for name, value in current.items():
            assert value is not None
            other_users = occupants.get(value, set()) - {name}
            if other_users:
                return False
        return True

    if valid_current():
        return runtime

    chosen = _choose_goal_slots(runtime, len(names), reserved_source=generated)
    for name, value in zip(names, chosen):
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
            r"\(defconst\s+([^\s()]+)\s+(-?\d+)\)",
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

    chosen = _choose_goal_slots(
        runtime,
        len(RECOVERY_NAMES),
        relocatable_names=RECOVERY_NAMES,
        reserved_source=generated,
    )
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
    return _ensure_named_defconsts(runtime, generated, RECOVERY_NAMES)


def _ensure_rule_requirement(
    source: str,
    identity: str,
    requirement: str,
    *,
    marker_prefix: str,
) -> str:
    marker = f"{marker_prefix} {identity}"
    start = source.find(marker)
    if start < 0:
        raise RuntimeError(f"runtime artifact is missing rule: {identity}")
    rule_start = source.find("(defrule", start)
    if rule_start < 0:
        raise RuntimeError(f"runtime artifact is missing defrule: {identity}")

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
                block_end = index + 1
                block = source[start:block_end]
                if requirement in block:
                    return source
                anchor = "    (current-age >= imperial-age)\\n"
                if anchor not in block:
                    raise RuntimeError(
                        f"runtime artifact rule lacks Imperial age anchor: {identity}"
                    )
                patched = block.replace(anchor, anchor + f"    {requirement}\\n", 1)
                return source[:start] + patched + source[block_end:]
    raise RuntimeError(f"runtime artifact has unterminated rule: {identity}")


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
                suffix = runtime[index + 1 :].lstrip("\n")
                return (
                    runtime[:start]
                    + generated_block.rstrip()
                    + "\n\n"
                    + suffix
                )
    raise RuntimeError(f"runtime artifact has unterminated rule: {identity}")


WATER_EXECUTION_STATE_NAMES = (
    "transport-phase",
    "water-posture",
    "water-transport-objective",
    "water-transport-rebuild",
)
WATER_EXECUTION_NEW_STATE_NAMES = (
    "water-transport-objective",
    "water-transport-rebuild",
)

WATER_RUNTIME_RESERVED_GOALS = {
    "water-dock-capability": 15994,
    "construction-retry-barrier-water-dock-capability": 15993,
    "demand-water-dock-capability": 15992,
    "issued-water-dock-capability": 15991,
    "pending-water-dock-capability": 15990,
    "complete-water-dock-capability": 15989,
    "water-transport-objective": 15988,
    "water-transport-rebuild": 15987,
}


def _ensure_reserved_water_goal_defconsts(runtime: str) -> str:
    definitions = _defconst_values(runtime)
    occupants = _goal_slot_occupants(runtime)

    for name, value in WATER_RUNTIME_RESERVED_GOALS.items():
        users = occupants.get(value, set()) - {name}
        if users:
            raise RuntimeError(
                f"reserved water Goal slot {value} for '{name}' is occupied by "
                f"{sorted(users)}"
            )

    missing_lines: list[str] = []
    for name, value in WATER_RUNTIME_RESERVED_GOALS.items():
        old_pattern = re.compile(
            rf"^\(defconst {re.escape(name)} -?\d+\)$",
            flags=re.MULTILINE,
        )
        new_line = f"(defconst {name} {value})"
        runtime, replaced = old_pattern.subn(new_line, runtime, count=1)
        if replaced == 0:
            missing_lines.append(new_line)

    if missing_lines:
        marker = "(defconst opening-plan "
        position = runtime.find(marker)
        if position < 0:
            raise RuntimeError("runtime artifact is missing opening-plan defconst")
        line_end = runtime.find("\n", position)
        insertion = "\n" + "\n".join(missing_lines)
        runtime = runtime[: line_end + 1] + insertion + runtime[line_end + 1 :]

    return runtime


def _ensure_water_execution_state_defconsts(
    runtime: str,
) -> str:
    names = WATER_EXECUTION_NEW_STATE_NAMES
    definitions = _defconst_values(runtime)
    values = {name: definitions.get(name) for name in names}
    occupants = _goal_slot_occupants(runtime)

    def valid_current() -> bool:
        resolved = {name: int(value) for name, value in values.items() if value is not None}
        if len(resolved) != len(names):
            return False
        if len(set(resolved.values())) != len(resolved):
            return False
        return all(
            not (occupants.get(value, set()) - {name})
            for name, value in resolved.items()
        )

    if valid_current():
        return runtime

    missing = [name for name in names if values[name] is None]
    chosen = _choose_goal_slots(
        runtime,
        len(missing),
        relocatable_names=tuple(name for name in names if values[name] is not None),
    )
    replacements = dict(zip(missing, chosen))
    for name, value in replacements.items():
        old_pattern = re.compile(
            rf"^\(defconst {re.escape(name)} -?\d+\)$",
            flags=re.MULTILINE,
        )
        new_line = f"(defconst {name} {value})"
        runtime, replaced = old_pattern.subn(new_line, runtime, count=1)
        if replaced:
            continue

        anchor = re.compile(
            r"^\(defconst water-posture -?\d+\)$",
            flags=re.MULTILINE,
        )
        match = anchor.search(runtime)
        if match is None:
            raise RuntimeError("runtime artifact is missing water-posture defconst")
        insert_at = match.end()
        runtime = runtime[:insert_at] + "\n" + new_line + runtime[insert_at:]

    return runtime


def _sync_water_execution_control(runtime: str, generated: str) -> str:
    """Synchronize the canonical water state machine into the checked-in runtime."""

    water_start = "; Native control rule: water-execution-initialize"
    water_end = "; Native control rule: opening-recovery-defense-clear-initialize"

    generated_start = generated.find(water_start)
    generated_end = generated.find(water_end, generated_start)
    runtime_start = runtime.find(water_start)
    runtime_end = runtime.find(water_end, runtime_start)

    if generated_start < 0 or generated_end < 0:
        raise RuntimeError("generated artifact is missing the canonical water control block")
    if runtime_start < 0 or runtime_end < 0:
        raise RuntimeError("runtime artifact is missing the water control insertion boundaries")

    runtime = (
        runtime[:runtime_start]
        + generated[generated_start:generated_end].rstrip()
        + "\n\n"
        + runtime[runtime_end:]
    )
    return _ensure_water_execution_state_defconsts(runtime)

def synchronize() -> bool:
    runtime = RUNTIME.read_text(encoding="utf-8")
    generated = GENERATED.read_text(encoding="utf-8")
    before = runtime

    runtime = _ensure_defconsts(runtime, generated)
    runtime = _sync_water_execution_control(runtime, generated)
    runtime = _sync_civilian_villager_castle_admission(runtime, generated)
    runtime = _ensure_reserved_water_goal_defconsts(runtime)
    runtime = _sync_first_dock_lifecycle(runtime, generated)

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

    for identity in ELITE_SKIRMISHER_PRODUCTION_RULES:
        generated_block = _rule_block(
            generated,
            identity,
            marker_prefix="; Action issuance:",
        )
        if "(up-research-status c: 98 >= 3)" not in generated_block:
            raise RuntimeError(
                f"generated artifact is missing Elite Skirmisher research gate: {identity}"
            )
        runtime = _ensure_rule_requirement(
            runtime,
            identity,
            "(up-research-status c: 98 >= 3)",
            marker_prefix="; Action issuance:",
        )

    for identity in ECONOMY_RULES:
        runtime = _replace_rule(runtime, generated, identity)

    voice_marker = "; Native Strategos voice plan"
    voice_start = generated.find(voice_marker)
    if voice_start < 0:
        raise RuntimeError("generated artifact is missing Native Strategos voice plan")
    generated_voice = generated[voice_start:]
    generated_voice = _remap_voice_storage(runtime, generated_voice)
    runtime = _replace_tail_section(runtime, voice_marker, generated_voice)

    if runtime == before:
        return False
    RUNTIME.write_text(runtime, encoding="utf-8", newline="")
    return True


if __name__ == "__main__":
    print("updated" if synchronize() else "already synchronized")
