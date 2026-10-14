from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

import tools.synchronize_byzantine_runtime as sync_runtime
from LearnerAI.Compiler.tests.test_runtime_semantic_isolation import (
    _storage_intervals,
)


class ByzantineRuntimeVoiceStorageIsolationTests(unittest.TestCase):
    def test_synchronization_remaps_voice_storage_away_from_overlay_occupancy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime_path = root / "Byzantine.per"
            generated_path = root / "generated.per"
            base_runtime = sync_runtime.RUNTIME.read_text(encoding="utf-8")
            base_occupied_goals = sync_runtime._occupied_goal_slots(base_runtime)
            generated = sync_runtime.GENERATED.read_text(encoding="utf-8")
            marker = "; Native Strategos voice plan"
            voice_start = generated.find(marker)
            self.assertGreaterEqual(voice_start, 0)
            stale_runtime = (
                base_runtime.split(marker, 1)[0].rstrip()
                + "\n\n"
                + generated[voice_start:].lstrip()
            )
            runtime_path.write_text(stale_runtime, encoding="utf-8")
            generated_path.write_text(generated, encoding="utf-8")

            original_runtime = sync_runtime.RUNTIME
            original_generated = sync_runtime.GENERATED
            sync_runtime.RUNTIME = runtime_path
            sync_runtime.GENERATED = generated_path
            try:
                sync_runtime.synchronize()
                synchronized = runtime_path.read_text(encoding="utf-8")
                before_second_sync = synchronized
                sync_runtime.synchronize()
                after_second_sync = runtime_path.read_text(encoding="utf-8")
            finally:
                sync_runtime.RUNTIME = original_runtime
                sync_runtime.GENERATED = original_generated

        self.assertEqual(before_second_sync, after_second_sync)

        camp_intervals: list[tuple[str, int, int]] = []
        for resource, floors, building_id in (
            ("wood", range(2, 7), 562),
            ("gold", range(2, 6), 584),
            ("stone", range(2, 6), 584),
        ):
            for floor in floors:
                search_identity = f"byzantine-resource-camp-search-{resource}-{floor}"
                place_identity = f"byzantine-resource-camp-place-{resource}-{floor}"
                search_block = sync_runtime._rule_block(
                    synchronized, search_identity, marker_prefix="; Native DUC rule:"
                )
                place_block = sync_runtime._rule_block(
                    synchronized, place_identity, marker_prefix="; Native DUC rule:"
                )
                search_match = re.search(r"\(up-get-search-state\s+(\d+)\)", search_block)
                count_match = re.search(r"\(up-compare-goal\s+(\d+)\s*>\s*(\d+)\)", place_block)
                point_match = re.search(r"\(up-get-point\s+position-object\s+(\d+)\)", place_block)
                target_point_match = re.search(r"\(up-set-target-point\s+(\d+)\)", place_block)
                target_index_match = re.search(r"\(up-set-target-object\s+search-remote\s+c:\s*(\d+)\)", place_block)
                build_match = re.search(r"\(up-build\s+place-point\s+0\s+c:\s*(\d+)\)", place_block)
                self.assertIsNotNone(search_match, search_identity)
                self.assertIsNotNone(count_match, place_identity)
                self.assertIsNotNone(point_match, place_identity)
                self.assertIsNotNone(target_point_match, place_identity)
                self.assertIsNotNone(target_index_match, place_identity)
                self.assertIsNotNone(build_match, place_identity)
                search_base = int(search_match.group(1))
                point_base = int(point_match.group(1))
                self.assertEqual(int(count_match.group(1)), search_base + 3, place_identity)
                self.assertEqual(int(count_match.group(2)), floor - 2, place_identity)
                self.assertEqual(int(target_index_match.group(1)), floor - 2, place_identity)
                self.assertEqual(int(target_point_match.group(1)), point_base, place_identity)
                self.assertEqual(int(build_match.group(1)), building_id, place_identity)
                self.assertIn("(up-filter-status c: 3 c: 0)", search_block, search_identity)
                camp_intervals.extend((
                    (search_identity, search_base, search_base + 3),
                    (place_identity, point_base, point_base + 1),
                ))

        for index, (first_name, first_start, first_end) in enumerate(camp_intervals):
            self.assertTrue(
                set(range(first_start, first_end + 1)).isdisjoint(base_occupied_goals),
                f"{first_name} overlaps pre-existing Goal storage",
            )
            for second_name, second_start, second_end in camp_intervals[index + 1:]:
                self.assertTrue(
                    first_end < second_start or second_end < first_start,
                    f"resource-camp Goal spans overlap: {first_name} and {second_name}",
                )

        base_source = synchronized.split("; Native Strategos voice plan", 1)[0]
        base_goal_ids = {
            value
            for interval in _storage_intervals(base_source)
            for value in range(interval["start"], interval["end"] + 1)
        }
        base_timer_ids = sync_runtime._timer_ids(base_source)

        intervals = _storage_intervals(synchronized)
        collisions = []
        ordered = sorted(
            intervals,
            key=lambda item: (item["start"], item["end"], item["name"]),
        )
        for index, first in enumerate(ordered):
            for second in ordered[index + 1 :]:
                if second["start"] > first["end"]:
                    break
                if first["name"] == second["name"]:
                    continue
                collisions.append((first, second))

        self.assertEqual(collisions, [])

        definitions = {
            match.group(1): int(match.group(2))
            for match in re.finditer(
                r"\(defconst\s+([^\s()]+)\s+(-?\d+)\)",
                synchronized,
            )
        }
        voice_goals = {
            name: definitions[name]
            for name in definitions
            if name == "voice-global-lock"
            or name == "voice-match-count"
            or name.startswith("voice-latch-")
        }
        self.assertEqual(len(voice_goals), 16)
        self.assertEqual(len(set(voice_goals.values())), 16)
        self.assertTrue(
            all(1 <= value <= 16_000 and value not in base_goal_ids for value in voice_goals.values())
        )

        voice_timers = {
            name: definitions[name]
            for name in definitions
            if name == "voice-global-cooldown"
            or name.startswith("voice-rearm-")
        }
        self.assertEqual(len(voice_timers), 15)
        self.assertEqual(len(set(voice_timers.values())), 15)
        self.assertTrue(
            all(1 <= value <= 50 and value not in base_timer_ids for value in voice_timers.values())
        )


    def test_synchronization_replaces_civilian_villager_castle_admission_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime_path = root / "Byzantine.per"
            generated_path = root / "generated.per"
            runtime_path.write_text(
                sync_runtime.RUNTIME.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            generated_path.write_text(
                sync_runtime.GENERATED.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            original_runtime = sync_runtime.RUNTIME
            original_generated = sync_runtime.GENERATED
            sync_runtime.RUNTIME = runtime_path
            sync_runtime.GENERATED = generated_path
            try:
                sync_runtime.synchronize()
                synchronized = runtime_path.read_text(encoding="utf-8")
            finally:
                sync_runtime.RUNTIME = original_runtime
                sync_runtime.GENERATED = original_generated

        start = synchronized.index("; Persistent civilian production")
        end = synchronized.index("; Pending diagnostics: early-defensive-spears", start)
        section = synchronized[start:end]
        self.assertIn("(can-afford-research castle-age)", section)
        self.assertNotIn("(can-research-with-escrow castle-age)", section)

    def test_checked_in_runtime_voice_storage_is_disjoint(self) -> None:
        source = sync_runtime.RUNTIME.read_text(encoding="utf-8")
        definitions = {
            match.group(1): int(match.group(2))
            for match in re.finditer(
                r"\(defconst\s+([^\s()]+)\s+(-?\d+)\)",
                source,
            )
        }
        marker = "; Native Strategos voice plan"
        base = source.split(marker, 1)[0]
        live_goals = {
            value
            for match in re.finditer(
                r"\((?:goal|set-goal|up-compare-goal|up-modify-goal)\s+([^\s()]+)",
                base,
            )
            if (value := definitions.get(match.group(1))) is not None
        }
        live_timers = sync_runtime._timer_ids(base)
        voice_goals = [
            int(match.group(1))
            for match in re.finditer(
                r"^\(defconst\s+(?:voice-global-lock|voice-match-count|voice-latch-[^\s()]+)\s+(-?\d+)\)$",
                source,
                flags=re.MULTILINE,
            )
        ]
        voice_timers = [
            int(match.group(1))
            for match in re.finditer(
                r"^\(defconst\s+(?:voice-global-cooldown|voice-rearm-[^\s()]+)\s+(-?\d+)\)$",
                source,
                flags=re.MULTILINE,
            )
        ]
        self.assertEqual(len(voice_goals), 16)
        self.assertEqual(len(set(voice_goals)), 16)
        self.assertTrue(all(1 <= value <= 16_000 and value not in live_goals for value in voice_goals))
        self.assertEqual(len(voice_timers), 15)
        self.assertEqual(len(set(voice_timers)), 15)
        self.assertTrue(all(1 <= value <= 50 and value not in live_timers for value in voice_timers))


    def test_voice_timer_allocator_ignores_non_timer_defconst_values(self) -> None:
        runtime = """
(defconst chemistry 47)
(defconst bombard-cannon 36)
(defconst bt-offensive-objective-radius 40)
(defconst byzantine-static-defense-score-timer 15)
(defconst byzantine-relic-control-timer 12)
(enable-timer byzantine-static-defense-score-timer)
(enable-timer byzantine-relic-control-timer)
""".strip() + "\n"
        self.assertEqual(
            sync_runtime._choose_voice_timer_slots(runtime, 15),
            list(range(50, 35, -1)),
        )


if __name__ == "__main__":
    unittest.main()
