#!/usr/bin/env python3
"""CI acceptance gate: an emitted .per must have exactly zero native findings."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _write_report(
    path: Path | None,
    *,
    artifact: Path,
    result: subprocess.CompletedProcess[str],
    payload: object | None,
    parse_error: str | None = None,
) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "artifact": str(artifact),
        "validator_exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "json": payload,
        "json_parse_error": parse_error,
    }
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    artifact = Path(args.artifact).resolve()
    if not artifact.is_file():
        print(f"artifact does not exist: {artifact}", file=sys.stderr)
        if args.report is not None:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                json.dumps(
                    {
                        "artifact": str(artifact),
                        "validator_exit_code": None,
                        "stdout": "",
                        "stderr": f"artifact does not exist: {artifact}",
                        "json": None,
                        "json_parse_error": None,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        return 2

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
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)

    payload = None
    parse_error = None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        parse_error = str(exc)

    _write_report(
        args.report,
        artifact=artifact,
        result=result,
        payload=payload,
        parse_error=parse_error,
    )

    if result.returncode != 0:
        print(
            f"native validator exited {result.returncode}: {artifact}",
            file=sys.stderr,
        )
        return result.returncode or 1

    if parse_error is not None:
        print(
            f"native validator did not return JSON: {parse_error}",
            file=sys.stderr,
        )
        return 2

    if not isinstance(payload, dict):
        print(
            "native validator JSON root must be an object",
            file=sys.stderr,
        )
        return 2

    finding_count = payload.get("finding_count")
    findings = payload.get("findings")

    if finding_count != 0 or findings != []:
        print(
            f"native zero-findings gate failed: finding_count={finding_count}",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
