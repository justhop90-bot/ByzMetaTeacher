#!/usr/bin/env python3
"""Native acceptance gate for the production acceptance vertical.

Compiles the Byzantine castle strategy (early-defensive-spears
spearman-line TRAIN) and requires deterministic lowering plus parser
zero-findings with all chain fragments present: issuance, arbitration
claim, retry barrier, and world-state witness. Busy/queue/same-pass
behavior stays OPEN runtime research.
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

from Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_castle_strategy,
    compile_strategy_profile,
)
from Compiler.ir.civ_profile import resolve_effective_civ


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
    profile = build_byzantine_castle_strategy(effective)
    first = compile_strategy_profile(profile, effective)
    second = compile_strategy_profile(profile, effective)

    if first != second:
        raise SystemExit(
            "strategy production vertical produced non-deterministic artifacts"
        )

    required_fragments = (
        "(train spearman-line)",
        "(defconst action-claim-train-arbitration",
        "(goal action-claim-train-arbitration 0)",
        "(set-goal action-claim-train-arbitration 1)",
        "(set-goal production-retry-barrier-early-defensive-spears 1)",
        "(unit-type-count spearman-line >= 2)",
        "(can-train-with-escrow spearman-line)",
    )
    missing = [fragment for fragment in required_fragments if fragment not in first]
    if missing:
        raise SystemExit(
            "strategy production vertical is missing expected native output: "
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
        "runtime_queue_status": "OPEN",
        "runtime_queue_reason": (
            "The gate proves static chain linkage and parser acceptance; "
            "provider busy/queued behavior and same-pass visibility remain "
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
        "strategy production vertical gate passed "
        f"(sha256={report['artifact_sha256']}; runtime=OPEN)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
