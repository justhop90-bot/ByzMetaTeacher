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


ECONOMY_RULES = (
    "economy-controller-select-counter-pressure",
    "economy-controller-select-fast-castle",
    "economy-controller-select-counter-feudal",
    "economy-controller-select-water-economy",
    "economy-controller-select-water-control",
    "economy-controller-select-base",
)

CAMP_DEMANDS = (
    "economy-lumber-camp-floor-1",
    "economy-lumber-camp-floor-2",
    "economy-wood-camp-floor-3",
    "economy-wood-camp-floor-4",
    "economy-wood-camp-floor-5",
    "economy-wood-camp-floor-6",
    "economy-gold-camp-floor-1",
    "economy-gold-camp-floor-2",
    "economy-gold-camp-floor-3",
    "economy-gold-camp-floor-4",
    "economy-gold-camp-floor-5",
    "economy-stone-camp-floor-1",
    "economy-stone-camp-floor-2",
    "economy-stone-camp-floor-3",
    "economy-stone-camp-floor-4",
    "economy-stone-camp-floor-5",
)

CAMP_DUC_IDENTITIES = tuple(
    [
        f"byzantine-camp-placement-{resource}-{floor}-{phase}"
        for resource, maximum in (("wood", 6), ("gold", 5), ("stone", 5))
        for floor in range(1, maximum + 1)
        for phase in ("search", "place")
    ]
    + ["byzantine-camp-placement-wood-1-fallback"]
)

CAMP_RUNTIME_START = "; Pending diagnostics: economy-lumber-camp-floor-1"
CAMP_RUNTIME_END = "; Narrow Dark Age second-mill rule:"


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


def _demand_block(source: str, identity: str) -> str:
    marker = f"; Pending diagnostics: {identity}"
    start = source.find(marker)
    if start < 0:
        raise RuntimeError(f"artifact is missing demand section: {identity}")
    next_marker = source.find("\n; Pending diagnostics:", start + len(marker))
    if next_marker < 0:
        return source[start:].rstrip() + "\n"
    return source[start:next_marker].rstrip() + "\n"


def _resource_camp_block(generated: str) -> str:
    duc_blocks = [
        _rule_block(generated, identity, marker_prefix="; Native DUC rule:")
        for identity in CAMP_DUC_IDENTITIES
    ]
    lifecycle_blocks = [
        _demand_block(generated, identity)
        for identity in CAMP_DEMANDS
    ]
    return (
        ";----------------------------------------------------------------\n"
        "; COMPILER-OWNED AIREF RESOURCE-CAMP LIFECYCLES\n"
        ";----------------------------------------------------------------\n"
        + "\n".join(block.rstrip() for block in duc_blocks)
        + "\n\n"
        + "\n".join(block.rstrip() for block in lifecycle_blocks)
        + "\n"
    )


def _replace_resource_camp_section(runtime: str, generated: str) -> str:
    generated_block = _resource_camp_block(generated).rstrip()
    start = runtime.find(CAMP_RUNTIME_START)
    if start < 0:
        raise RuntimeError(
            f"runtime artifact is missing camp section start: {CAMP_RUNTIME_START}"
        )
    end = runtime.find(CAMP_RUNTIME_END, start)
    if end < 0:
        raise RuntimeError(
            f"runtime artifact is missing camp section end: {CAMP_RUNTIME_END}"
        )
    current = runtime[start:end].rstrip()
    replacement = generated_block
    if current == replacement:
        return runtime
    return runtime[:start] + replacement + "\n" + runtime[end:]


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


def synchronize() -> bool:
    runtime = RUNTIME.read_text(encoding="utf-8")
    generated = GENERATED.read_text(encoding="utf-8")
    before = runtime

    runtime = _ensure_defconsts(runtime, generated)
    runtime = _sync_civilian_villager_castle_admission(runtime, generated)
    runtime = _replace_resource_camp_section(runtime, generated)

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
