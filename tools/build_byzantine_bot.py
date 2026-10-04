#!/usr/bin/env python3
"""Build the canonical compiler-produced Byzantine Core v1 artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from LearnerAI.Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_strategy,
    compile_strategy_profile,
)
from LearnerAI.Compiler.ir.civ_profile import resolve_effective_civ

NATIVE_PARSER_REVISION = "3dfa2583b7c2ec36b85ccb421ebd0abe9ff276ba"
DEFAULT_OUTPUT_DIR = Path("dist/byzantine")


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
        raise RuntimeError("canonical Byzantine build requires a Git checkout") from exc
    revision = result.stdout.strip()
    if len(revision) != 40:
        raise RuntimeError(f"unexpected Git revision: {revision!r}")
    return revision


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def build(output_dir: Path) -> tuple[Path, Path]:
    root = Path(__file__).resolve().parents[1]
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    civ_profile = ByzantineProfile.for_update_185872()
    effective = resolve_effective_civ(civ_profile)
    profile = build_byzantine_strategy(effective, include_water_continuity=True)

    first = compile_strategy_profile(profile, effective)
    second = compile_strategy_profile(profile, effective)
    if first != second:
        raise RuntimeError("canonical Byzantine compilation is not byte-deterministic")

    artifact_sha256 = _sha256_text(first)
    artifact_path = output_dir / "Byzantine.per"
    manifest_path = output_dir / "Byzantine.manifest.json"

    build_input_identity = {
        "profile_entrypoint": "ByzantineProfile.for_update_185872",
        "strategy_entrypoint": "build_byzantine_strategy",
        "compiler_entrypoint": "compile_strategy_profile",
        "include_water_continuity": True,
        "profile_id": profile.profile_id,
        "civilization": effective.civ_name,
        "civ_id": int(effective.civ_id),
        "patch_key": effective.patch.key,
        "effective_snapshot_fingerprint": effective.fingerprint,
    }

    manifest = {
        "schema": "byzantine-core-v1-build-1",
        "profile_id": profile.profile_id,
        "civilization": effective.civ_name,
        "civ_id": int(effective.civ_id),
        "patch_key": effective.patch.key,
        "effective_snapshot_fingerprint": effective.fingerprint,
        "artifact_sha256": artifact_sha256,
        "artifact_line_count": len(first.splitlines()),
        "artifact_rule_count": first.count("(defrule"),
        "artifact_byte_length": len(first.encode("utf-8")),
        "compiler_source_revision": _git_revision(root),
        "build_input_identity": build_input_identity,
        "native_parser_revision": NATIVE_PARSER_REVISION,
        "determinism": {
            "second_compile_equal": True,
            "artifact_sha256_matches_manifest": True,
        },
    }

    artifact_path.write_text(first, encoding="utf-8")
    manifest_path.write_text(_canonical_json(manifest) + "\n", encoding="utf-8")
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
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
