#!/usr/bin/env python3
"""CI acceptance gate: an emitted .per must have exactly zero native findings."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: assert_native_zero.py <artifact>", file=sys.stderr)
        return 2

    artifact = Path(sys.argv[1]).resolve()
    if not artifact.is_file():
        print(f"artifact does not exist: {artifact}", file=sys.stderr)
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

    if result.returncode != 0:
        print(
            f"native validator exited {result.returncode}: {artifact}",
            file=sys.stderr,
        )
        return result.returncode or 1

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"native validator did not return JSON: {exc}", file=sys.stderr)
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
