#!/usr/bin/env python3
"""Native zero-findings acceptance gate for the typed internal DUC plan path."""
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
from Compiler.ir import GoalRole, GoalSlotRequest, GoalSpanKind, GoalSpanRequest, SemanticId, StorageRequestId
from Compiler.ir import NativeDucOutputRequest, NativeDucPlan, NativeDucRule


def _search_state_output_request() -> NativeDucOutputRequest:
    request = GoalSpanRequest(
        StorageRequestId(
            SemanticId("native.duc", "search-state-output"),
            "up-get-search-state",
        ),
        role=GoalRole.NATIVE_OUTPUT,
        width=4,
        shape=GoalSpanKind.EXTENDED_4,
        contract_id="up-get-search-state.OutputGoalId",
        start_min=41,
        start_max=15996,
    )
    return NativeDucOutputRequest(
        rule_identity="search-state",
        section="ACTION",
        expression_index=0,
        request=request,
        command="up-get-search-state",
        argument_index=0,
    )


def _group_size_output_request() -> NativeDucOutputRequest:
    request = GoalSlotRequest(
        StorageRequestId(
            SemanticId("native.duc", "group-size-output"),
            "up-get-group-size",
        ),
        role=GoalRole.NATIVE_OUTPUT,
    )
    return NativeDucOutputRequest(
        rule_identity="group-size",
        section="ACTION",
        expression_index=0,
        request=request,
        command="up-get-group-size",
        argument_index=2,
    )


def _cost_delta_output_request() -> NativeDucOutputRequest:
    request = GoalSpanRequest(
        StorageRequestId(
            SemanticId("native.duc", "cost-delta-output"),
            "up-get-cost-delta",
        ),
        role=GoalRole.NATIVE_OUTPUT,
        width=4,
        shape=GoalSpanKind.EXTENDED_4,
        contract_id="up-get-cost-delta.OutputGoalId",
        start_min=41,
        start_max=15996,
    )
    return NativeDucOutputRequest(
        rule_identity="cost-delta",
        section="ACTION",
        expression_index=0,
        request=request,
        command="up-get-cost-delta",
        argument_index=0,
    )


def _point_output_request() -> NativeDucOutputRequest:
    request = GoalSpanRequest(
        StorageRequestId(
            SemanticId("native.duc", "point-output"),
            "up-get-point",
        ),
        role=GoalRole.NATIVE_OUTPUT,
        width=2,
        shape=GoalSpanKind.POINT_PAIR,
        contract_id="up-get-point.Point",
        start_min=41,
        start_max=15998,
    )
    return NativeDucOutputRequest(
        rule_identity="point",
        section="ACTION",
        expression_index=0,
        request=request,
        command="up-get-point",
        argument_index=1,
    )


def _target_data_output_request(
    command: str,
    rule_identity: str,
) -> NativeDucOutputRequest:
    request = GoalSlotRequest(
        StorageRequestId(
            SemanticId("native.duc", rule_identity),
            command,
        ),
        role=GoalRole.NATIVE_OUTPUT,
    )
    return NativeDucOutputRequest(
        rule_identity=rule_identity,
        section="ACTION",
        expression_index=0,
        request=request,
        command=command,
        argument_index=1,
    )


def _plan() -> NativeDucPlan:
    return NativeDucPlan(
        (
            NativeDucRule(
                identity="search-and-select",
                order=100,
                facts=(
                    Expression(
                        "(up-find-local c: 83 c: 1)",
                        "up-find-local",
                        ("c:", "83", "c:", "1"),
                    ),
                ),
                actions=(
                    Expression(
                        "(up-set-target-object search-local c: 0)",
                        "up-set-target-object",
                        ("search-local", "c:", "0"),
                    ),
                ),
            ),
            NativeDucRule(
                identity="search-state",
                order=101,
                facts=(
                    Expression(
                        "(true)",
                        "true",
                        (),
                    ),
                ),
                actions=(
                    Expression(
                        "(up-get-search-state 41)",
                        "up-get-search-state",
                        ("41",),
                    ),
                ),
            ),
            NativeDucRule(
                identity="object-data",
                order=102,
                facts=(
                    Expression(
                        "(true)",
                        "true",
                        (),
                    ),
                ),
                actions=(
                    Expression(
                        "(up-get-object-data 38 41)",
                        "up-get-object-data",
                        ("38", "41"),
                    ),
                ),
            ),
            NativeDucRule(
                identity="object-target-data",
                order=103,
                facts=(
                    Expression(
                        "(true)",
                        "true",
                        (),
                    ),
                ),
                actions=(
                    Expression(
                        "(up-get-object-target-data 38 41)",
                        "up-get-object-target-data",
                        ("38", "41"),
                    ),
                ),
            ),
            NativeDucRule(
                identity="point",
                order=104,
                facts=(
                    Expression(
                        "(true)",
                        "true",
                        (),
                    ),
                ),
                actions=(
                    Expression(
                        "(up-get-point position-center 41)",
                        "up-get-point",
                        ("position-center", "41"),
                    ),
                ),
            ),
            NativeDucRule(
                identity="cost-delta",
                order=105,
                facts=(
                    Expression(
                        "(true)",
                        "true",
                        (),
                    ),
                ),
                actions=(
                    Expression(
                        "(up-get-cost-delta 41)",
                        "up-get-cost-delta",
                        ("41",),
                    ),
                ),
            ),
            NativeDucRule(
                identity="group-size",
                order=106,
                facts=(
                    Expression(
                        "(true)",
                        "true",
                        (),
                    ),
                ),
                actions=(
                    Expression(
                        "(up-get-group-size c: 3 41)",
                        "up-get-group-size",
                        ("c:", "3", "41"),
                    ),
                ),
            ),
            NativeDucRule(
                identity="group-create",
                order=108,
                facts=(),
                actions=(
                    Expression(
                        "(up-create-group 0 40 c: 0)",
                        "up-create-group",
                        ("0", "40", "c:", "0"),
                    ),
                ),
            ),
            NativeDucRule(
                identity="group-size-fact",
                order=109,
                facts=(
                    Expression(
                        "(up-group-size c: 0 > 0)",
                        "up-group-size",
                        ("c:", "0", ">", "0"),
                    ),
                ),
                actions=(),
            ),
            NativeDucRule(
                identity="group-set",
                order=110,
                facts=(),
                actions=(
                    Expression(
                        "(up-set-group search-local c: 0)",
                        "up-set-group",
                        ("search-local", "c:", "0"),
                    ),
                ),
            ),
            NativeDucRule(
                identity="group-flag",
                order=111,
                facts=(),
                actions=(
                    Expression(
                        "(up-modify-group-flag 1 c: 0)",
                        "up-modify-group-flag",
                        ("1", "c:", "0"),
                    ),
                ),
            ),
            NativeDucRule(
                identity="group-reset",
                order=112,
                facts=(),
                actions=(
                    Expression(
                        "(up-reset-group c: 0)",
                        "up-reset-group",
                        ("c:", "0"),
                    ),
                ),
            ),
            NativeDucRule(
                identity="target-action",
                order=113,
                facts=(
                    Expression(
                        "(up-set-target-object search-local c: 0)",
                        "up-set-target-object",
                        ("search-local", "c:", "0"),
                    ),
                ),
                actions=(
                    Expression(
                        "(up-target-objects 1 0 -1 -1)",
                        "up-target-objects",
                        ("1", "0", "-1", "-1"),
                    ),
                ),
            ),
        ),
        output_requests=(
            _search_state_output_request(),
            _group_size_output_request(),
            _cost_delta_output_request(),
            _point_output_request(),
            _target_data_output_request(
                "up-get-object-data",
                "object-data",
            ),
            _target_data_output_request(
                "up-get-object-target-data",
                "object-target-data",
            ),
        ),
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

    source = """
    demand marker {
        require (can-train spearman)
        action (train spearman)
        witness (unit-type-count spearman >= 1)
        release (unit-type-count spearman >= 1)
    }
    """
    plan = _plan()
    first = compile_source(source, duc_plan=plan)
    second = compile_source(source, duc_plan=plan)
    if first != second:
        raise SystemExit("typed NativeDucPlan artifact is non-deterministic")

    required_fragments = (
        "(up-find-local c: 83 c: 1)",
        "(up-get-search-state 52)",
        "(up-get-group-size c: 3 42)",
        "(up-get-object-data 38 43)",
        "(up-get-object-target-data 38 44)",
        "(up-get-cost-delta 46)",
        "(up-get-point position-center 50)",
        "(up-set-target-object search-local c: 0)",
        "(up-target-objects 1 0 -1 -1)",
    )
    missing = tuple(
        fragment for fragment in required_fragments if fragment not in first
    )
    if missing:
        raise SystemExit(
            f"DUC artifact is missing emitted commands: {missing}"
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
        "duc_rules": [
            {
                "identity": rule.identity,
                "order": rule.order,
                "facts": tuple(expression.source for expression in rule.facts),
                "actions": tuple(expression.source for expression in rule.actions),
            }
            for rule in plan.rules
        ],
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
            f"DUC native gate failed: finding_count={finding_count}",
            file=sys.stderr,
        )
        return 1

    print(
        "DUC compiler/native zero-findings gate passed "
        f"(sha256={report['artifact_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
