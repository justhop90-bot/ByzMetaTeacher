#!/usr/bin/env python3
"""Native zero-findings acceptance gate for compiler-owned Timer allocation."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.compiler import _binding_manifest_text, _compile_source_parts
from Compiler.primitives import default_de_registry

FIXTURE = Path(__file__).parent / "fixtures" / "timer_allocation.perdsl"
_TIMER_DEFCONST = re.compile(r"^\(defconst\s+([a-z][a-z0-9_-]*)\s+(\d+)\)$")


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


def _timer_bindings(artifact: str) -> dict[str, int]:
    bindings: dict[str, int] = {}
    for line in artifact.splitlines():
        match = _TIMER_DEFCONST.match(line)
        if match:
            bindings[match.group(1)] = int(match.group(2))
    return {
        name: bindings[name]
        for name in ("cooldown",)
        if name in bindings
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    source = FIXTURE.read_text(encoding="utf-8")
    first, first_bindings, first_context = _compile_source_parts(
        source,
        source_unit="timer-fixture",
        registry=default_de_registry(),
    )
    second, second_bindings, second_context = _compile_source_parts(
        source,
        source_unit="timer-fixture",
        registry=default_de_registry(),
    )
    if first != second:
        raise SystemExit("compiler-owned Timer artifact is non-deterministic")

    first_manifest = _binding_manifest_text(first_bindings, first_context)
    second_manifest = _binding_manifest_text(second_bindings, second_context)
    if first_manifest != second_manifest:
        raise SystemExit("compiler-owned Timer binding manifest is non-deterministic")

    bindings = _timer_bindings(first)
    if bindings != {"cooldown": 1}:
        raise SystemExit(f"expected deterministic Timer binding {{'cooldown': 1}}, found {bindings}")

    if "(disable-timer cooldown)" not in first:
        raise SystemExit("timer initialization rule is missing disable-timer cooldown")

    manifest_payload = json.loads(first_manifest)
    timer_records = [
        record
        for record in manifest_payload["records"]
        if record.get("binding_kind") == "TIMER"
    ]
    if len(timer_records) != 1:
        raise SystemExit(f"expected one Timer binding record, found {len(timer_records)}")
    record = timer_records[0]
    if record["timer_id"] != 1:
        raise SystemExit(f"expected TimerId 1, found {record['timer_id']}")
    if record["initialization_policy"] != "DISABLE_BEFORE_FIRST_USE":
        raise SystemExit(
            "Timer binding did not preserve DISABLE_BEFORE_FIRST_USE initialization policy"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(first, encoding="utf-8")
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(first_manifest, encoding="utf-8")

    result, payload = _validate_native(args.output)
    finding_count = payload.get("finding_count")
    findings = payload.get("findings")

    report = {
        "artifact": str(args.output.resolve()),
        "binding_manifest": str(args.manifest.resolve()),
        "fixture_source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "artifact_sha256": hashlib.sha256(first.encode("utf-8")).hexdigest(),
        "binding_manifest_sha256": hashlib.sha256(
            first_manifest.encode("utf-8")
        ).hexdigest(),
        "validator_exit_code": result.returncode,
        "timer_bindings": bindings,
        "timer_records": timer_records,
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
        return result.returncode or 1
    if finding_count != 0 or findings != []:
        print(
            f"timer native gate failed: finding_count={finding_count}",
            file=sys.stderr,
        )
        return 1

    print(
        "timer compiler/native zero-findings gate passed "
        f"(artifact_sha256={report['artifact_sha256']}, "
        f"binding_manifest_sha256={report['binding_manifest_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
