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

        intervals = _storage_intervals(synchronized)
        collisions = []
        ordered = sorted(intervals, key=lambda item: (item[0], item[1], item[2]))
        for index, first in enumerate(ordered):
            for second in ordered[index + 1 :]:
                if second[0] > first[1]:
                    break
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
        self.assertTrue(all(value > 512 for value in voice_goals.values()))

        voice_timers = {
            name: definitions[name]
            for name in definitions
            if name == "voice-global-cooldown"
            or name.startswith("voice-rearm-")
        }
        self.assertEqual(len(voice_timers), 15)
        self.assertTrue(all(value > 22 for value in voice_timers.values()))


if __name__ == "__main__":
    unittest.main()
