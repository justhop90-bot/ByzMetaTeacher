#!/usr/bin/env python3
"""Native acceptance gate for DUC group-creation window inputs.

Vertical: MEASURE (find + target + create group 0 + read group size and
native id into allocated GoalSlots) -> WINDOW (create group 1 with the
stored start/size goals) -> MICRO (set-group reload + retarget + consume).
Group membership and flag runtime values remain OPEN.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.ast import Expression
from Compiler.compiler import compile_source
from Compiler.ir.model import (
    GoalRole,
    GoalSlotRequest,
    SemanticId,
    StorageRequestId,
)
from Compiler.ir.native_duc import (
    NativeDucGoalInputRequest,
    NativeDucOutputRequest,
    NativeDucPlan,
    NativeDucRule,
)


def _e(source, head, *args):
    return Expression(source=source, head=head, args=args)


def _vertical():
    measure_slot = GoalSlotRequest(
        StorageRequestId(SemanticId("test", "window"), "up-get-group-size"),
        role=GoalRole.NATIVE_OUTPUT,
    )
    identity_slot = GoalSlotRequest(
        StorageRequestId(SemanticId("test", "window"), "up-get-object-data"),
        role=GoalRole.NATIVE_OUTPUT,
    )
    measure = NativeDucOutputRequest(
        rule_identity="measure",
        section="ACTION",
        expression_index=3,
        request=measure_slot,
        command="up-get-group-size",
        argument_index=2,
    )
    identity = NativeDucOutputRequest(
        rule_identity="measure",
        section="ACTION",
        expression_index=4,
        request=identity_slot,
        command="up-get-object-data",
        argument_index=1,
    )
    plan = NativeDucPlan(
        rules=(
            NativeDucRule(
                identity="measure",
                order=0,
                facts=(_e("(true)", "true"),),
                actions=(
                    _e("(up-find-local c: 83 c: 1)", "up-find-local", "c:", "83", "c:", "1"),
                    _e("(up-set-target-object search-local c: 0)", "up-set-target-object", "search-local", "c:", "0"),
                    _e("(up-create-group 0 40 c: 0)", "up-create-group", "0", "40", "c:", "0"),
                    _e("(up-get-group-size c: 0 41)", "up-get-group-size", "c:", "0", "41"),
                    _e("(up-get-object-data id 41)", "up-get-object-data", "id", "41"),
                ),
            ),
            NativeDucRule(
                identity="window",
                order=1,
                facts=(_e("(true)", "true"),),
                actions=(
                    _e("(up-create-group 0 0 c: 1)", "up-create-group", "0", "0", "c:", "1"),
                ),
            ),
            NativeDucRule(
                identity="micro",
                order=2,
                facts=(_e("(true)", "true"),),
                actions=(
                    _e("(up-set-group search-local c: 1)", "up-set-group", "search-local", "c:", "1"),
                    _e("(up-set-target-object search-local c: 0)", "up-set-target-object", "search-local", "c:", "0"),
                    _e("(up-target-objects 1 0 -1 -1)", "up-target-objects", "1", "0", "-1", "-1"),
                ),
            ),
        ),
        output_requests=(measure, identity),
        input_requests=(
            NativeDucGoalInputRequest(
                rule_identity="window",
                section="ACTION",
                expression_index=0,
                argument_index=0,
                source=measure_slot.request_id,
            ),
            NativeDucGoalInputRequest(
                rule_identity="window",
                section="ACTION",
                expression_index=0,
                argument_index=1,
                source=identity_slot.request_id,
            ),
        ),
    )
    source = """
demand marker {
    require (can-train spearman)
    action (train spearman)
    witness (unit-type-count spearman >= 1)
    release (unit-type-count spearman >= 1)
}
"""
    return source, plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    source, plan = _vertical()
    first = compile_source(source, duc_plan=plan)
    _, repeat_plan = _vertical()
    second = compile_source(source, duc_plan=repeat_plan)

    if first != second:
        raise SystemExit(
            "group window fixture produced non-deterministic artifacts"
        )

    required_fragments = (
        "(up-find-local c: 83 c: 1)",
        "(up-create-group 0 40 c: 0)",
        "(up-set-group search-local c: 1)",
        "(up-set-target-object search-local c: 0)",
        "(up-target-objects 1 0 -1 -1)",
    )
    missing = [fragment for fragment in required_fragments if fragment not in first]
    if missing:
        raise SystemExit(
            "group window fixture is missing expected native output: "
            + ", ".join(missing)
        )

    size_slot = re.search(r"\(up-get-group-size c: 0 (\d+)\)", first)
    id_slot = re.search(r"\(up-get-object-data id (\d+)\)", first)
    windowed = re.search(r"\(up-create-group (\d+) (\d+) c: 1\)", first)
    if size_slot is None or id_slot is None or windowed is None:
        raise SystemExit("group window fixture is missing the measure/window pair")
    if windowed.group(1) != size_slot.group(1) or windowed.group(2) != id_slot.group(1):
        raise SystemExit(
            "group window handoff is broken: window "
            f"({windowed.group(1)}, {windowed.group(2)}) != "
            f"measured ({size_slot.group(1)}, {id_slot.group(1)})"
        )

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
        "window_start_goal": windowed.group(1),
        "window_size_goal": windowed.group(2),
        "required_fragments": required_fragments,
        "native_gate_returncode": result.returncode,
        "native_report": str(native_report),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "runtime_membership_status": "OPEN",
        "runtime_membership_reason": (
            "The compiler resolves goal identity between measure and "
            "window; group membership, flag values, and target liveness "
            "remain unverified runtime research."
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
        "group window native artifact gate passed "
        f"(sha256={report['artifact_sha256']}; "
        f"window=({windowed.group(1)}, {windowed.group(2)}); runtime=OPEN)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
