#!/usr/bin/env python3
"""Native zero-findings gate for posture/age Strategic Number mode synthesis."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_castle_strategy,
    compile_strategy_profile,
)
from Compiler.ir.civ_profile import resolve_effective_civ


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
        raise SystemExit(
            f"native validator did not return JSON: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise SystemExit("native validator JSON root must be an object")
    return result, payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    effective = resolve_effective_civ(
        ByzantineProfile.for_update_185872()
    )
    profile = build_byzantine_castle_strategy(effective)

    first = compile_strategy_profile(profile, effective)
    second = compile_strategy_profile(profile, effective)
    if first != second:
        raise SystemExit(
            "posture/age Strategic Number mode artifact is non-deterministic"
        )

    expected_aliases = (
        "(defconst sn-native-4 4)",
        "(defconst sn-native-227 227)",
    )
    for alias in expected_aliases:
        if alias not in first:
            raise SystemExit(f"missing native Strategic Number alias: {alias}")

    expected_age_modes = (
        ("dark-age", 3),
        ("feudal-age", 5),
        ("castle-age", 8),
        ("imperial-age", 12),
    )
    for age_name, value in expected_age_modes:
        write = f"(set-strategic-number sn-native-4 {value})"
        drift = f"(up-compare-sn sn-native-4 != {value})"
        guard = f"(current-age == {age_name})"
        if first.count(write) != 1:
            raise SystemExit(
                f"expected exactly one age-mode write for {age_name}: {write}"
            )
        if drift not in first or guard not in first:
            raise SystemExit(
                f"missing deterministic age-mode guard for {age_name}"
            )

    expected_posture_modes = (
        (1, 50),
        (2, 50),
        (3, 75),
        (4, 75),
    )
    posture_write_counts = {50: 0, 75: 0}
    for posture_value, target in expected_posture_modes:
        write = f"(set-strategic-number sn-native-227 {target})"
        drift = f"(up-compare-sn sn-native-227 != {target})"
        posture = f"(goal strategy-posture {posture_value})"
        posture_write_counts[target] += 1
        if posture not in first:
            raise SystemExit(
                f"missing strategy-posture guard for posture value {posture_value}"
            )
        if drift not in first:
            raise SystemExit(
                f"missing drift guard for posture value {posture_value}"
            )
    for target, expected_count in posture_write_counts.items():
        write = f"(set-strategic-number sn-native-227 {target})"
        if first.count(write) != expected_count:
            raise SystemExit(
                f"expected {expected_count} guarded posture-mode writes for {target}: {write}"
            )
    if first.count("(current-age >= feudal-age)") < 4:
        raise SystemExit(
            "expected all posture-driven SN modes to be gated to Feudal Age or later"
        )

    forbidden_initializers = (
        "(set-strategic-number sn-native-4 0)",
        "(set-strategic-number sn-native-227 0)",
    )
    for initializer in forbidden_initializers:
        if initializer in first:
            raise SystemExit(
                f"native Strategic Number received compiler-owned initialization: {initializer}"
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(first, encoding="utf-8")

    result, payload = _validate_native(args.output)
    finding_count = payload.get("finding_count")
    findings = payload.get("findings")

    report = {
        "artifact": str(args.output.resolve()),
        "artifact_sha256": hashlib.sha256(
            first.encode("utf-8")
        ).hexdigest(),
        "fixture_profile": profile.profile_id,
        "strategic_number_modes": [
            {
                "native_id": mode.native_strategic_number_id,
                "identity": mode.identity,
                "value": mode.value,
                "minimum_age": mode.minimum_age.value,
                "maximum_age": (
                    None if mode.maximum_age is None else mode.maximum_age.value
                ),
                "postures": [posture.value for posture in mode.postures],
                "reassertion_policy": mode.reassertion_policy.value,
            }
            for mode in profile.strategic_number_modes
        ],
        "validator_exit_code": result.returncode,
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
            "posture/age Strategic Number native gate failed: "
            f"finding_count={finding_count}",
            file=sys.stderr,
        )
        return 1

    print(
        "posture/age Strategic Number native zero-findings gate passed "
        f"(sha256={report['artifact_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
