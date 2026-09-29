#!/usr/bin/env python3
"""Native zero-findings acceptance for explicit escrow percentage lowering."""
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
    NativeEscrowPolicyPlan,
    SemanticId,
)


def _plan() -> NativeEscrowPolicyPlan:
    owner = SemanticId("fixture", "escrow-policy")
    return NativeEscrowPolicyPlan(
        (
            EscrowOperation(
                contract_identity="policy-food",
                owner=owner,
                kind=EscrowOperationKind.POLICY_RESET,
                resource="food",
                command="set-escrow-percentage",
                percentage=50,
                rule_order=400,
                within_rule_order=0,
            ),
            EscrowOperation(
                contract_identity="policy-gold",
                owner=owner,
                kind=EscrowOperationKind.POLICY_RESET,
                resource="gold",
                command="set-escrow-percentage",
                percentage=25,
                rule_order=400,
                within_rule_order=1,
            ),
            EscrowOperation(
                contract_identity="policy-wood",
                owner=owner,
                kind=EscrowOperationKind.POLICY_RESET,
                resource="wood",
                command="set-escrow-percentage",
                percentage=0,
                rule_order=401,
                within_rule_order=0,
            ),
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    source_path = Path(__file__).parent / "fixtures" / "escrow_policy.perdsl"
    source = source_path.read_text(encoding="utf-8")
    plan = _plan()

    first = compile_source(source, escrow_plan=plan)
    second = compile_source(source, escrow_plan=plan)
    if first != second:
        raise SystemExit("NativeEscrowPolicyPlan artifact is non-deterministic")

    required = (
        "; Native escrow policy plan",
        "; Native escrow policy rule: 400",
        "(set-escrow-percentage food 50)",
        "(set-escrow-percentage gold 25)",
        "; Native escrow policy rule: 401",
        "(set-escrow-percentage wood 0)",
    )
    missing = tuple(fragment for fragment in required if fragment not in first)
    if missing:
        raise SystemExit(f"escrow policy artifact is missing emitted fragments: {missing}")

    section = first.split("; Native escrow policy plan", 1)[1]
    for marker in (
        "\n; Native persistent control plane",
        "\n; Per-pass transient action arbitration",
        "\n; Per-pass construction retry barriers",
        "\n; Per-pass production retry barriers",
        "\n; Per-pass research retry barriers",
        "\n; Demand initialization",
    ):
        if marker in section:
            section = section.split(marker, 1)[0]
            break

    forbidden = (
        "(release-escrow",
        "(up-modify-escrow",
        "(up-release-escrow",
        "(set-goal",
    )
    present = tuple(fragment for fragment in forbidden if fragment in section)
    if present:
        raise SystemExit(f"escrow policy section emitted out-of-scope commands: {present}")

    policy_lines = tuple(
        line.strip()
        for line in section.splitlines()
        if line.strip().startswith("(set-escrow-percentage ")
    )
    if policy_lines != (
        "(set-escrow-percentage food 50)",
        "(set-escrow-percentage gold 25)",
        "(set-escrow-percentage wood 0)",
    ):
        raise SystemExit(f"policy emission is not deterministic: {policy_lines}")

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
        "artifact": str(args.output.resolve()),
        "fixture": str(source_path),
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "artifact_sha256": hashlib.sha256(first.encode("utf-8")).hexdigest(),
        "validator_exit_code": result.returncode,
        "operations": [
            {
                "contract_identity": operation.contract_identity,
                "resource": operation.resource,
                "percentage": operation.percentage,
                "rule_order": operation.rule_order,
                "within_rule_order": operation.within_rule_order,
            }
            for operation in plan.operations
        ],
        "finding_count": payload.get("finding_count"),
        "findings": payload.get("findings"),
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
        return result.returncode or 1
    if payload.get("finding_count") != 0 or payload.get("findings") != []:
        print(
            f"escrow policy native gate failed: finding_count={payload.get('finding_count')}",
            file=sys.stderr,
        )
        return 1

    print(
        "escrow policy compiler/native zero-findings gate passed "
        f"(sha256={report['artifact_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
