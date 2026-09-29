#!/usr/bin/env python3
"""Native acceptance gate for the typed production provider-readiness seam."""
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

FIXTURE = Path(__file__).parent / "fixtures" / "production_provider_readiness.perdsl"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    source = FIXTURE.read_text(encoding="utf-8")
    first = compile_source(source)
    second = compile_source(source)

    if first != second:
        raise SystemExit(
            "production provider-readiness fixture produced non-deterministic artifacts"
        )

    required_fragments = (
        "(up-train-site-ready c: 93)",
        "(can-train spearman)",
        "(train spearman)",
    )
    missing = [fragment for fragment in required_fragments if fragment not in first]
    if missing:
        raise SystemExit(
            "production provider-readiness fixture is missing expected native output: "
            + ", ".join(missing)
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(first, encoding="utf-8")

    native_report = args.report.with_name(args.report.stem + "-native.json")
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("assert_native_zero.py")),
            str(args.output),
            "--report",
            str(native_report),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    report = {
        "fixture_source_sha256": hashlib.sha256(
            source.encode("utf-8")
        ).hexdigest(),
        "artifact_sha256": hashlib.sha256(first.encode("utf-8")).hexdigest(),
        "required_fragments": required_fragments,
        "native_gate_returncode": result.returncode,
        "native_report": str(native_report),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "provider_readiness_status": "OPEN",
        "provider_readiness_reason": (
            "AIRef/UserPatch documents up-train-site-ready as a training-site "
            "readiness/availability fact; exact current DE runtime behavior under "
            "busy providers and queued work remains unverified."
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
        return result.returncode or 1

    print(
        "production provider-readiness native artifact gate passed "
        f"(sha256={report['artifact_sha256']}; runtime=OPEN)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
