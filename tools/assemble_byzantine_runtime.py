#!/usr/bin/env python3
"""Deterministic compiler-artifact + runtime-overlay assembly."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from LearnerAI.Compiler.artifacts.lineage import (
    COMPILER_ARTIFACT,
    COMPILER_MANIFEST,
    OVERLAY_ARTIFACT,
    OVERLAY_MANIFEST,
    RUNTIME_ARTIFACT,
    RUNTIME_MANIFEST,
    ArtifactLineageError,
    sha256_file,
    verify_compiler_manifest_semantics,
    verify_overlay_manifest_semantics,
)

ROOT = Path(__file__).resolve().parents[1]


def _canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _rule_fingerprints(payload: bytes) -> set[str]:
    text = payload.decode("utf-8")
    rules: set[str] = set()
    cursor = 0
    while True:
        start = text.find("(defrule", cursor)
        if start < 0:
            return rules
        depth = 0
        end = None
        for index in range(start, len(text)):
            char = text[index]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is None:
            raise ArtifactLineageError(
                code="BYZ-ASSEMBLY-001",
                edge="compiler/overlay -> rule-parse",
                expected="balanced defrule",
                observed="unterminated rule",
            )
        rules.add(hashlib.sha256(text[start:end].encode("utf-8")).hexdigest())
        cursor = end


def _artifact_metrics(payload: bytes) -> dict[str, int]:
    text = payload.decode("utf-8")
    return {
        "byte_length": len(payload),
        "line_count": len(text.splitlines()),
        "rule_count": len(_rule_fingerprints(payload)),
    }


def assemble_byzantine_runtime(
    *,
    repository_root: Path = ROOT,
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    """Assemble and manifest the deterministic Byzantine runtime artifact."""
    root = repository_root.resolve()
    destination = (output_dir or (root / RUNTIME_ARTIFACT.parent)).resolve()
    destination.mkdir(parents=True, exist_ok=True)

    compiler_sha, compiler_revision = verify_compiler_manifest_semantics(
        repository_root=root,
    )
    overlay_sha = verify_overlay_manifest_semantics(repository_root=root)

    compiler_bytes = (root / COMPILER_ARTIFACT).read_bytes()
    overlay_bytes = (root / OVERLAY_ARTIFACT).read_bytes()

    compiler_rules = _rule_fingerprints(compiler_bytes)
    overlay_rules = _rule_fingerprints(overlay_bytes)
    collisions = sorted(compiler_rules & overlay_rules)
    if collisions:
        raise ArtifactLineageError(
            code="BYZ-ASSEMBLY-002",
            edge="compiler-artifact -> runtime-overlay",
            expected="disjoint emitted rule fingerprints",
            observed=",".join(collisions),
            source_path=root / COMPILER_ARTIFACT,
            target_path=root / OVERLAY_ARTIFACT,
        )

    if not compiler_bytes.endswith(b"\n"):
        compiler_bytes += b"\n"
    runtime_bytes = compiler_bytes + overlay_bytes

    artifact_path = destination / RUNTIME_ARTIFACT.name
    manifest_path = destination / RUNTIME_MANIFEST.name
    artifact_path.write_bytes(runtime_bytes)

    compiler_manifest_path = root / COMPILER_MANIFEST
    overlay_manifest_path = root / OVERLAY_MANIFEST
    runtime_manifest = {
        "schema": "byzantine-runtime-artifact-1",
        "artifact_kind": "runtime",
        "inputs": {
            "compiler": {
                "artifact_kind": "compiler",
                "path": COMPILER_ARTIFACT.as_posix(),
                "manifest_path": COMPILER_MANIFEST.as_posix(),
                "sha256": compiler_sha,
                "manifest_sha256": sha256_file(compiler_manifest_path),
            },
            "overlay": {
                "artifact_kind": "runtime-overlay",
                "id": "byzantine-runtime-overlay",
                "path": OVERLAY_ARTIFACT.as_posix(),
                "manifest_path": OVERLAY_MANIFEST.as_posix(),
                "sha256": overlay_sha,
                "manifest_sha256": sha256_file(overlay_manifest_path),
            },
        },
        "assembly": {
            "version": "1",
            "order": ["compiler", "runtime-overlay"],
            "conflict_mode": "reject",
            "deterministic": True,
        },
        "artifact": {
            "path": RUNTIME_ARTIFACT.as_posix(),
            "manifest_path": RUNTIME_MANIFEST.as_posix(),
            "sha256": hashlib.sha256(runtime_bytes).hexdigest(),
            **_artifact_metrics(runtime_bytes),
        },
        "compiler_source_revision": compiler_revision,
    }
    manifest_path.write_bytes(_canonical_json(runtime_manifest))

    return artifact_path, manifest_path


def main() -> int:
    assemble_byzantine_runtime()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
