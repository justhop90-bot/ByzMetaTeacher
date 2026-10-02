#!/usr/bin/env python3
"""Build the deployable Byzantine .per artifact and deterministic manifest."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEARNER_AI = ROOT / "LearnerAI"
DIST = ROOT / "dist" / "byzantine"
ARTIFACT = DIST / "Byzantine.per"
MANIFEST = DIST / "manifest.json"
NATIVE_PARSER_REVISION = "3dfa2583b7c2ec36b85ccb421ebd0abe9ff276ba"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_revision() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip()


def _build_once():
    sys.path.insert(0, str(LEARNER_AI))
    from Compiler.bots.byzantine import build_byzantine_bot_profile
    from Compiler.clients.basilisk import ByzantineProfile, resolve_effective_civ
    from Compiler.clients.basilisk.compiler import compile_strategy_profile

    effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
    profile = build_byzantine_bot_profile(effective)
    artifact = compile_strategy_profile(profile, effective)
    return effective, profile, artifact


def main() -> int:
    first_effective, first_profile, first = _build_once()
    second_effective, second_profile, second = _build_once()

    first_bytes = first.encode("utf-8")
    second_bytes = second.encode("utf-8")
    if first_bytes != second_bytes:
        raise SystemExit("Byzantine build is not byte-deterministic")

    if first_effective.fingerprint != second_effective.fingerprint:
        raise SystemExit("EffectiveCivData fingerprint changed between deterministic builds")
    if first_profile.profile_id != second_profile.profile_id:
        raise SystemExit("Byzantine profile identity changed between deterministic builds")

    DIST.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_bytes(first_bytes)

    manifest = {
        "artifact": "Byzantine.per",
        "artifact_sha256": _sha256(first_bytes),
        "artifact_bytes": len(first_bytes),
        "profile_id": first_profile.profile_id,
        "civ_id": int(first_effective.civ_id),
        "patch": first_effective.patch.key,
        "effective_snapshot_fingerprint": first_effective.fingerprint,
        "demand_count": len(first_profile.demands),
        "strategic_number_mode_count": len(first_profile.strategic_number_modes),
        "compiler_revision": _git_revision(),
        "native_parser_revision": NATIVE_PARSER_REVISION,
    }
    MANIFEST.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"built {ARTIFACT}")
    print(f"sha256 {manifest['artifact_sha256']}")
    print(f"demands {manifest['demand_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
