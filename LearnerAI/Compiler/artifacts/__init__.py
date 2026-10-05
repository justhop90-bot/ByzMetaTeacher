"""Artifact verification primitives for the Byzantine compiler/runtime pipeline."""
from .lineage import (
    ArtifactLineageError,
    ArtifactLineageResult,
    sha256_bytes,
    sha256_file,
    verify_byzantine_artifact_lineage,
    verify_compiler_manifest_semantics,
    verify_promotion_manifest_semantics,
    verify_runtime_manifest_semantics,
)

__all__ = [
    "ArtifactLineageError",
    "ArtifactLineageResult",
    "sha256_bytes",
    "sha256_file",
    "verify_byzantine_artifact_lineage",
    "verify_compiler_manifest_semantics",
    "verify_promotion_manifest_semantics",
    "verify_runtime_manifest_semantics",
]
