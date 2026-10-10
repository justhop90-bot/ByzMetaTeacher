#!/usr/bin/env python3
"""Synchronize compiler-owned strategy slices into the checked-in Byzantine runtime artifact.

The checked-in Byzantine.per is a controlled hybrid: the canonical compiler owns the
strategy core, while the file also contains runtime-only repairs that are not yet
compiler policy. This script ports selected canonical sections and resource-camp DUC
execution from the freshly generated artifact while preserving the runtime overlay.
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
        (re.compile(r"\((?:goal|set-goal|up-compare-goal|up-modify-goal)\s+([^\s()]+)"), 1, "GOAL_SLOT"),
        (re.compile(r"\(up-get-point\s+position-object\s+([^\s()]+)"), 2, "POINT_PAIR"),
        (re.compile(r"\(up-set-target-point\s+([^\s()]+)"), 2, "POINT_PAIR"),
        (re.compile(r"\(up-get-search-state\s+([^\s()]+)"), 4, "SEARCH_STATE"),
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
            r"\(defconst\s+([^\s()]+)\s+(-?\d+)\)",
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


def _resource_camp_rule_identities() -> tuple[tuple[str, str, int, int], ...]:
    identities: list[tuple[str, str, int, int]] = []
    for resource, floors, building_id in (
        ("wood", range(2, 7), 562),
        ("gold", range(2, 6), 584),
        ("stone", range(2, 6), 584),
    ):
        for floor in floors:
            identities.append((
                resource,
                f"byzantine-resource-camp-search-{resource}-{floor}",
                floor,
                building_id,
            ))
            identities.append((
                resource,
                f"byzantine-resource-camp-place-{resource}-{floor}",
                floor,
                building_id,
            ))
    return tuple(identities)


def _occupied_goal_slots(source: str) -> set[int]:
    """Conservatively find Goal ids that a remapped DUC span must not reuse."""
    occupied = {
        int(match.group(1))
        for match in re.finditer(r"(?<![A-Za-z0-9_-])(-?\d+)", source)
        if 1 <= int(match.group(1)) <= 16_000
    }
    definitions = {
        match.group(1): int(match.group(2))
        for match in re.finditer(
            r"\(defconst\s+([^\s()]+)\s+(-?\d+)\)",
            source,
        )
    }
    occupied.update(value for value in definitions.values() if 1 <= value <= 16_000)
    for start, end, _kind in _storage_intervals(source):
        occupied.update(range(max(1, start), min(16_000, end) + 1))
    for pattern, width in (
        (r"\(up-get-search-state\s+(-?\d+)\)", 4),
        (r"\(up-get-point\s+position-object\s+(-?\d+)\)", 2),
        (r"\(up-set-target-point\s+(-?\d+)\)", 2),
    ):
        for match in re.finditer(pattern, source):
            start = int(match.group(1))
            occupied.update(range(max(1, start), min(16_000, start + width - 1) + 1))
    return occupied


def _allocate_goal_span(occupied: set[int], width: int) -> int:
    if width < 1:
        raise ValueError("Goal span width must be positive")
    for start in range(16_000 - width + 1, 0, -1):
        slots = set(range(start, start + width))
        if slots.isdisjoint(occupied):
            occupied.update(slots)
            return start
    raise RuntimeError(f"no free native Goal span remains for width {width}")


def _remove_marked_rule(source: str, identity: str) -> str:
    marker = f"; Native DUC rule: {identity}"
    start = source.find(marker)
    if start < 0:
        return source
    rule_start = source.find("(defrule", start)
    if rule_start < 0:
        raise RuntimeError(f"runtime has DUC marker without defrule: {identity}")
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
                return re.sub(r"\n{3,}", "\n\n", source[:start] + source[index + 1:])
    raise RuntimeError(f"runtime has unterminated DUC rule: {identity}")


def _rewrite_once(source: str, pattern: str, replacement: str, identity: str) -> str:
    updated, count = re.subn(pattern, replacement, source, count=1)
    if count != 1:
        raise RuntimeError(f"cannot safely remap resource-camp DUC operand for {identity}")
    return updated


def _sync_resource_camp_duc_rules(runtime: str, generated: str) -> str:
    """Install resource-front DUC rules with Goal spans remapped around the runtime overlay."""
    entries = _resource_camp_rule_identities()
    for _resource, identity, _floor, _building_id in entries:
        runtime = _remove_marked_rule(runtime, identity)

    occupied = _occupied_goal_slots(runtime)
    remapped_blocks: list[str] = []
    by_resource_floor = sorted(
        {(resource, floor, building_id) for resource, _identity, floor, building_id in entries},
        key=lambda item: ({"wood": 0, "gold": 1, "stone": 2}[item[0]], item[1]),
    )
    for resource, floor, building_id in by_resource_floor:
        search_identity = f"byzantine-resource-camp-search-{resource}-{floor}"
        place_identity = f"byzantine-resource-camp-place-{resource}-{floor}"
        search_block = _rule_block(generated, search_identity, marker_prefix="; Native DUC rule:")
        place_block = _rule_block(generated, place_identity, marker_prefix="; Native DUC rule:")

        search_match = re.search(r"\(up-get-search-state\s+(-?\d+)\)", search_block)
        count_match = re.search(r"\(up-compare-goal\s+(-?\d+)\s*>\s*(-?\d+)\)", place_block)
        point_match = re.search(r"\(up-get-point\s+position-object\s+(-?\d+)\)", place_block)
        target_point_match = re.search(r"\(up-set-target-point\s+(-?\d+)\)", place_block)
        target_index_match = re.search(r"\(up-set-target-object\s+search-remote\s+c:\s*(-?\d+)\)", place_block)
        build_match = re.search(r"\(up-build\s+place-point\s+0\s+c:\s*(\d+)\)", place_block)
        if not all((search_match, count_match, point_match, target_point_match, target_index_match, build_match)):
            raise RuntimeError(f"generated resource-camp DUC rule pair is incomplete: {resource} floor {floor}")

        search_base = int(search_match.group(1))
        if int(count_match.group(1)) != search_base + 3:
            raise RuntimeError(
                f"generated resource-camp search-state/count contract is inconsistent: "
                f"{resource} floor {floor}"
            )
        expected_index = floor - 2
        if int(count_match.group(2)) != expected_index or int(target_index_match.group(1)) != expected_index:
            raise RuntimeError(
                f"generated resource-camp selector is not zero-based for {resource} floor {floor}"
            )
        if int(build_match.group(1)) != building_id:
            raise RuntimeError(
                f"generated resource-camp building id is incorrect for {resource} floor {floor}"
            )
        point_base = int(point_match.group(1))
        if int(target_point_match.group(1)) != point_base:
            raise RuntimeError(
                f"generated resource-camp point writer/reader mismatch for {resource} floor {floor}"
            )

        new_search_base = _allocate_goal_span(occupied, 4)
        new_point_base = _allocate_goal_span(occupied, 2)
        search_block = _rewrite_once(
            search_block,
            r"\(up-get-search-state\s+-?\d+\)",
            f"(up-get-search-state {new_search_base})",
            search_identity,
        )
        place_block = _rewrite_once(
            place_block,
            r"\(up-compare-goal\s+-?\d+(\s*>\s*-?\d+\))",
            f"(up-compare-goal {new_search_base + 3}" + r"\1",
            place_identity,
        )
        place_block = _rewrite_once(
            place_block,
            r"\(up-get-point\s+position-object\s+-?\d+\)",
            f"(up-get-point position-object {new_point_base})",
            place_identity,
        )
        place_block = _rewrite_once(
            place_block,
            r"\(up-set-target-point\s+-?\d+\)",
            f"(up-set-target-point {new_point_base})",
            place_identity,
        )
        remapped_blocks.extend((search_block.rstrip(), place_block.rstrip()))

    marker = "; Native attack lifecycle plan"
    insertion = runtime.find(marker)
    if insertion < 0:
        raise RuntimeError("runtime artifact is missing Native attack lifecycle insertion marker")
    camp_section = "\n\n".join(remapped_blocks) + "\n\n"
    return runtime[:insertion].rstrip() + "\n\n" + camp_section + runtime[insertion:]


def synchronize() -> bool:
    runtime = RUNTIME.read_text(encoding="utf-8")
    generated = GENERATED.read_text(encoding="utf-8")
    before = runtime

    runtime = _ensure_defconsts(runtime, generated)
    runtime = _sync_civilian_villager_castle_admission(runtime, generated)

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

    runtime = _sync_resource_camp_duc_rules(runtime, generated)

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
