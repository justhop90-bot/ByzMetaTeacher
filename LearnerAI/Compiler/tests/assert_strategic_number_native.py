#!/usr/bin/env python3
"""Native zero-findings acceptance gate for compiler-owned Strategic Number state."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from Compiler.compiler import compile_source
from Compiler.primitives.strategic_number_catalog import (
    default_strategic_number_catalog,
)

FIXTURE = Path(__file__).parent / "fixtures" / "strategic_number.perdsl"


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
        raise SystemExit(f"native validator did not return JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("native validator JSON root must be an object")
    return result, payload


def _numeric_states(artifact: str) -> dict[str, int]:
    pattern = re.compile(r"^\(defconst\s+([a-z][a-z0-9_-]*)\s+(\d+)\)$")
    result: dict[str, int] = {}
    for line in artifact.splitlines():
        match = pattern.match(line)
        if match:
            result[match.group(1)] = int(match.group(2))
    return {
        name: result[name]
        for name in ("posture", "secondary-posture")
        if name in result
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    SOURCE = FIXTURE.read_text(encoding="utf-8")
    first = compile_source(SOURCE)
    second = compile_source(SOURCE)
    if first != second:
        raise SystemExit("compiler-owned Strategic Number artifact is non-deterministic")

    states = _numeric_states(first)
    if set(states) != {"posture", "secondary-posture"}:
        raise SystemExit(f"expected compiler-owned SN bindings, found {sorted(states)}")

    catalog = default_strategic_number_catalog()
    if not set(states.values()).issubset(catalog.compiler_candidate_ids):
        raise SystemExit(
            f"compiler emitted non-candidate Strategic Number(s): {sorted(states.values())}"
        )
    if 511 in states.values():
        raise SystemExit("compiler emitted reserved Strategic Number 511")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(first, encoding="utf-8")

    result, payload = _validate_native(args.output)
    finding_count = payload.get("finding_count")
    findings = payload.get("findings")

    report = {
        "artifact": str(args.output.resolve()),
        "fixture_source_sha256": hashlib.sha256(
            SOURCE.encode("utf-8")
        ).hexdigest(),
        "artifact_sha256": hashlib.sha256(
            first.encode("utf-8")
        ).hexdigest(),
        "validator_exit_code": result.returncode,
        "strategic_number_bindings": states,
        "strategic_number_catalog_version": catalog.version,
        "strategic_number_inventory_sha": catalog.inventory.inventory_sha,
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
        "strategic-number compiler/native zero-findings gate passed "
        f"(sha256={report['artifact_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
