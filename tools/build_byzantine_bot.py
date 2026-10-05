#!/usr/bin/env python3
"""Build the canonical Byzantine compiler -> runtime -> promoted artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from LearnerAI.Compiler.clients.basilisk import (  # noqa: E402
    ByzantineProfile,
    build_byzantine_strategy,
    compile_strategy_profile,
)
from LearnerAI.Compiler.ir.civ_profile import resolve_effective_civ  # noqa: E402
from LearnerAI.Compiler.artifacts.lineage import (  # noqa: E402
    PROMOTED_ARTIFACT,
    PROMOTION_MANIFEST,
    RUNTIME_ARTIFACT,
    RUNTIME_MANIFEST,
    verify_byzantine_artifact_lineage,
)
from tools.assemble_byzantine_runtime import assemble_byzantine_runtime  # noqa: E402
from tools.promote_byzantine_runtime import promote_byzantine_runtime  # noqa: E402

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


def build(output_dir: Path = DEFAULT_OUTPUT_DIR) -> tuple[Path, Path]:
    """Compile, assemble, promote, and cryptographically verify Byzantine."""
    root = ROOT
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    compiler_artifact = output_dir / "Byzantine.compiler.per"
    compiler_manifest = output_dir / "Byzantine.compiler.manifest.json"
    overlay_artifact = root / "runtime/byzantine/Byzantine.runtime-overlay.per"
    if not overlay_artifact.is_file():
        raise RuntimeError(
            "BYZ-ASSEMBLY-003: canonical Byzantine runtime overlay is missing at "
            f"{overlay_artifact}"
        )
    if not (root / "runtime/byzantine/Byzantine.runtime-overlay.json").is_file():
        raise RuntimeError(
            "BYZ-ASSEMBLY-003: canonical Byzantine runtime overlay manifest is missing"
        )

    civ_profile = ByzantineProfile.for_update_185872()
    effective = resolve_effective_civ(civ_profile)
    profile = build_byzantine_strategy(effective, include_water_continuity=True)

    first = compile_strategy_profile(profile, effective)
    second = compile_strategy_profile(profile, effective)
    if first != second:
        raise RuntimeError("canonical Byzantine compilation is not byte-deterministic")

    artifact_sha256 = _sha256_text(first)
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

    compiler_manifest_payload = {
        "schema": "byzantine-compiler-artifact-1",
        "artifact_kind": "compiler",
        "artifact": {
            "path": "dist/byzantine/Byzantine.compiler.per",
            "manifest_path": "dist/byzantine/Byzantine.compiler.manifest.json",
            "sha256": artifact_sha256,
            "byte_length": len(first.encode("utf-8")),
            "line_count": len(first.splitlines()),
            "rule_count": first.count("(defrule"),
        },
        "compiler": {
            "source_revision": _git_revision(root),
            "entrypoint": "compile_strategy_profile",
        },
        "strategy": {
            "profile_entrypoint": "ByzantineProfile.for_update_185872",
            "strategy_entrypoint": "build_byzantine_strategy",
            "profile_id": profile.profile_id,
        },
        "effective_civ": {
            "civilization": effective.civ_name,
            "civ_id": int(effective.civ_id),
            "patch_key": effective.patch.key,
            "snapshot_fingerprint": effective.fingerprint,
        },
        "native_parser": {
            "name": "aoe2-ai-parser",
            "revision": NATIVE_PARSER_REVISION,
        },
        "determinism": {
            "compile_repeat_equal": True,
            "hash_recomputed": True,
        },
    }
    compiler_artifact.write_text(first, encoding="utf-8", newline="")
    compiler_manifest.write_text(
        _canonical_json(compiler_manifest_payload) + "\n",
        encoding="utf-8",
        newline="",
    )

    assemble_byzantine_runtime(repository_root=root, output_dir=output_dir)
    promote_byzantine_runtime(repository_root=root)
    result = verify_byzantine_artifact_lineage(repository_root=root)
    if not result.root_matches_runtime:
        raise RuntimeError("BYZ-PROMOTE-001: promoted Byzantine.per diverges from runtime")

    print(
        json.dumps(
            {
                "compiler_artifact": str(compiler_artifact),
                "runtime_artifact": str(root / RUNTIME_ARTIFACT),
                "promoted_artifact": str(root / PROMOTED_ARTIFACT),
                "promotion_manifest": str(root / PROMOTION_MANIFEST),
                "compiler_sha256": result.compiler_sha256,
                "runtime_sha256": result.runtime_sha256,
                "promoted_sha256": result.promoted_sha256,
                "lineage_verified": True,
            },
            sort_keys=True,
        )
    )
    return root / PROMOTED_ARTIFACT, root / PROMOTION_MANIFEST


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    build(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
