#!/usr/bin/env python3
"""Native zero-findings acceptance gate for the typed native attack lifecycle path."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.ast import Expression
from Compiler.compiler import compile_source
from Compiler.ir import (
    AttackLifecycleObservation,
    NativeAttackLifecyclePlan,
    NativeAttackRule,
)


LIFECYCLE = (
    AttackLifecycleObservation.ADMISSION_REQUIRED,
    AttackLifecycleObservation.ISSUE,
    AttackLifecycleObservation.COMPLETION_UNOBSERVED,
    AttackLifecycleObservation.REASSESS_REQUIRED,
)


def _plan() -> NativeAttackLifecyclePlan:
    return NativeAttackLifecyclePlan(
        (
            NativeAttackRule(
                identity="attack-first",
                order=10,
                facts=(Expression("(true)", "true", ()),),
                actions=(Expression("(attack-now)", "attack-now", ()),),
                lifecycle=LIFECYCLE,
            ),
            NativeAttackRule(
                identity="attack-second",
                order=20,
                facts=(Expression("(true)", "true", ()),),
                actions=(Expression("(attack-now)", "attack-now", ()),),
                lifecycle=LIFECYCLE,
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

    source = """
    demand marker {
        require (can-train spearman)
        action (train spearman)
        witness (unit-type-count spearman >= 1)
        release (unit-type-count spearman >= 1)
    }
    """

    plan = _plan()
    first = compile_source(source, attack_plan=plan)
    second = compile_source(source, attack_plan=plan)

    if first != second:
        raise SystemExit("typed NativeAttackLifecyclePlan artifact is non-deterministic")

    required_fragments = (
        "; Native attack lifecycle plan",
        "; Native attack rule: attack-first",
        "; Native attack rule: attack-second",
        "(attack-now)",
    )
    missing = tuple(fragment for fragment in required_fragments if fragment not in first)
    if missing:
        raise SystemExit(f"attack artifact is missing emitted fragments: {missing}")

    forbidden_fragments = (
        "sn-number-attack-groups",
        "sn-percent-attack-soldiers",
        "sn-initial-exploration-required",
        "sn-number-explore-groups",
        "sn-total-number-explorers",
        "sn-enemy-sighted-response-distance",
        "sn-maximum-town-size",
        "(up-reset-attack-now)",
        "(timer-triggered",
        "(enable-timer",
    )
    present = tuple(fragment for fragment in forbidden_fragments if fragment in first)
    if present:
        raise SystemExit(
            f"attack artifact emitted forbidden controller/lifecycle machinery: {present}"
        )

    attack_section = first.split("; Native attack lifecycle plan", 1)[1]
    attack_section = attack_section.split("; Native persistent control plane", 1)[0]
    if "(set-goal " in attack_section:
        raise SystemExit("attack lifecycle section emitted synthetic goal lifecycle state")
    if "COMPLETE" in attack_section or "RELEASE" in attack_section:
        raise SystemExit("attack lifecycle section emitted synthetic completion/release semantics")

    if first.count("(attack-now)") != 2:
        raise SystemExit(
            f"expected exactly two attack-now actions, found {first.count('(attack-now)')}"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(first, encoding="utf-8")

    result, payload = _validate_native(args.output)
    finding_count = payload.get("finding_count")
    findings = payload.get("findings")

    report = {
        "artifact": str(args.output.resolve()),
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "artifact_sha256": hashlib.sha256(first.encode("utf-8")).hexdigest(),
        "validator_exit_code": result.returncode,
        "attack_rules": [
            {
                "identity": rule.identity,
                "order": rule.order,
                "facts": tuple(expression.source for expression in rule.facts),
                "actions": tuple(expression.source for expression in rule.actions),
                "lifecycle": tuple(item.value for item in rule.lifecycle),
            }
            for rule in plan.rules
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
            f"attack native gate failed: finding_count={finding_count}",
            file=sys.stderr,
        )
        return 1

    print(
        "attack lifecycle compiler/native zero-findings gate passed "
        f"(sha256={report['artifact_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
