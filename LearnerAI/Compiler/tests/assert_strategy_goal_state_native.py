#!/usr/bin/env python3
"""Native acceptance gate for strategy-owned goal-state assertions.

Builds the Byzantine castle strategy with one goal-backed FSM assertion
(war-posture 0 -> 1) and requires deterministic lowering plus parser
zero-findings. Same-pass write visibility stays engine-ordered and
outside this gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import replace
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_castle_strategy,
    compile_strategy_profile,
)
from Compiler.ir.civ_profile import resolve_effective_civ
from Compiler.ir.strategy import GoalStateAssertion


def _profile():
    effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
    profile = build_byzantine_castle_strategy(effective)
    spec = profile.demands[0]
    assertion = GoalStateAssertion(
        spec.identity, "war-posture", "(goal war-posture 0)", 1
    )
    demands = tuple(
        replace(item, goal_assertions=item.goal_assertions + (assertion,))
        if item.identity == spec.identity
        else item
        for item in profile.demands
    )
    return effective, replace(profile, demands=demands)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    effective, profile = _profile()
    first = compile_strategy_profile(profile, effective)
    _, repeat = _profile()
    second = compile_strategy_profile(repeat, effective)

    if first != second:
        raise SystemExit(
            "goal-state fixture produced non-deterministic artifacts"
        )

    required_fragments = (
        "(goal war-posture 0)",
        "(set-goal war-posture 1)",
        "; Native control rule: war-posture-assert-000",
    )
    missing = [fragment for fragment in required_fragments if fragment not in first]
    if missing:
        raise SystemExit(
            "goal-state fixture is missing expected native output: "
            + ", ".join(missing)
        )
    if "(defconst war-posture " not in first:
        raise SystemExit("goal-state fixture is missing the state defconst")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(first, encoding="utf-8")

    native_report = args.report.with_name(args.report.stem + "-native.json")
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("assert_native_zero.py")),
            str(args.output),
            "--report",
            str(native_report),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    report = {
        "artifact_sha256": hashlib.sha256(first.encode("utf-8")).hexdigest(),
        "required_fragments": required_fragments,
        "native_gate_returncode": result.returncode,
        "native_report": str(native_report),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "runtime_visibility_status": "OPEN",
        "runtime_visibility_reason": (
            "Same-pass guard/set visibility is engine-ordered; the gate "
            "proves deterministic lowering and parser acceptance only."
        ),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)

    if result.returncode != 0:
        return result.returncode or 1

    print(
        "goal-state native artifact gate passed "
        f"(sha256={report['artifact_sha256']}; runtime=OPEN)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
