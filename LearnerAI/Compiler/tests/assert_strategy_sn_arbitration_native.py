#!/usr/bin/env python3
"""Native acceptance gate for Strategic Number controller arbitration."""
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
    StrategicNumberController,
    StrategicNumberControllerLayer,
    StrategicNumberControllerScope,
    StrategicNumberReleaseEvidence,
)
from Compiler.primitives.strategic_number_catalog import (
    default_strategic_number_inventory,
)
from Compiler.semantic.strategic_number_arbitration import (
    build_strategic_number_arbitration_plan,
    lower_strategic_number_arbitration,
)


def _lint(artifact: Path) -> dict[str, object]:
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
    if result.returncode != 0:
        raise SystemExit(
            f"native validator exited {result.returncode}: {result.stderr}"
        )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    class Profile:
        profile_id = "sn-arbitration-native-v1"
        strategic_number_modes = ()

    base = StrategicNumberController(
        identity="strategy-base",
        native_strategic_number_id=227,
        value=75,
        layer=StrategicNumberControllerLayer.STRATEGY,
        activation_guard="(current-age >= feudal-age)",
        owner=Profile.profile_id,
    )
    temporary = StrategicNumberController(
        identity="emergency-defense",
        native_strategic_number_id=227,
        value=25,
        layer=StrategicNumberControllerLayer.TEMPORARY,
        activation_guard="(current-age >= feudal-age)",
        release_guard="(current-age >= imperial-age)",
        scope=StrategicNumberControllerScope.UNTIL_RELEASE,
        release_evidence=StrategicNumberReleaseEvidence.WORLD_WITNESS,
        owner=Profile.profile_id,
    )
    recovery = StrategicNumberController(
        identity="recovery-override",
        native_strategic_number_id=227,
        value=100,
        layer=StrategicNumberControllerLayer.RECOVERY,
        activation_guard="(current-age >= castle-age)",
        release_guard="(current-age >= imperial-age)",
        scope=StrategicNumberControllerScope.UNTIL_RELEASE,
        release_evidence=StrategicNumberReleaseEvidence.WORLD_WITNESS,
        owner=Profile.profile_id,
    )

    inventory = default_strategic_number_inventory()
    plan = build_strategic_number_arbitration_plan(
        Profile(),
        extra_controllers=(base, temporary, recovery),
    )
    lowered = lower_strategic_number_arbitration(
        plan,
        profile_id=Profile.profile_id,
        documented_native_ids=inventory.documented_ids,
    )
    if lowered.control_plan is None:
        raise SystemExit("arbitration lowering produced no native control plan")

    source = """
        demand bootstrap {
            require (can-build house)
            action (build house)
            witness (building-type-count house >= 1)
            release (building-type-count house >= 1)
        }
    """
    first = compile_source(source, control_plan=lowered.control_plan)
    second = compile_source(source, control_plan=lowered.control_plan)
    if first != second:
        raise SystemExit("Strategic Number arbitration artifact is non-deterministic")

    activation_rule_marker = "; Native control rule: sn-controller-emergency-defense-activate"
    if activation_rule_marker not in first:
        raise SystemExit("temporary SN activation rule is missing")
    activation_section = first.split(activation_rule_marker, 1)[1]
    next_marker = activation_section.find("\n; Native ")
    if next_marker >= 0:
        activation_section = activation_section[:next_marker]
    if "(up-compare-sn sn-native-227 != 25)" in activation_section:
        raise SystemExit(
            "temporary SN activation incorrectly depends on native value drift"
        )
    activation_actions = [
        line.strip()
        for line in activation_section.splitlines()
        if line.strip().startswith("(")
    ]
    try:
        activation_index = activation_actions.index(
            "(set-goal sn-controller-emergency-defense-active 1)"
        )
        write_index = activation_actions.index(
            "(set-strategic-number sn-native-227 25)"
        )
    except ValueError as exc:
        raise SystemExit(
            "temporary SN activation rule is missing latch/write actions"
        ) from exc
    if write_index != activation_index + 1:
        raise SystemExit(
            "temporary SN activation must latch ownership immediately before its SN write"
        )

    controller_orders = (
        (
            "recovery-override",
            (
                "; Native control rule: sn-controller-recovery-override-activate",
                "; Native control rule: sn-controller-recovery-override-release",
                "; Native control rule: sn-controller-recovery-override-rearm",
                "; Native control rule: sn-controller-recovery-override-steady",
            ),
        ),
        (
            "emergency-defense",
            (
                "; Native control rule: sn-controller-emergency-defense-activate",
                "; Native control rule: sn-controller-emergency-defense-release",
                "; Native control rule: sn-controller-emergency-defense-rearm",
                "; Native control rule: sn-controller-emergency-defense-steady",
            ),
        ),
    )
    controller_order_positions = {}
    for identity, markers in controller_orders:
        positions = []
        for marker in markers:
            if marker not in first:
                raise SystemExit(f"missing transient controller rule marker: {marker}")
            positions.append(first.index(marker))
        if not positions[0] < positions[1] < positions[2] < positions[3]:
            raise SystemExit(
                f"{identity} controller must emit activate -> release -> rearm -> steady order"
            )
        controller_order_positions[identity] = positions
    if controller_order_positions["recovery-override"][3] >= controller_order_positions["emergency-defense"][0]:
        raise SystemExit(
            "higher-precedence recovery controller must emit before the temporary controller"
        )

    recovery_activation_marker = (
        "; Native control rule: sn-controller-recovery-override-activate"
    )
    recovery_activation = first.split(recovery_activation_marker, 1)[1]
    next_marker = recovery_activation.find("\n; Native ")
    if next_marker >= 0:
        recovery_activation = recovery_activation[:next_marker]
    if "(goal sn-controller-recovery-override-release-block 0)" not in recovery_activation:
        raise SystemExit("recovery activation is missing its release-block guard")

    recovery_release_marker = (
        "; Native control rule: sn-controller-recovery-override-release"
    )
    recovery_release = first.split(recovery_release_marker, 1)[1]
    next_marker = recovery_release.find("\n; Native ")
    if next_marker >= 0:
        recovery_release = recovery_release[:next_marker]
    recovery_release_actions = [
        line.strip()
        for line in recovery_release.splitlines()
        if line.strip().startswith("(")
    ]
    try:
        active_release_index = recovery_release_actions.index(
            "(set-goal sn-controller-recovery-override-active 0)"
        )
        block_release_index = recovery_release_actions.index(
            "(set-goal sn-controller-recovery-override-release-block 1)"
        )
    except ValueError as exc:
        raise SystemExit(
            "recovery release must clear active ownership and latch the release block"
        ) from exc
    if block_release_index != active_release_index + 1:
        raise SystemExit(
            "recovery release must clear active ownership before latching rearm block"
        )

    recovery_rearm_marker = (
        "; Native control rule: sn-controller-recovery-override-rearm"
    )
    recovery_rearm = first.split(recovery_rearm_marker, 1)[1]
    next_marker = recovery_rearm.find("\n; Native ")
    if next_marker >= 0:
        recovery_rearm = recovery_rearm[:next_marker]
    if "(not (current-age >= castle-age))" not in recovery_rearm:
        raise SystemExit(
            "recovery rearm must wait for the activation guard to become false"
        )
    if "(goal sn-controller-recovery-override-release-block 1)" not in recovery_rearm:
        raise SystemExit("recovery rearm is missing its release-block latch")
    if "(set-goal sn-controller-recovery-override-release-block 0)" not in recovery_rearm:
        raise SystemExit("recovery rearm must clear the release-block latch")

    required = (
        "(defconst sn-native-227 227)",
        "(current-age >= feudal-age)",
        "(goal sn-controller-emergency-defense-active 1)",
        "(set-strategic-number sn-native-227 75)",
        "(set-strategic-number sn-native-227 25)",
        "(set-strategic-number sn-native-227 100)",
        "(up-compare-sn sn-native-227 != 75)",
        "(up-compare-sn sn-native-227 != 25)",
        "(up-compare-sn sn-native-227 != 100)",
        "(goal sn-controller-emergency-defense-release-block 0)",
        "(goal sn-controller-recovery-override-release-block 0)",
    )
    for fragment in required:
        if fragment not in first:
            raise SystemExit(f"missing arbitration artifact fragment: {fragment}")

    expected_underlay_guard = "(not (goal sn-controller-emergency-defense-active 1))"
    if expected_underlay_guard not in first:
        raise SystemExit(
            "temporary release does not expose the strategy underlay reassertion guard"
        )
    stale_underlay_guard = (
        "(not (or (current-age >= feudal-age) "
        "(goal sn-controller-emergency-defense-active 1)))"
    )
    if stale_underlay_guard in first:
        raise SystemExit(
            "temporary activation eligibility still suppresses the underlay after release"
        )

    if "(set-strategic-number sn-native-227 0)" in first:
        raise SystemExit("native Strategic Number received compiler-owned zero initialization")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(first, encoding="utf-8")

    payload = _lint(args.output)
    report = {
        "artifact": str(args.output.resolve()),
        "artifact_sha256": hashlib.sha256(first.encode("utf-8")).hexdigest(),
        "finding_count": payload.get("finding_count"),
        "findings": payload.get("findings"),
        "controllers": [
            {
                "identity": controller.identity,
                "native_id": controller.native_strategic_number_id,
                "value": controller.value,
                "layer": controller.layer.value,
                "priority": controller.priority,
            }
            for controller in plan.controllers
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if payload.get("finding_count") != 0 or payload.get("findings") != []:
        raise SystemExit(
            "Strategic Number arbitration native gate failed: "
            f"finding_count={payload.get('finding_count')}"
        )

    print(
        "Strategic Number arbitration native zero-findings gate passed "
        f"(sha256={report['artifact_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
