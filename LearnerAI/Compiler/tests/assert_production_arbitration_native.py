#!/usr/bin/env python3
"""Native acceptance gate for the production/train arbitration seam."""
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

FIXTURE = Path(__file__).parent / "fixtures" / "production_arbitration.perdsl"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    source = FIXTURE.read_text(encoding="utf-8")
    first = compile_source(source)
    second = compile_source(source)

    if first != second:
        raise SystemExit(
            "production arbitration fixture produced non-deterministic artifacts"
        )

    required_fragments = (
        "(build castle)",
        "(train spearman)",
        "(defconst action-claim-build-pass-singleton",
        "(defconst action-claim-train-arbitration",
        "(goal action-claim-train-arbitration 0)",
        "(set-goal action-claim-train-arbitration 1)",
    )
    missing = [fragment for fragment in required_fragments if fragment not in first]
    if missing:
        raise SystemExit(
            "production arbitration fixture is missing expected native output: "
            + ", ".join(missing)
        )

    # The compiler-policy production claim must not leak native-only
    # vocabulary: no invented train conflict primitive appears in output.
    forbidden_fragments = ("train-arbitration-conflict", "up-train-arbitrate")
    present = [fragment for fragment in forbidden_fragments if fragment in first]
    if present:
        raise SystemExit(
            "production arbitration fixture emits invented native vocabulary: "
            + ", ".join(present)
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
        "fixture_source_sha256": hashlib.sha256(
            source.encode("utf-8")
        ).hexdigest(),
        "artifact_sha256": hashlib.sha256(first.encode("utf-8")).hexdigest(),
        "required_fragments": required_fragments,
        "native_gate_returncode": result.returncode,
        "native_report": str(native_report),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "runtime_arbitration_status": "OPEN",
        "runtime_arbitration_reason": (
            "Compiler-policy train arbitration is deterministic static "
            "ownership; exact DE busy/queue interaction, same-pass "
            "arbitration, starvation, provider loss, and queue timing "
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
        "production arbitration native artifact gate passed "
        f"(sha256={report['artifact_sha256']}; runtime=OPEN)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
