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

def build_fixture() -> str:
    lines = [
        "(defconst sn-test-a 510)",
        "(defconst sn-test-b 509)",
        "(defconst goal-test-a 500)",
        "",
        "(defrule",
        "    (true)",
        "=>",
        "    (set-goal goal-test-a 3)",
        "    (set-strategic-number sn-test-a 8)",
        "    (set-strategic-number sn-test-b 3)",
        "    (disable-self)",
        ")",
        "",
    ]
    domains = (
        ("c", "3"),
        ("g", "goal-test-a"),
        ("s", "sn-test-b"),
    )
    for prefix, value in domains:
        lines.extend(["(defrule", "    (true)", "=>"])
        for operator in ("=", "+", "-", "*", "/", "z/", "mod", "min", "max", "neg", "%*", "%/"):
            lines.append(
                f"    (up-modify-sn sn-test-a {prefix}:{operator} {value})"
            )
        lines.extend(["    (disable-self)", ")", ""])
    lines.extend([
        "(defrule",
        "    (strategic-number sn-test-a >= 0)",
        "    (up-compare-sn sn-test-a >= c:0)",
        "=>",
        "    (disable-self)",
        ")",
        "",
    ])
    return "
".join(lines)

EXPECTED_TEXT = build_fixture()


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
    generated = build_fixture()
    if checked_in != generated:
        raise SystemExit("strategic-number fixture is stale or non-reproducible")

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
