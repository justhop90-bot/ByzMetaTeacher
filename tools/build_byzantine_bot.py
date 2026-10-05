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
    COMPILER_ARTIFACT,
    COMPILER_MANIFEST,
    PROMOTED_ARTIFACT,
    WovenRuntimeLineageResult,
    verify_woven_runtime_lineage,
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
    """Compile, verify compiler-rule conservation, and package woven runtime."""
    root = ROOT
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    compiler_artifact = output_dir / "Byzantine.compiler.per"
    compiler_manifest = output_dir / "Byzantine.compiler.manifest.json"
    runtime_artifact = output_dir / "Byzantine.runtime.per"
    runtime_manifest = output_dir / "Byzantine.runtime.manifest.json"
    root_runtime = root / PROMOTED_ARTIFACT

    civ_profile = ByzantineProfile.for_update_185872()
    effective = resolve_effective_civ(civ_profile)
    profile = build_byzantine_strategy(effective, include_water_continuity=True)

    first = compile_strategy_profile(profile, effective)
    second = compile_strategy_profile(profile, effective)
    if first != second:
        raise RuntimeError("canonical Byzantine compilation is not byte-deterministic")

    compiler_bytes = first.encode("utf-8")
    artifact_sha256 = hashlib.sha256(compiler_bytes).hexdigest()
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
            "byte_length": len(compiler_bytes),
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
    compiler_artifact.write_bytes(compiler_bytes)
    compiler_manifest.write_text(
        _canonical_json(compiler_manifest_payload) + "\n",
        encoding="utf-8",
    )

    if not root_runtime.is_file():
        raise RuntimeError(
            f"BYZ-LINEAGE-031: checked-in woven runtime artifact is missing at {root_runtime}"
        )

    lineage = verify_woven_runtime_lineage(repository_root=root)
    runtime_bytes = root_runtime.read_bytes()
    runtime_artifact.write_bytes(runtime_bytes)

    runtime_manifest_payload = {
        "schema": "byzantine-woven-runtime-1",
        "artifact_kind": "woven-runtime",
        "compiler": {
            "artifact_kind": "compiler",
            "path": COMPILER_ARTIFACT.as_posix(),
            "manifest_path": COMPILER_MANIFEST.as_posix(),
            "sha256": lineage.compiler_sha256,
            "source_revision": lineage.compiler_source_revision,
            "compiler_rule_count": lineage.compiler_rule_count,
        },
        "runtime": {
            "artifact_kind": "woven-runtime",
            "authoritative_path": PROMOTED_ARTIFACT.as_posix(),
            "packaged_path": "dist/byzantine/Byzantine.runtime.per",
            "sha256": lineage.runtime_sha256,
            "runtime_rule_count": lineage.runtime_rule_count,
            "compiler_rules_conserved": lineage.compiler_rules_conserved,
        },
        "assembly": {
            "model": "woven-rule-conservation",
            "compiler_order_owned": False,
            "runtime_order_owned_by": "checked-in Byzantine.per",
            "deterministic": True,
        },
    }
    runtime_manifest.write_text(
        _canonical_json(runtime_manifest_payload) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "compiler_artifact": str(compiler_artifact),
                "runtime_artifact": str(runtime_artifact),
                "authoritative_runtime": str(root_runtime),
                "compiler_sha256": lineage.compiler_sha256,
                "runtime_sha256": lineage.runtime_sha256,
                "compiler_rule_count": lineage.compiler_rule_count,
                "runtime_rule_count": lineage.runtime_rule_count,
                "compiler_rules_conserved": lineage.compiler_rules_conserved,
            },
            sort_keys=True,
        )
    )
    return runtime_artifact, runtime_manifest



def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    build(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
