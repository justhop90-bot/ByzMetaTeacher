#!/usr/bin/env python3
"""Native acceptance gate for an ACTION-scoped Strategic Number controller on attack-now."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.ast import SourceLocation
from Compiler.compiler import compile_source
from Compiler.ir import (
    AttackLifecycleObservation,
    NativeAttackLifecyclePlan,
    NativeAttackRule,
    StrategicNumberController,
    StrategicNumberControllerLayer,
    StrategicNumberControllerScope,
    StrategicNumberReleaseEvidence,
    StrategicNumberActionAttachment,
)
from Compiler.primitives.strategic_number_catalog import (
    default_strategic_number_inventory,
)
from Compiler.semantic.analyzer import parse_expression
from Compiler.semantic.strategic_number_arbitration import (
    build_strategic_number_arbitration_plan,
    lower_strategic_number_arbitration,
)


LIFECYCLE = (
    AttackLifecycleObservation.ADMISSION_REQUIRED,
    AttackLifecycleObservation.ISSUE,
    AttackLifecycleObservation.COMPLETION_UNOBSERVED,
    AttackLifecycleObservation.REASSESS_REQUIRED,
)


def _attack_plan() -> NativeAttackLifecyclePlan:
    rule = NativeAttackRule(
        identity="attack-now-owned",
        order=10,
        facts=(
            parse_expression(
                "(current-age >= feudal-age)",
                SourceLocation(1),
            ),
        ),
        actions=(
            parse_expression("(attack-now)", SourceLocation(1)),
        ),
        lifecycle=LIFECYCLE,
    )

    attachment = (
        StrategicNumberActionAttachment(
            identity="attack-surge-attachment",
            controller_identity="attack-surge",
            action_identity="attack-now",
            native_strategic_number_id=227,
            value=100,
            activation_state_name="sn-controller-attack-surge-active",
        ),
    )

    return NativeAttackLifecyclePlan(
        rules=(rule,),
    ).bind_strategic_number_action_attachments(
        attachment,
        owned_actions={"attack-surge": ("attack-now-owned", 0)},
    )


def _control_plan():
    class Profile:
        profile_id = "sn-action-controller-native-v1"
        strategic_number_modes = ()

    underlay = StrategicNumberController(
        identity="strategy-underlay",
        native_strategic_number_id=227,
        value=75,
        layer=StrategicNumberControllerLayer.STRATEGY,
        activation_guard="(current-age >= feudal-age)",
        owner=Profile.profile_id,
    )
    action = StrategicNumberController(
        identity="attack-surge",
        native_strategic_number_id=227,
        value=100,
        layer=StrategicNumberControllerLayer.ACTION,
        activation_guard="(current-age >= feudal-age)",
        release_guard="(current-age >= imperial-age)",
        scope=StrategicNumberControllerScope.ACTION_SCOPED,
        action_identity="attack-now",
        release_evidence=StrategicNumberReleaseEvidence.WORLD_WITNESS,
        owner=Profile.profile_id,
    )

    inventory = default_strategic_number_inventory()
    plan = build_strategic_number_arbitration_plan(
        Profile(),
        extra_controllers=(underlay, action),
    )
    lowering = lower_strategic_number_arbitration(
        plan,
        profile_id=Profile.profile_id,
        documented_native_ids=inventory.documented_ids,
        action_identities=frozenset({"attack-now"}),
    )
    if lowering.control_plan is None:
        raise SystemExit("ACTION controller lowering produced no native control plan")
    return plan, lowering.control_plan


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


def _rule_section(artifact: str, marker: str) -> str:
    if marker not in artifact:
        raise SystemExit(f"missing rule marker: {marker}")
    section = artifact.split(marker, 1)[1]
    next_marker = section.find("\n; Native ")
    if next_marker >= 0:
        section = section[:next_marker]
    return section


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    source = """
    demand marker {
        require (can-build house)
        action (build house)
        witness (building-type-count house >= 1)
        release (building-type-count house >= 1)
    }
    """

    plan, control_plan = _control_plan()
    attack_plan = _attack_plan()

    controller = plan.controller("attack-surge")
    activation_guard = (
        controller.activation_guard.source
        if hasattr(controller.activation_guard, "source")
        else controller.activation_guard
    )
    release_guard = (
        controller.release_guard.source
        if hasattr(controller.release_guard, "source")
        else controller.release_guard
    )
    if activation_guard is None or release_guard is None:
        raise SystemExit("ACTION controller lost activation or release guard")

    attachment = attack_plan.strategic_number_action_attachments[0]
    if attachment.controller_identity != "attack-surge":
        raise SystemExit("ACTION attachment lost its controller identity")
    if attachment.action_identity != "attack-now":
        raise SystemExit("ACTION attachment is not bound to attack-now")
    if attachment.owned_rule_identity != "attack-now-owned":
        raise SystemExit("ACTION attachment is not bound to the owned attack rule")
    if attachment.action_index != 0:
        raise SystemExit("ACTION attachment is not bound to action index 0")

    owned_rule = attack_plan.rules[0]
    if owned_rule.actions[attachment.action_index].head != "attack-now":
        raise SystemExit("owned action identity does not match attack-now")
    if attachment.native_strategic_number_id != controller.native_strategic_number_id:
        raise SystemExit("ACTION attachment native Strategic Number does not match its controller")
    if attachment.value != controller.value:
        raise SystemExit("ACTION attachment value does not match its controller")

    if activation_guard not in tuple(fact.source for fact in owned_rule.facts):
        raise SystemExit("attack-now ownership is missing the ACTION activation guard")

    first = compile_source(
        source,
        control_plan=control_plan,
        attack_plan=attack_plan,
    )
    second = compile_source(
        source,
        control_plan=control_plan,
        attack_plan=attack_plan,
    )
    if first != second:
        raise SystemExit("ACTION-controller artifact is non-deterministic")

    required_fragments = (
        "; Native attack lifecycle plan",
        "; Native attack rule: attack-now-owned",
        activation_guard,
        "(defconst sn-native-227 227)",
        "(set-strategic-number sn-native-227 75)",
        "(set-goal sn-controller-attack-surge-active 1)",
        "(set-strategic-number sn-native-227 100)",
        "(not (or (current-age >= feudal-age) (goal sn-controller-attack-surge-active 1)))",
        "; Native control rule: sn-controller-attack-surge-release",
        "(goal sn-controller-attack-surge-active 1)",
        release_guard,
        "(set-goal sn-controller-attack-surge-active 0)",
    )
    missing = tuple(fragment for fragment in required_fragments if fragment not in first)
    if missing:
        raise SystemExit(f"ACTION-controller artifact is missing fragments: {missing}")

    if first.count("(defconst sn-native-227 227)") != 1:
        raise SystemExit("native Strategic Number alias must be emitted exactly once")

    if first.count("(set-goal sn-controller-attack-surge-active 1)") != 1:
        raise SystemExit("ACTION controller activation transition must appear exactly once")
    if first.count("(set-strategic-number sn-native-227 100)") != 1:
        raise SystemExit("ACTION Strategic Number write must appear exactly once")
    if first.count("(attack-now)") != 1:
        raise SystemExit("ACTION fixture must emit exactly one attack-now action")

    attack_section = _rule_section(
        first,
        "; Native attack rule: attack-now-owned",
    )
    attack_lines = [line.strip() for line in attack_section.splitlines()]
    try:
        activation_index = attack_lines.index("(set-goal sn-controller-attack-surge-active 1)")
        sn_index = attack_lines.index("(set-strategic-number sn-native-227 100)")
        attack_index = attack_lines.index("(attack-now)")
    except ValueError as exc:
        raise SystemExit("ACTION attack rule is missing expected SN/action lines") from exc
    if sn_index != activation_index + 1:
        raise SystemExit(
            "ACTION controller activation was not emitted immediately before its Strategic Number write"
        )
    if attack_index != sn_index + 1:
        raise SystemExit(
            "ACTION Strategic Number write was not emitted immediately before attack-now"
        )
    if activation_guard not in attack_lines:
        raise SystemExit("ACTION activation guard is not attached to the owned attack rule")

    release_section = _rule_section(
        first,
        "; Native control rule: sn-controller-attack-surge-release",
    )
    if "(goal sn-controller-attack-surge-active 1)" not in release_section:
        raise SystemExit("ACTION release rule lost its active-state guard")
    if release_guard not in release_section:
        raise SystemExit("ACTION release rule lost its release witness")
    if "(set-goal sn-controller-attack-surge-active 0)" not in release_section:
        raise SystemExit("ACTION release rule does not clear the controller state")

    underlay_section = _rule_section(
        first,
        "; Native control rule: sn-controller-strategy-underlay-write",
    )
    expected_restore_guard = "(not (goal sn-controller-attack-surge-active 1))"
    if expected_restore_guard not in underlay_section:
        raise SystemExit(
            "ACTION release does not permit the strategy underlay to reassert"
        )
    if "(set-strategic-number sn-native-227 75)" not in underlay_section:
        raise SystemExit("ACTION release path lost the strategy underlay write")
    release_marker = first.index(
        "; Native control rule: sn-controller-attack-surge-release"
    )
    restore_marker = first.index(
        "; Native control rule: sn-controller-strategy-underlay-write"
    )
    if restore_marker <= release_marker:
        raise SystemExit("ACTION restoration rule was emitted before controller release")

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
        "underlay": {
            "identity": "strategy-underlay",
            "native_id": 227,
            "value": 75,
        },
        "action_controller": {
            "identity": "attack-surge",
            "native_id": 227,
            "value": 100,
            "activation_guard": activation_guard,
            "release_guard": release_guard,
            "action_identity": "attack-now",
        },
        "attachment": {
            "controller_identity": attachment.controller_identity,
            "action_identity": attachment.action_identity,
            "owned_rule_identity": attachment.owned_rule_identity,
            "action_index": attachment.action_index,
        },
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
            f"ACTION-controller native gate failed: finding_count={finding_count}",
            file=sys.stderr,
        )
        return 1

    print(
        "ACTION Strategic Number controller native zero-findings gate passed "
        f"(sha256={report['artifact_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
