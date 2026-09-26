from __future__ import annotations

import argparse
import json
from pathlib import Path

def load_snapshots(root: Path) -> list[tuple[Path, dict[str, object]]]:
    snapshots = []
    for path in sorted(root.rglob("native-support-replay.json")):
        snapshots.append((path, json.loads(path.read_text(encoding="utf-8"))))
    return snapshots

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    snapshots = load_snapshots(args.root)
    if len(snapshots) != 9:
        raise AssertionError(f"expected 9 cross-platform snapshots, found {len(snapshots)}")
    reference_path, reference = snapshots[0]
    reference_fixtures = reference["fixtures"]
    for path, snapshot in snapshots[1:]:
        if snapshot["fixtures"] != reference_fixtures:
            for name in sorted(reference_fixtures):
                if snapshot["fixtures"].get(name) != reference_fixtures.get(name):
                    raise AssertionError(
                        f"cross-platform determinism mismatch for {name}: "
                        f"{reference_path} != {path}"
                    )
            raise AssertionError(f"cross-platform determinism mismatch: {reference_path} != {path}")
    print(
        f"verified {len(snapshots)} Python/OS snapshots with identical "
        "diagnostics, support-state sequences, and artifact hashes"
    )

if __name__ == "__main__":
    main()
