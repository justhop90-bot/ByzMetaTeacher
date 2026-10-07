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

    def test_synchronization_installs_canonical_water_execution_control(self) -> None:
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
                first_sync = synchronized
                sync_runtime.synchronize()
                second_sync = runtime_path.read_text(encoding="utf-8")
            finally:
                sync_runtime.RUNTIME = original_runtime
                sync_runtime.GENERATED = original_generated

        self.assertEqual(first_sync, second_sync)
        self.assertIn(
            "(defconst water-transport-objective ",
            synchronized,
        )
        self.assertIn(
            "(defconst water-transport-rebuild ",
            synchronized,
        )
        reserved = {
            "water-dock-capability": 15977,
            "construction-retry-barrier-water-dock-capability": 15976,
            "demand-water-dock-capability": 15975,
            "issued-water-dock-capability": 15973,
            "pending-water-dock-capability": 15972,
            "complete-water-dock-capability": 15971,
            "water-transport-objective": 15970,
            "water-transport-rebuild": 15969,
        }
        for name, value in reserved.items():
            self.assertIn(f"(defconst {name} {value})", synchronized)
        self.assertEqual(len(set(reserved.values())), len(reserved))
        self.assertIn(
            "(or (map-type islands) (map-type pacific-islands))",
            synchronized,
        )
        self.assertIn(
            "; Native control rule: transport-objective-open",
            synchronized,
        )
        self.assertIn(
            "; Native control rule: transport-phase-reopen",
            synchronized,
        )
        self.assertIn(
            "; Native control rule: water-posture-naval-defense",
            synchronized,
        )
        self.assertIn(
            "; Native control rule: water-posture-fishing",
            synchronized,
        )
        self.assertNotIn(
            "(defrule\\n    (map-type islands)\\n=>\\n    (set-goal water-posture 4)",
            synchronized,
        )
    def test_goal_slot_allocator_returns_empty_for_zero_requests(self) -> None:
        runtime = sync_runtime.RUNTIME.read_text(encoding="utf-8")
        self.assertEqual(sync_runtime._choose_goal_slots(runtime, 0), [])
    
    def test_synchronization_remaps_voice_storage_away_from_overlay_occupancy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime_path = root / "Byzantine.per"
            generated_path = root / "generated.per"
            base_runtime = sync_runtime.RUNTIME.read_text(encoding="utf-8")
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

    def test_synchronization_installs_first_dock_construction_lifecycle(self) -> None:
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
                before_second_sync = synchronized
                sync_runtime.synchronize()
                after_second_sync = runtime_path.read_text(encoding="utf-8")
            finally:
                sync_runtime.RUNTIME = original_runtime
                sync_runtime.GENERATED = original_generated

        self.assertEqual(before_second_sync, after_second_sync)
        self.assertIn("; Action issuance: water-dock-capability", synchronized)
        self.assertEqual(
            synchronized.count("; Action issuance: water-dock-capability | ACTIVE -> ISSUED"),
            1,
        )
        self.assertIn("(defconst demand-water-dock-capability ", synchronized)
        self.assertIn(
            "(defconst construction-retry-barrier-water-dock-capability ",
            synchronized,
        )
        self.assertIn("(build dock)", synchronized)
        self.assertIn(
            "; Completion witness: water-dock-capability | PENDING/ISSUED -> COMPLETE",
            synchronized,
        )
        self.assertIn(
            "; Release: water-dock-capability | COMPLETE -> RELEASED",
            synchronized,
        )
        self.assertRegex(
            synchronized,
            r"\(set-goal demand-water-dock-capability 1\)",
        )
        self.assertIn(
            "(set-goal construction-retry-barrier-water-dock-capability 0)",
            synchronized,
        )
        definitions = {
            match.group(1): int(match.group(2))
            for match in re.finditer(
                r"\(defconst\s+([^\s()]+)\s+(-?\d+)\)",
                synchronized,
            )
        }
        water_goal_names = (
            "demand-water-dock-capability",
            "issued-water-dock-capability",
            "pending-water-dock-capability",
            "complete-water-dock-capability",
            "construction-retry-barrier-water-dock-capability",
        )
        recovery_goal_names = (
            "opening-recovery",
            "opening-recovery-cause",
            "opening-recovery-defense-clear",
            "opening-recovery-gold-proven",
            "opening-recovery-origin",
            "opening-recovery-water-proven",
        )
        water_ids = {definitions[name] for name in water_goal_names}
        recovery_ids = {definitions[name] for name in recovery_goal_names}
        self.assertEqual(len(water_ids), len(water_goal_names))
        self.assertEqual(water_ids & recovery_ids, set())

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
