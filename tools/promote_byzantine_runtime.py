#!/usr/bin/env python3
"""Atomically promote a verified Byzantine runtime artifact."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from LearnerAI.Compiler.artifacts.lineage import (
    COMPILER_MANIFEST,
    PROMOTED_ARTIFACT,
    PROMOTION_MANIFEST,
    RUNTIME_ARTIFACT,
    RUNTIME_MANIFEST,
    ArtifactLineageError,
    sha256_file,
    verify_runtime_manifest_semantics,
)

ROOT = Path(__file__).resolve().parents[1]


def _canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _metrics(payload: bytes) -> dict[str, int]:
    text = payload.decode("utf-8")
    return {
        "byte_length": len(payload),
        "line_count": len(text.splitlines()),
        "rule_count": text.count("(defrule"),
    }


def promote_byzantine_runtime(
    *,
    repository_root: Path = ROOT,
    runtime_artifact: Path | None = None,
    runtime_manifest: Path | None = None,
    destination_artifact: Path | None = None,
    destination_manifest: Path | None = None,
) -> tuple[Path, Path]:
    """Promote runtime bytes to the canonical root artifact and verify identity."""
    root = repository_root.resolve()
    runtime_path = runtime_artifact or (root / RUNTIME_ARTIFACT)
    runtime_manifest_path = runtime_manifest or (root / RUNTIME_MANIFEST)
    destination_path = destination_artifact or (root / PROMOTED_ARTIFACT)
    destination_manifest_path = destination_manifest or (root / PROMOTION_MANIFEST)

    compiler_manifest = json.loads(
        (root / COMPILER_MANIFEST).read_text(encoding="utf-8")
    )
    runtime_manifest_data = json.loads(runtime_manifest_path.read_text(encoding="utf-8"))
    verify_runtime_manifest_semantics(
        repository_root=root,
        compiler_manifest=compiler_manifest,
        overlay_manifest=json.loads(
            (root / "runtime/byzantine/Byzantine.runtime-overlay.json").read_text(
                encoding="utf-8"
            )
        ),
        manifest_path=runtime_manifest_path.relative_to(root),
    )

    runtime_bytes = runtime_path.read_bytes()
    runtime_sha = hashlib.sha256(runtime_bytes).hexdigest()

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    fd, staged_name = tempfile.mkstemp(
        prefix=f".{destination_path.name}.",
        suffix=".stage",
        dir=destination_path.parent,
    )
    try:
        staged = Path(staged_name)
        staged.write_bytes(runtime_bytes)
        with staged.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(staged, destination_path)
    finally:
        Path(staged_name).unlink(missing_ok=True)

    promoted_bytes = destination_path.read_bytes()
    promoted_sha = hashlib.sha256(promoted_bytes).hexdigest()
    if promoted_bytes != runtime_bytes:
        raise ArtifactLineageError(
            code="BYZ-PROMOTE-001",
            edge="runtime-artifact -> promoted-artifact",
            expected=runtime_sha,
            observed=promoted_sha,
            source_path=runtime_path,
            target_path=destination_path,
        )

    compiler_source_revision = str(runtime_manifest_data["compiler_source_revision"])
    promotion_manifest = {
        "schema": "byzantine-promoted-runtime-1",
        "artifact_kind": "promoted-runtime",
        "source_runtime": {
            "artifact_kind": "runtime",
            "path": RUNTIME_ARTIFACT.as_posix(),
            "manifest_path": RUNTIME_MANIFEST.as_posix(),
            "sha256": runtime_sha,
            "manifest_sha256": sha256_file(runtime_manifest_path),
        },
        "promoted_artifact": {
            "artifact_kind": "promoted-runtime",
            "path": PROMOTED_ARTIFACT.as_posix(),
            "manifest_path": PROMOTION_MANIFEST.as_posix(),
            "sha256": promoted_sha,
            **_metrics(promoted_bytes),
        },
        "promotion": {
            "version": "1",
            "mode": "byte-copy",
            "atomic": True,
            "source_matches_destination": True,
        },
        "compiler_source_revision": compiler_source_revision,
    }
    destination_manifest_path.write_bytes(_canonical_json(promotion_manifest))
    return destination_path, destination_manifest_path


def main() -> int:
    promote_byzantine_runtime()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
