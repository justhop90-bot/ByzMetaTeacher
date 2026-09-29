#!/usr/bin/env python3
"""Native acceptance gate for recurrent-execution suppression of impossible DUC state effects."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.compiler import compile_source
from Compiler.semantic.duc import analyze_duc
from Compiler.semantic.recurrent_execution import (
    RecurrentExecutionStatus,
    analyze_recurrent_execution,
)
from Compiler.semantic.rule_execution import analyze_effective_rules
from Compiler.source_graph import SourceGraphRequest, SourceGraphResolver


SOURCE = """
demand impossible-duc {
    require (goal duc-gate = 1)
    action (up-find-local c: 83 c: 1)
    witness (goal duc-gate = 1)
    release (goal duc-gate = 1)
}

demand live-duc {
    require (can-build castle)
    action (up-find-local c: 83 c: 1)
    witness (building-type-count castle > 0)
    release (building-type-count castle > 0)
}
"""



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

    artifact = compile_source(SOURCE)

    with tempfile.TemporaryDirectory() as tmp:
        entrypoint = Path(tmp) / "compiled.per"
        entrypoint.write_text(artifact, encoding="utf-8")
        execution = analyze_effective_rules(
            SourceGraphResolver().resolve(
                SourceGraphRequest(entrypoint=entrypoint)
            )
        )

    recurrent = analyze_recurrent_execution(execution)
    never_runnable = tuple(
        rule_order
        for rule_order, status in recurrent.statuses
        if status is RecurrentExecutionStatus.NEVER_RUNNABLE
    )
    if not never_runnable:
        raise SystemExit("compiled artifact did not produce any NEVER_RUNNABLE recurrent rule")

    duc = analyze_duc(
        execution,
        recurrent_execution=recurrent,
    )
    search_orders = tuple(search.provenance.rule_order for search in duc.searches)
    if len(search_orders) != 1:
        raise SystemExit(
            f"DUC recurrent suppression failed: expected one live search, got {search_orders}"
        )
    if duc.final_state.local_list.current_generation is None:
        raise SystemExit("live DUC rule did not produce the expected search generation")
    if artifact.count("(up-find-local c: 83 c: 1)") != 2:
        raise SystemExit("compiled artifact did not retain both native DUC rule bodies")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(artifact, encoding="utf-8")

    result, payload = _validate_native(args.output)
    finding_count = payload.get("finding_count")
    findings = payload.get("findings")

    report = {
        "artifact": str(args.output.resolve()),
        "source_sha256": hashlib.sha256(SOURCE.encode("utf-8")).hexdigest(),
        "artifact_sha256": hashlib.sha256(artifact.encode("utf-8")).hexdigest(),
        "never_runnable_rule_orders": list(never_runnable),
        "duc_search_rule_orders": list(search_orders),
        "native_validator_exit_code": result.returncode,
        "finding_count": finding_count,
        "findings": findings,
        "assertion": (
            "The emitted .per is accepted by the native parser, while the same emitted "
            "artifact proves a NEVER_RUNNABLE recurrent rule whose DUC mutation is excluded "
            "from semantic state transfer; the live DUC rule remains the sole search-state writer."
        ),
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
            f"DUC recurrent native gate failed: finding_count={finding_count}",
            file=sys.stderr,
        )
        return 1

    print(
        "DUC recurrent execution/native zero-findings gate passed "
        f"(sha256={report['artifact_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
