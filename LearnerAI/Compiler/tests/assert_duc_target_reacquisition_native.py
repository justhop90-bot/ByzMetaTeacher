#!/usr/bin/env python3
"""Native acceptance gate for DUC target reacquisition by stored identity.

Vertical: DISCOVER (find + set-target-object) -> STORE_ID
(up-get-object-data 0 into an allocated GoalSlot) ->
REACQUIRE (up-set-target-by-id g: resolving to the same slot) ->
ISSUE (up-target-objects). Target liveness remains runtime OPEN.
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
    owner = SemanticId("test", "reacquire")
    slot = GoalSlotRequest(
        StorageRequestId(owner, "up-get-object-data"),
        role=GoalRole.NATIVE_OUTPUT,
    )
    writer = NativeDucOutputRequest(
        rule_identity="discover",
        section="ACTION",
        expression_index=2,
        request=slot,
        command="up-get-object-data",
        argument_index=1,
    )
    plan = NativeDucPlan(
        rules=(
            NativeDucRule(
                identity="discover",
                order=0,
                facts=(_e("(true)", "true"),),
                actions=(
                    _e("(up-find-local c: 83 c: 1)", "up-find-local", "c:", "83", "c:", "1"),
                    _e("(up-set-target-object search-local c: 0)", "up-set-target-object", "search-local", "c:", "0"),
                    _e("(up-get-object-data 0 41)", "up-get-object-data", "0", "41"),
                ),
            ),
            NativeDucRule(
                identity="reacquire",
                order=1,
                facts=(_e("(true)", "true"),),
                actions=(
                    _e("(up-set-target-by-id g: 0)", "up-set-target-by-id", "g:", "0"),
                    _e("(up-target-objects 1 0 -1 -1)", "up-target-objects", "1", "0", "-1", "-1"),
                ),
            ),
        ),
        output_requests=(writer,),
        input_requests=(
            NativeDucGoalInputRequest(
                rule_identity="reacquire",
                section="ACTION",
                expression_index=0,
                argument_index=1,
                source=slot.request_id,
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
            "target reacquisition fixture produced non-deterministic artifacts"
        )

    required_fragments = (
        "(up-find-local c: 83 c: 1)",
        "(up-set-target-object search-local c: 0)",
        "(up-target-objects 1 0 -1 -1)",
    )
    missing = [fragment for fragment in required_fragments if fragment not in first]
    if missing:
        raise SystemExit(
            "target reacquisition fixture is missing expected native output: "
            + ", ".join(missing)
        )

    written = re.search(r"\(up-get-object-data 0 (\d+)\)", first)
    read = re.search(r"\(up-set-target-by-id g: (\d+)\)", first)
    if written is None or read is None:
        raise SystemExit(
            "target reacquisition fixture is missing the store/reacquire pair"
        )
    if written.group(1) != read.group(1):
        raise SystemExit(
            "target reacquisition handoff is broken: store goal "
            f"{written.group(1)} != reacquire goal {read.group(1)}"
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
        "stored_goal": written.group(1),
        "required_fragments": required_fragments,
        "native_gate_returncode": result.returncode,
        "native_report": str(native_report),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "runtime_liveness_status": "OPEN",
        "runtime_liveness_reason": (
            "The compiler resolves goal identity between store and "
            "reacquire; whether the native object is alive at the "
            "reacquire rule remains unverified runtime research."
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
        "target reacquisition native artifact gate passed "
        f"(sha256={report['artifact_sha256']}; goal={written.group(1)}; runtime=OPEN)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
