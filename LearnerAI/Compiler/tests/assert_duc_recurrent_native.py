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


SOURCE = """(defrule
    (true)
    =>
    (set-goal duc-gate 0)
)
(defrule
    (goal duc-gate 1)
    =>
    (up-find-local c: 83 c: 1)
)
(defrule
    (true)
    =>
    (up-find-local c: 83 c: 1)
)
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

    with tempfile.TemporaryDirectory() as tmp:
        entrypoint = Path(tmp) / "duc-recurrent.per"
        entrypoint.write_text(SOURCE, encoding="utf-8")
        execution = analyze_effective_rules(
            SourceGraphResolver().resolve(
                SourceGraphRequest(entrypoint=entrypoint)
            )
        )

    recurrent = analyze_recurrent_execution(execution)
    if recurrent.status_for_rule(2) is not RecurrentExecutionStatus.NEVER_RUNNABLE:
        raise SystemExit("rule 2 must be proven NEVER_RUNNABLE")

    duc = analyze_duc(
        execution,
        recurrent_execution=recurrent,
    )
    if tuple(search.provenance.rule_order for search in duc.searches) != (3,):
        raise SystemExit(
            "DUC recurrent suppression failed: only live rule 3 may seed search state"
        )
    if duc.final_state.local_list.current_generation is None:
        raise SystemExit("live DUC rule did not produce the expected search generation")

    artifact = compile_source(SOURCE)
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
        "recurrent_status_rule_2": recurrent.status_for_rule(2).value,
        "duc_search_rule_orders": [search.provenance.rule_order for search in duc.searches],
        "native_validator_exit_code": result.returncode,
        "finding_count": finding_count,
        "findings": findings,
        "assertion": (
            "Rule 2 is emitted syntactically but is proven NEVER_RUNNABLE by the "
            "recurrent semantic interpreter and therefore does not seed DUC state; "
            "rule 3 remains executable and seeds the DUC list."
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
