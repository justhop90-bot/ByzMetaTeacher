import re
import shutil
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PER_PATH = REPO_ROOT / "Byzantine.per"


class ByzantineDefensiveGeometryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.per = PER_PATH.read_text(encoding="utf-8")

    def test_parse_repository_replay_for_analysis(self):
        import json
        import os
        import subprocess
        import sys

        replay = REPO_ROOT / "rec.aoe2record"
        out_dir = Path("/tmp/native-reports")
        out_dir.mkdir(parents=True, exist_ok=True)
        analysis_path = out_dir / "replay-mgz-fast-analysis.json"
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "mgz-fast==1.0.0"],
            check=True,
        )

        def scrub(value, depth=0):
            if depth > 5:
                return repr(value)
            if value is None or isinstance(value, (str, int, float, bool)):
                return value
            if isinstance(value, dict):
                return {str(k): scrub(v, depth + 1) for k, v in value.items()}
            if isinstance(value, (list, tuple)):
                return [scrub(v, depth + 1) for v in value]
            if hasattr(value, "name"):
                return getattr(value, "name")
            return repr(value)

        import mgz.fast.header as header_mod
        from mgz.fast import meta, operation
        from mgz.fast.enums import Operation

        with replay.open("rb") as handle:
            eof = os.fstat(handle.fileno()).st_size
            header = header_mod.parse(handle)
            meta(handle)
            elapsed_ms = 0
            operation_counts = {}
            action_counts = {}
            selected_events = []
            postgame = []
            chat = []

            while handle.tell() < eof:
                try:
                    op_type, payload = operation(handle)
                except EOFError:
                    break

                op_name = getattr(op_type, "name", str(op_type))
                operation_counts[op_name] = operation_counts.get(op_name, 0) + 1

                if op_type == Operation.SYNC:
                    increment, checksum, data = payload
                    elapsed_ms += int(increment)
                    continue

                if op_name == "POSTGAME":
                    postgame.append({"time_s": round(elapsed_ms / 1000.0, 3), "data": scrub(payload)})
                    continue

                if op_type == Operation.CHAT:
                    chat.append({
                        "time_s": elapsed_ms / 1000.0,
                        "text": (
                            payload.decode("utf-8", errors="replace")
                            if isinstance(payload, bytes)
                            else scrub(payload)
                        ),
                    })
                    continue

                if op_type == Operation.ACTION:
                    action_type, action_data = payload
                    action_name = getattr(action_type, "name", str(action_type))
                    action_counts[action_name] = action_counts.get(action_name, 0) + 1
                    data = scrub(action_data)
                    selected_events.append({
                        "time_s": round(elapsed_ms / 1000.0, 3),
                        "action": action_name,
                        "data": data,
                    })

        report = {
            "file": {
                "size_bytes": replay.stat().st_size,
            },
            "header": scrub(header),
            "duration_seconds_from_sync": elapsed_ms / 1000.0,
            "operation_counts": operation_counts,
            "action_counts": action_counts,
            "chat": chat,
            "postgame": postgame,
            "events": selected_events,
        }
        analysis_path.write_text(
            json.dumps(report, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )

    def test_cross_parse_replay_with_rust_and_agealyser(self):
        import json
        import subprocess
        import sys

        replay = REPO_ROOT / "rec.aoe2record"
        out_dir = Path("/tmp/native-reports")
        out_dir.mkdir(parents=True, exist_ok=True)
        report = {
            "replay_size_bytes": replay.stat().st_size,
            "parsers": {},
        }

        def run_python(code, packages):
            install = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", *packages],
                capture_output=True,
                text=True,
            )
            if install.returncode != 0:
                return {
                    "status": "install_error",
                    "returncode": install.returncode,
                    "stdout": install.stdout[-4000:],
                    "stderr": install.stderr[-4000:],
                }
            result = subprocess.run(
                [sys.executable, "-c", code, str(replay)],
                capture_output=True,
                text=True,
            )
            return {
                "status": "success" if result.returncode == 0 else "runtime_error",
                "returncode": result.returncode,
                "stdout": result.stdout[-20000:],
                "stderr": result.stderr[-20000:],
            }

        report["parsers"]["aoe2rec_py"] = run_python(
            '''
import json
import sys
from pathlib import Path
import aoe2rec_py
p = Path(sys.argv[1])
data = aoe2rec_py.parse_rec(p.read_bytes())
Path("/tmp/native-reports/aoe2rec-py.json").write_text(
    json.dumps(data, indent=2, default=str),
    encoding="utf-8",
)
print(json.dumps({"top_keys": sorted(data.keys()) if isinstance(data, dict) else repr(data)}))
''',
            ["aoe2rec-py==0.1.22"],
        )

        report["parsers"]["age_alyser"] = run_python(
            '''
import json
import sys
from pathlib import Path
from agealyser import AgeGame
stats = AgeGame(sys.argv[1]).advanced_parser(include_map_analysis=False)
if hasattr(stats, "to_dict"):
    stats = stats.to_dict()
Path("/tmp/native-reports/age-alyser.json").write_text(
    json.dumps(stats, indent=2, default=str),
    encoding="utf-8",
)
print(json.dumps({"keys": sorted(stats.keys()) if isinstance(stats, dict) else repr(stats)}))
''',
            ["age-alyser==0.0.5"],
        )

        report["parsers"]["mgz_model"] = run_python(
            '''
import json
import sys
from pathlib import Path
from mgz.model import parse_match, serialize
with open(sys.argv[1], "rb") as handle:
    match = parse_match(handle)
data = serialize(match)
Path("/tmp/native-reports/mgz-model.json").write_text(
    json.dumps(data, indent=2, default=str),
    encoding="utf-8",
)
print(json.dumps({"top_keys": sorted(data.keys()) if isinstance(data, dict) else repr(data)}))
''',
            ["mgz==1.8.51"],
        )

        (out_dir / "replay-cross-parser.json").write_text(
            json.dumps(report, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )

    def test_export_repository_replay_for_analysis(self):
        replay = REPO_ROOT / "rec.aoe2record"
        evidence_dir = Path("/tmp/native-reports")
        evidence_dir.mkdir(parents=True, exist_ok=True)
        exported = evidence_dir / "rec.aoe2record"
        self.assertTrue(replay.is_file(), f"missing replay: {replay}")
        shutil.copyfile(replay, exported)
        self.assertEqual(exported.stat().st_size, replay.stat().st_size)
        self.assertGreater(exported.stat().st_size, 0)

    def test_tower_geometry_prefers_elevation_and_point_placement(self):
        self.assertIn(
            "(set-strategic-number sn-ignore-tower-elevation 0)",
            self.per,
        )
        self.assertIn("(defconst byzantine-defensive-build-point 710)", self.per)
        self.assertIn("(up-build place-point 0 c: watch-tower)", self.per)
        self.assertIn("(up-build place-point 0 c: keep)", self.per)
        self.assertIn("(up-build place-point 0 c: bombard-tower)", self.per)

    def test_static_defense_has_a_single_stone_spend_channel(self):
        self.assertIn(
            "(defconst byzantine-bombard-tower-target 713)",
            self.per,
        )
        self.assertIn(
            "(set-goal byzantine-bombard-tower-target byzantine-bombard-tower-target-two)",
            self.per,
        )
        self.assertIn(
            "(stone-amount > bt-byzantine-bombard-stone-surplus)",
            self.per,
        )
        self.assertIn(
            "(gold-amount > bt-byzantine-bombard-gold-surplus)",
            self.per,
        )

    def test_bombard_tower_does_not_compete_with_first_castle(self):
        self.assertIn("(building-type-count-total castle >= 1)", self.per)
        self.assertIn("(stone-amount >= bt-byzantine-static-stone-reserve)", self.per)
        self.assertIn("(gold-amount >= bt-byzantine-bombard-gold-reserve)", self.per)

    def test_extreme_surplus_adds_a_final_production_capacity_tier(self):
        # Final throughput tier directly addresses the observed all-resource
        # late-game bank instead of adding more passive static defense.
        self.assertIn(
            "(set-goal byzantine-production-barracks-target 6)",
            self.per,
        )
        self.assertIn(
            "(set-goal byzantine-production-archery-target 5)",
            self.per,
        )
        self.assertIn(
            "(set-goal byzantine-production-stable-target 5)",
            self.per,
        )
        self.assertIn(
            "(set-goal byzantine-production-siege-target 5)",
            self.per,
        )
        self.assertIn(
            "(goal byzantine-production-barracks-target 6)",
            self.per,
        )
        self.assertIn(
            "(goal byzantine-production-archery-target 5)",
            self.per,
        )
        self.assertIn(
            "(goal byzantine-production-stable-target 5)",
            self.per,
        )
        self.assertIn(
            "(goal byzantine-production-siege-target 5)",
            self.per,
        )

    def test_keep_respects_castle_stone_commitment_and_uses_frontier_fallback(self):
        self.assertIn(
            "(not (goal byzantine-production-castle-target 2))",
            self.per,
        )
        self.assertIn(
            "(not (goal byzantine-production-castle-target 3))",
            self.per,
        )
        self.assertIn("(build-forward keep)", self.per)

    def test_bombard_tower_has_a_wall_frontier_fallback(self):
        self.assertIn("(build-forward bombard-tower)", self.per)

    def test_native_choke_scorer_ranks_resource_and_fortified_candidates(self):
        self.assertIn(
            "(defconst byzantine-static-defense-score-state 714)",
            self.per,
        )
        self.assertIn(
            "(defconst byzantine-static-defense-resource-score 716)",
            self.per,
        )
        self.assertIn(
            "(defconst byzantine-static-defense-fortified-score 717)",
            self.per,
        )
        self.assertIn(
            "(defconst byzantine-static-defense-placement-kind 718)",
            self.per,
        )
        self.assertIn(
            "(defconst byzantine-static-defense-score-timer 15)",
            self.per,
        )
        self.assertIn(
            "(up-compare-goal byzantine-static-defense-resource-score g:>=",
            self.per,
        )
        self.assertIn(
            "(set-goal byzantine-static-defense-placement-kind byzantine-static-defense-placement-resource)",
            self.per,
        )
        self.assertIn(
            "(set-goal byzantine-static-defense-placement-kind byzantine-static-defense-placement-fortified)",
            self.per,
        )
        self.assertIn(
            "(goal byzantine-wall-geometry-state byzantine-wall-geometry-armed)",
            self.per,
        )
        self.assertIn(
            "(up-compare-goal byzantine-static-defense-resource-score g:>= byzantine-static-defense-fortified-score)",
            self.per,
        )

    def test_goal_comparisons_use_up_compare_goal(self):
        # `goal` is exact equality only. Comparator forms belong to
        # `up-compare-goal`; letting `(goal G > 0)` through produces a native
        # parser failure that can misleadingly surface on the operator line.
        invalid = re.findall(
            r"\\(goal\\s+[^\\s()]+\\s+(?:==|!=|<=|>=|<|>)\\s+[^()]+\\)",
            self.per,
        )
        self.assertEqual(
            invalid,
            [],
            f"goal comparator facts must use up-compare-goal: {invalid}",
        )

    def test_keep_and_bombard_build_only_through_scored_geometry(self):
        self.assertIn(
            "(goal byzantine-static-defense-score-state byzantine-static-defense-score-resource-selected)",
            self.per,
        )
        self.assertIn(
            "(goal byzantine-static-defense-score-state byzantine-static-defense-score-fortified-selected)",
            self.per,
        )
        self.assertNotIn("(build 235)", self.per)
        self.assertNotIn("(build 236)", self.per)

    def test_greek_fire_land_trigger_requires_actual_artillery(self):
        marker = "(set-goal demand-water-greek-fire 1)"
        start = self.per.index(marker) - 2200
        trigger = self.per[start : start + 2500]
        self.assertTrue(
            "(building-type-count-total bombard-tower >= 1)" in trigger
            or "(building-type-count-total bombard-cannon >= 1)" in trigger,
            "Greek Fire must be tied to an actual artillery witness on land",
        )


if __name__ == "__main__":
    unittest.main()
