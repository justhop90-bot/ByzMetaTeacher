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

    inventory = default_strategic_number_inventory()
    plan = build_strategic_number_arbitration_plan(
        Profile(),
        extra_controllers=(base, temporary),
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

    required = (
        "(defconst sn-native-227 227)",
        "(current-age >= feudal-age)",
        "(goal sn-controller-emergency-defense-active 1)",
        "(set-strategic-number sn-native-227 75)",
        "(set-strategic-number sn-native-227 25)",
        "(up-compare-sn sn-native-227 != 75)",
        "(up-compare-sn sn-native-227 != 25)",
    )
    for fragment in required:
        if fragment not in first:
            raise SystemExit(f"missing arbitration artifact fragment: {fragment}")

    if "(not (or (current-age >= feudal-age) (goal sn-controller-emergency-defense-active 1)))" not in first:
        raise SystemExit("underlay write is not suppressed across the temporary override lifetime")

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
