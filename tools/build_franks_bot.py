#!/usr/bin/env python3
"""Package and attest the standalone native Franks Arabia bot."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Franks.per"
DEFAULT_OUTPUT_DIR = Path("dist/franks")
NATIVE_PARSER_REVISION = "3dfa2583b7c2ec36b85ccb421ebd0abe9ff276ba"

REQUIRED_FRAGMENTS = (
    "(can-research-with-escrow feudal-age)",
    "(can-research-with-escrow castle-age)",
    "(can-research-with-escrow imperial-age)",
    "(train knight-line)",
    "(train frank-throwing-axeman)",
    "(train frank-mounted-crossbowman)",
    "(research ri-ordonnance-companies)",
    "(train battering-ram-line)",
    "(train trebuchet)",
    "(attack-now)",
)


def _git_revision(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("Franks packaging requires a Git checkout") from exc
    revision = result.stdout.strip()
    if len(revision) != 40:
        raise RuntimeError(f"unexpected Git revision: {revision!r}")
    return revision


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def build(output_dir: Path) -> tuple[Path, Path]:
    """Create a byte-identical test artifact and a reproducibility manifest.

    Franks.per is intentionally hand-authored native AI source in this first
    vertical slice. This builder packages it without rewriting native rule order.
    It does not pretend the native source was generated from Byzantine-scoped
    GameData, which is not a valid factual basis for Franks.
    """
    source = SOURCE.read_text(encoding="utf-8")
    if not source.endswith("\n"):
        raise RuntimeError("Franks.per must end with exactly one newline")
    if any(fragment not in source for fragment in REQUIRED_FRAGMENTS):
        missing = [fragment for fragment in REQUIRED_FRAGMENTS if fragment not in source]
        raise RuntimeError(f"Franks.per is missing required strategy behaviors: {missing}")
    rule_count = source.count("(defrule")
    line_count = len(source.splitlines())
    if rule_count < 80:
        raise RuntimeError(f"Franks.per unexpectedly has only {rule_count} rules")
    for forbidden in ("cataphract", "varangian-guard", "ri-bearded-axe", "cavalry-archer-line"):
        if forbidden in source.lower():
            raise RuntimeError(f"Franks.per contains stale or foreign strategy material: {forbidden}")

    # Re-read the canonical source rather than mutating it; repeated package builds
    # must preserve exact bytes, comments, and source-order semantics.
    second = SOURCE.read_text(encoding="utf-8")
    if source != second:
        raise RuntimeError("canonical Franks source changed during packaging")

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / "Franks.per"
    manifest_path = output_dir / "Franks.manifest.json"
    artifact_path.write_text(source, encoding="utf-8", newline="")

    source_sha256 = _sha256_text(source)
    artifact_sha256 = _sha256_text(artifact_path.read_text(encoding="utf-8"))
    if artifact_sha256 != source_sha256:
        raise RuntimeError("packaged Franks artifact differs from canonical source")

    manifest = {
        "schema": "franks-arabia-native-bot-v1",
        "civilization": "Franks",
        "map_policy": ["ARABIA", "STANDARD_LAND"],
        "game_patch": "AOE2DE:185872:2026-09-22",
        "source_path": "Franks.per",
        "source_sha256": source_sha256,
        "artifact_sha256": artifact_sha256,
        "artifact_line_count": line_count,
        "artifact_rule_count": rule_count,
        "artifact_byte_length": len(source.encode("utf-8")),
        "compiler_source_revision": _git_revision(ROOT),
        "native_parser_revision": NATIVE_PARSER_REVISION,
        "build_mode": "byte-preserving native source package",
        "determinism": {
            "second_read_equal": True,
            "artifact_sha256_matches_source": True,
        },
        "runtime_status": "NOT_YET_RUNTIME_TESTED",
    }
    manifest_path.write_text(_canonical_json(manifest) + "\n", encoding="utf-8", newline="")
    return artifact_path, manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    artifact_path, manifest_path = build(args.output_dir)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(json.dumps({
        "artifact": str(artifact_path),
        "manifest": str(manifest_path),
        "artifact_sha256": manifest["artifact_sha256"],
        "rule_count": manifest["artifact_rule_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
