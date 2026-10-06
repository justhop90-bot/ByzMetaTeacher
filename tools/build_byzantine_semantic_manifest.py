from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from LearnerAI.Compiler.semantic import build_semantic_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description='Build the deterministic semantic shadow for an AoE2 .per artifact.')
    parser.add_argument('--input', type=Path, default=ROOT / 'Byzantine.per')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()

    manifest = build_semantic_manifest(args.input)
    payload = manifest.to_json()
    if args.output is None:
        sys.stdout.write(payload)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
