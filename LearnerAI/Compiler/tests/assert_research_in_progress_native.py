#!/usr/bin/env python3
"""Native zero-findings acceptance for research in-progress lifecycle lowering."""
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    fixture = ROOT / "tests" / "fixtures" / "research_in_progress.perdsl"
    source = fixture.read_text(encoding="utf-8")
    first = compile_source(source, source_unit=str(fixture))
    second = compile_source(source, source_unit=str(fixture))
    if first != second:
        raise SystemExit("research in-progress artifact is non-deterministic")

    required = (
        "(up-research-status c: ri-wheelbarrow >= research-pending)",
        "research-retry-barrier-research-wheelbarrow",
        "(research ri-wheelbarrow)",
        "(research-completed ri-wheelbarrow)",
    )
    missing = tuple(fragment for fragment in required if fragment not in first)
    if missing:
        raise SystemExit(f"research artifact missing required fragments: {missing}")

    retry = first[first.index("; RETRY | ISSUED/PENDING -> ACTIVE"):]
    issuance = first[first.index("; Action issuance: research-wheelbarrow"):]
    if "(not (up-research-status c: ri-wheelbarrow >= research-pending))" not in retry:
        raise SystemExit("research retry rule lacks native in-progress-loss guard")
    if "(goal research-retry-barrier-research-wheelbarrow 0)" not in issuance:
        raise SystemExit("research issuance rule lacks retry barrier guard")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(first, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "aoe2_ai_lab",
            "lint",
            str(args.output),
            "--profile",
            "default",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"native validator did not return JSON: {exc}") from exc

    report = {
        "fixture": str(fixture.resolve()),
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "artifact_sha256": hashlib.sha256(first.encode("utf-8")).hexdigest(),
        "validator_exit_code": result.returncode,
        "finding_count": payload.get("finding_count"),
        "findings": payload.get("findings"),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode != 0:
        return result.returncode or 1
    if payload.get("finding_count") != 0 or payload.get("findings") != []:
        return 1
    print(f"research in-progress native gate passed (sha256={report['artifact_sha256']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
