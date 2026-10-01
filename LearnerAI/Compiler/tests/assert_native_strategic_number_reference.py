#!/usr/bin/env python3
"""Native zero-findings acceptance gate for documented native Strategic Number references."""
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
from Compiler.ir import NativeControlPlan, NativeControlRule, NativeControlState
from Compiler.ir.strategic_number import StrategicNumberOrigin
from Compiler.ir.model import SemanticId, StorageRequestId
from Compiler.runtime_binding import StrategicNumberRequest
from Compiler.semantic.analyzer import parse_expression

FIXTURE = Path(__file__).parent / "fixtures" / "native_strategic_number_reference.perdsl"
_NATIVE_SN_NAME = "sn-food-gatherer-percentage"
_NATIVE_SN_ID = 117


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


def _control_plan() -> NativeControlPlan:
    owner = SemanticId("native-sn-reference.fixture", "native-sn")
    request = StrategicNumberRequest(
        StorageRequestId(owner, "native-sn-food-gatherer"),
        why_not_goal="This state is an engine-defined Strategic Number with a documented native identity.",
        stability_key="native-sn-reference.fixture:native-sn-food-gatherer",
        origin=StrategicNumberOrigin.NATIVE_REFERENCE,
        native_strategic_number_id=_NATIVE_SN_ID,
    )
    return NativeControlPlan(
        states=(NativeControlState(_NATIVE_SN_NAME, request),),
        rules=(
            NativeControlRule(
                "feudal-food-mode",
                facts=(parse_expression("(current-age >= feudal-age)"),),
                actions=(
                    parse_expression(
                        f"(set-strategic-number {_NATIVE_SN_NAME} 45)"
                    ),
                ),
            ),
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    source = FIXTURE.read_text(encoding="utf-8")
    plan = _control_plan()
    first = compile_source(source, control_plan=plan)
    second = compile_source(source, control_plan=plan)
    if first != second:
        raise SystemExit("native Strategic Number reference artifact is non-deterministic")

    expected_symbol = f"(defconst {_NATIVE_SN_NAME} {_NATIVE_SN_ID})"
    expected_guard = "(current-age >= feudal-age)"
    expected_write = f"(set-strategic-number {_NATIVE_SN_NAME} 45)"
    forbidden_init = f"(set-strategic-number {_NATIVE_SN_NAME} 0)"

    if expected_symbol not in first:
        raise SystemExit("native Strategic Number defconst binding is missing")
    if expected_guard not in first:
        raise SystemExit("guarded native Strategic Number rule is missing")
    if first.count(expected_write) != 1:
        raise SystemExit("guarded native Strategic Number write is not emitted exactly once")
    if forbidden_init in first:
        raise SystemExit("native Strategic Number received a compiler-owned initialization write")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(first, encoding="utf-8")

    result, payload = _validate_native(args.output)
    finding_count = payload.get("finding_count")
    findings = payload.get("findings")

    report = {
        "artifact": str(args.output.resolve()),
        "fixture_source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "artifact_sha256": hashlib.sha256(first.encode("utf-8")).hexdigest(),
        "validator_exit_code": result.returncode,
        "native_strategic_number_name": _NATIVE_SN_NAME,
        "native_strategic_number_id": _NATIVE_SN_ID,
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
            f"native Strategic Number reference gate failed: finding_count={finding_count}",
            file=sys.stderr,
        )
        return 1

    print(
        "native Strategic Number reference zero-findings gate passed "
        f"(sha256={report['artifact_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
