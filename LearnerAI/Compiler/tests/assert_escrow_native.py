#!/usr/bin/env python3
"""Native zero-findings acceptance gate for the release-escrow lowering slice."""
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
from Compiler.ir import (
    EscrowOperation,
    EscrowOperationKind,
    NativeEscrowReleasePlan,
    SemanticId,
)


def _plan() -> NativeEscrowReleasePlan:
    owner = SemanticId("fixture", "escrow-release")
    return NativeEscrowReleasePlan(
        (
            EscrowOperation(
                contract_identity="release-food",
                owner=owner,
                kind=EscrowOperationKind.RELEASE,
                resource="food",
                command="release-escrow",
                rule_order=400,
                within_rule_order=0,
            ),
            EscrowOperation(
                contract_identity="release-gold",
                owner=owner,
                kind=EscrowOperationKind.RELEASE,
                resource="gold",
                command="release-escrow",
                rule_order=400,
                within_rule_order=1,
            ),
            EscrowOperation(
                contract_identity="release-wood",
                owner=owner,
                kind=EscrowOperationKind.RELEASE,
                resource="wood",
                command="release-escrow",
                rule_order=401,
                within_rule_order=0,
            ),
        )
    )


def _validate_native(
    artifact: Path,
) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    source_path = Path(__file__).parent / "fixtures" / "escrow_release.perdsl"
    source = source_path.read_text(encoding="utf-8")
    plan = _plan()

    first = compile_source(source, escrow_plan=plan)
    second = compile_source(source, escrow_plan=plan)
    if first != second:
        raise SystemExit("NativeEscrowReleasePlan artifact is non-deterministic")

    required = (
        "; Native escrow release plan",
        "; Native escrow release rule: 400",
        "(release-escrow food)",
        "(release-escrow gold)",
        "; Native escrow release rule: 401",
        "(release-escrow wood)",
    )
    missing = tuple(fragment for fragment in required if fragment not in first)
    if missing:
        raise SystemExit(f"escrow artifact is missing emitted fragments: {missing}")

    section = first.split("; Native escrow release plan", 1)[1]
    for marker in (
        "\n; Native persistent control plane",
        "\n; Per-pass transient action arbitration",
        "\n; Per-pass construction retry barriers",
        "\n; Demand initialization",
    ):
        if marker in section:
            section = section.split(marker, 1)[0]
            break

    forbidden = (
        "(set-escrow-percentage",
        "(up-modify-escrow",
        "(up-release-escrow",
        "(set-goal",
        "(research ",
        "(build ",
        "(train ",
    )
    present = tuple(fragment for fragment in forbidden if fragment in section)
    if present:
        raise SystemExit(
            f"escrow release section emitted out-of-scope commands: {present}"
        )

    release_lines = tuple(
        line.strip()
        for line in section.splitlines()
        if line.strip().startswith("(release-escrow ")
    )
    if release_lines != (
        "(release-escrow food)",
        "(release-escrow gold)",
        "(release-escrow wood)",
    ):
        raise SystemExit(f"release emission is not deterministic: {release_lines}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(first, encoding="utf-8")

    result, payload = _validate_native(args.output)
    finding_count = payload.get("finding_count")
    findings = payload.get("findings")

    report = {
        "artifact": str(args.output.resolve()),
        "fixture": str(source_path),
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "artifact_sha256": hashlib.sha256(first.encode("utf-8")).hexdigest(),
        "validator_exit_code": result.returncode,
        "operations": [
            {
                "contract_identity": operation.contract_identity,
                "owner": {
                    "source_unit": operation.owner.source_unit,
                    "local_name": operation.owner.local_name,
                },
                "resource": operation.resource,
                "rule_order": operation.rule_order,
                "within_rule_order": operation.within_rule_order,
            }
            for operation in plan.operations
        ],
        "finding_count": finding_count,
        "findings": findings,
        "stdout": result.stdout,
        "stderr": result.stderr,
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
            f"escrow native gate failed: finding_count={finding_count}",
            file=sys.stderr,
        )
        return 1

    print(
        "escrow release compiler/native zero-findings gate passed "
        f"(sha256={report['artifact_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
