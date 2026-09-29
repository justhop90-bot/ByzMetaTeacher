#!/usr/bin/env python3
"""Native zero-findings acceptance gate for targeted research escrow release lowering."""
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
    owner = SemanticId("fixture", "research")
    return NativeEscrowReleasePlan(
        (
            EscrowOperation(
                contract_identity="research-food",
                owner=owner,
                kind=EscrowOperationKind.RELEASE,
                resource="food",
                command="release-escrow",
                rule_order=100,
                within_rule_order=0,
                target_demand=owner,
            ),
        )
    )


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    source_path = Path(__file__).parent / "fixtures" / "research_escrow.perdsl"
    source = source_path.read_text(encoding="utf-8")
    plan = _plan()

    first = compile_source(source, source_unit="fixture", escrow_plan=plan)
    second = compile_source(source, source_unit="fixture", escrow_plan=plan)
    if first != second:
        raise SystemExit("targeted research escrow artifact is non-deterministic")

    action_start = first.index("; Action issuance: research")
    action_block = first[action_start:]
    release_pos = action_block.index("(release-escrow food)")
    research_pos = action_block.index("(research feudal-age)")
    if release_pos >= research_pos:
        raise SystemExit("targeted escrow release was not emitted before research")

    if "; Native escrow release plan" in action_block:
        raise SystemExit("targeted escrow release leaked into standalone release-plan emission")

    for forbidden in (
        "(set-escrow-percentage",
        "(up-modify-escrow",
        "(up-release-escrow",
    ):
        if forbidden in action_block:
            raise SystemExit(
                f"research escrow claim emitted out-of-scope mutation: {forbidden}"
            )

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
        "owner": {
            "source_unit": "fixture",
            "local_name": "research",
        },
        "released_resources": ["food"],
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
        print(f"native validator exited {result.returncode}", file=sys.stderr)
        return result.returncode or 1
    if finding_count != 0 or findings != []:
        print(
            f"research escrow native gate failed: finding_count={finding_count}",
            file=sys.stderr,
        )
        return 1

    print(
        "research escrow claim compiler/native zero-findings gate passed "
        f"(sha256={report['artifact_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
