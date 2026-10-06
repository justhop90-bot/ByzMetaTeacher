from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from LearnerAI.Compiler.semantic import assess_runtime_witness


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assess a Byzantine runtime witness record without inventing engine observations."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    record = json.loads(args.input.read_text(encoding="utf-8"))
    assessment = assess_runtime_witness(record)
    payload = json.dumps(assessment.to_dict(), indent=2, sort_keys=True) + "\n"

    if args.output is None:
        sys.stdout.write(payload)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
