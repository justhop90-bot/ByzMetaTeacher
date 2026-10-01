#!/usr/bin/env python3
"""Native acceptance gate for inventory-gap unit aliases.

Compiles train demands for demolition-raft (1104) and carrack (2628),
whose symbols come from the evidenced alias table rather than the pinned
AIRef object inventory, and requires parser zero-findings on the emitted
artifact. Alias legitimacy (manifest identity + parser acceptance) is
pinned here: a bad alias symbol fails this gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.compiler import compile_source

SOURCE = """
demand demolition-raft-line {
    require (unit-type-count-total demolition-raft < 2)
    require (can-train demolition-raft)
    action (train demolition-raft)
    witness (unit-type-count demolition-raft >= 2)
    release (unit-type-count demolition-raft >= 2)
}

demand carrack-line {
    require (unit-type-count-total carrack < 1)
    require (can-train carrack)
    action (train carrack)
    witness (unit-type-count carrack >= 1)
    release (unit-type-count carrack >= 1)
}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    first = compile_source(SOURCE)
    second = compile_source(SOURCE)

    if first != second:
        raise SystemExit(
            "unit alias fixture produced non-deterministic artifacts"
        )

    required_fragments = (
        "(train demolition-raft)",
        "(up-pending-objects c: 1104 >= 1)",
        "(train carrack)",
        "(up-pending-objects c: 2628 >= 1)",
    )
    missing = [fragment for fragment in required_fragments if fragment not in first]
    if missing:
        raise SystemExit(
            "unit alias fixture is missing expected native output: "
            + ", ".join(missing)
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
        "required_fragments": required_fragments,
        "native_gate_returncode": result.returncode,
        "native_report": str(native_report),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "runtime_alias_status": "OPEN",
        "runtime_alias_reason": (
            "Alias legitimacy is manifest identity plus parser acceptance; "
            "live engine training behavior for these hulls remains "
            "unverified runtime research."
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
        "unit alias native artifact gate passed "
        f"(sha256={report['artifact_sha256']}; runtime=OPEN)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
