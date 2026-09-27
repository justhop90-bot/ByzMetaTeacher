#!/usr/bin/env python3
"""Native zero-findings acceptance gate for Strategic Number semantics."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).parents[2]
FIXTURE = ROOT / "Compiler" / "tests" / "fixtures" / "strategic_number.per"

EXPECTED_TEXT = FIXTURE.read_text(encoding="utf-8")


def _validate_native(artifact: Path) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "aoe2_ai_lab",
            "lint",
            str(artifact),
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
        raise SystemExit(
            f"native validator did not return JSON: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise SystemExit("native validator JSON root must be an object")
    return result, payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    checked_in = FIXTURE.read_text(encoding="utf-8")
    if checked_in != EXPECTED_TEXT:
        raise SystemExit("strategic-number fixture changed during execution")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(EXPECTED_TEXT, encoding="utf-8")

    result, payload = _validate_native(args.output)
    finding_count = payload.get("finding_count")
    findings = payload.get("findings")

    report = {
        "artifact": str(args.output.resolve()),
        "fixture_sha256": hashlib.sha256(
            EXPECTED_TEXT.encode("utf-8")
        ).hexdigest(),
        "validator_exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "finding_count": finding_count,
        "findings": findings,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)

    if result.returncode != 0:
        print(
            f"native validator exited {result.returncode}",
            file=sys.stderr,
        )
        return result.returncode or 1
    if finding_count != 0 or findings != []:
        print(
            f"strategic-number native gate failed: finding_count={finding_count}",
            file=sys.stderr,
        )
        return 1

    print(
        "strategic-number native zero-findings gate passed "
        f"(sha256={report['fixture_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
