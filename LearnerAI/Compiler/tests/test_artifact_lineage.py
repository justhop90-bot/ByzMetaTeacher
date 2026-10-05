"""Semantic Byzantine artifact-lineage verification tests."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from LearnerAI.Compiler.artifacts.lineage import (
    ArtifactLineageError,
    verify_byzantine_artifact_lineage,
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write(path: Path, payload: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return _sha256(payload)


def _manifest_hash(path: Path) -> str:
    return _sha256(path.read_bytes())


def _write_json(path: Path, value: dict[str, object]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.write_bytes(payload)
    return _sha256(payload)


class ByzantineArtifactLineageTests(unittest.TestCase):
    def _fixture(self) -> Path:
        root = Path(tempfile.mkdtemp())
        compiler = root / "dist/byzantine/Byzantine.compiler.per"
        overlay = root / "runtime/byzantine/Byzantine.runtime-overlay.per"
        runtime = root / "dist/byzantine/Byzantine.runtime.per"
        promoted = root / "Byzantine.per"

        compiler_sha = _write(compiler, b"(defrule compiler)\n")
        overlay_sha = _write(overlay, b"(defrule overlay)\n")
        runtime_sha = _write(runtime, compiler.read_bytes() + overlay.read_bytes())
        promoted.write_bytes(runtime.read_bytes())

        compiler_manifest_path = root / "dist/byzantine/Byzantine.compiler.manifest.json"
        compiler_manifest = {
            "schema": "byzantine-compiler-artifact-1",
            "artifact_kind": "compiler",
            "artifact": {
                "path": "dist/byzantine/Byzantine.compiler.per",
                "manifest_path": "dist/byzantine/Byzantine.compiler.manifest.json",
                "sha256": compiler_sha,
                "byte_length": len(compiler.read_bytes()),
                "line_count": 1,
                "rule_count": 1,
            },
            "compiler": {
                "source_revision": "a" * 40,
                "entrypoint": "compile_strategy_profile",
            },
            "strategy": {
                "profile_entrypoint": "ByzantineProfile.for_update_185872",
                "strategy_entrypoint": "build_byzantine_strategy",
                "profile_id": "byzantine-stock-v1",
            },
            "effective_civ": {
                "civilization": "Byzantines",
                "civ_id": 13,
                "patch_key": "185872",
                "snapshot_fingerprint": "b" * 64,
            },
            "native_parser": {
                "name": "aoe2-ai-parser",
                "revision": "c" * 40,
            },
            "determinism": {
                "compile_repeat_equal": True,
                "hash_recomputed": True,
            },
        }
        _write_json(compiler_manifest_path, compiler_manifest)

        overlay_manifest_path = root / "runtime/byzantine/Byzantine.runtime-overlay.json"
        overlay_manifest = {
            "schema": "byzantine-runtime-overlay-1",
            "artifact_kind": "runtime-overlay",
            "id": "byzantine-runtime-overlay",
            "artifact": {
                "path": "runtime/byzantine/Byzantine.runtime-overlay.per",
                "manifest_path": "runtime/byzantine/Byzantine.runtime-overlay.json",
                "sha256": overlay_sha,
                "byte_length": len(overlay.read_bytes()),
                "line_count": 1,
                "rule_count": 1,
            },
            "ownership": {"conflict_mode": "reject"},
        }
        _write_json(overlay_manifest_path, overlay_manifest)

        runtime_manifest_path = root / "dist/byzantine/Byzantine.runtime.manifest.json"
        runtime_manifest = {
            "schema": "byzantine-runtime-artifact-1",
            "artifact_kind": "runtime",
            "inputs": {
                "compiler": {
                    "artifact_kind": "compiler",
                    "path": "dist/byzantine/Byzantine.compiler.per",
                    "manifest_path": "dist/byzantine/Byzantine.compiler.manifest.json",
                    "sha256": compiler_sha,
                    "manifest_sha256": _manifest_hash(compiler_manifest_path),
                },
                "overlay": {
                    "artifact_kind": "runtime-overlay",
                    "id": "byzantine-runtime-overlay",
                    "path": "runtime/byzantine/Byzantine.runtime-overlay.per",
                    "manifest_path": "runtime/byzantine/Byzantine.runtime-overlay.json",
                    "sha256": overlay_sha,
                    "manifest_sha256": _manifest_hash(overlay_manifest_path),
                },
            },
            "assembly": {
                "version": "1",
                "order": ["compiler", "runtime-overlay"],
                "conflict_mode": "reject",
                "deterministic": True,
            },
            "artifact": {
                "path": "dist/byzantine/Byzantine.runtime.per",
                "manifest_path": "dist/byzantine/Byzantine.runtime.manifest.json",
                "sha256": runtime_sha,
                "byte_length": len(runtime.read_bytes()),
                "line_count": 2,
                "rule_count": 2,
            },
            "compiler_source_revision": "a" * 40,
        }
        _write_json(runtime_manifest_path, runtime_manifest)

        promotion_manifest_path = root / "Byzantine.manifest.json"
        promotion_manifest = {
            "schema": "byzantine-promoted-runtime-1",
            "artifact_kind": "promoted-runtime",
            "source_runtime": {
                "artifact_kind": "runtime",
                "path": "dist/byzantine/Byzantine.runtime.per",
                "manifest_path": "dist/byzantine/Byzantine.runtime.manifest.json",
                "sha256": runtime_sha,
                "manifest_sha256": _manifest_hash(runtime_manifest_path),
            },
            "promoted_artifact": {
                "artifact_kind": "promoted-runtime",
                "path": "Byzantine.per",
                "manifest_path": "Byzantine.manifest.json",
                "sha256": runtime_sha,
                "byte_length": len(promoted.read_bytes()),
                "line_count": 2,
                "rule_count": 2,
            },
            "promotion": {
                "version": "1",
                "mode": "byte-copy",
                "atomic": True,
                "source_matches_destination": True,
            },
            "compiler_source_revision": "a" * 40,
        }
        _write_json(promotion_manifest_path, promotion_manifest)
        return root

    def test_valid_lineage_passes(self) -> None:
        root = self._fixture()
        result = verify_byzantine_artifact_lineage(repository_root=root)
        self.assertTrue(result.compiler_verified)
        self.assertTrue(result.runtime_verified)
        self.assertTrue(result.promotion_verified)
        self.assertTrue(result.root_matches_runtime)

    def test_compiler_hash_mismatch_reports_first_broken_edge(self) -> None:
        root = self._fixture()
        path = root / "dist/byzantine/Byzantine.compiler.per"
        path.write_bytes(b"(defrule tampered)\n")
        with self.assertRaises(ArtifactLineageError) as ctx:
            verify_byzantine_artifact_lineage(repository_root=root)
        self.assertEqual(ctx.exception.code, "BYZ-LINEAGE-003")
        self.assertEqual(ctx.exception.edge, "compiler-manifest -> compiler-artifact")

    def test_runtime_manifest_hash_mismatch_is_detected(self) -> None:
        root = self._fixture()
        path = root / "dist/byzantine/Byzantine.runtime.manifest.json"
        payload = json.loads(path.read_text())
        payload["inputs"]["compiler"]["sha256"] = "d" * 64
        _write_json(path, payload)
        with self.assertRaises(ArtifactLineageError) as ctx:
            verify_byzantine_artifact_lineage(repository_root=root)
        self.assertEqual(ctx.exception.code, "BYZ-LINEAGE-010")

    def test_runtime_and_promoted_bytes_must_match(self) -> None:
        root = self._fixture()
        (root / "Byzantine.per").write_bytes(b"(defrule divergent)\n")
        with self.assertRaises(ArtifactLineageError) as ctx:
            verify_byzantine_artifact_lineage(repository_root=root)
        self.assertEqual(ctx.exception.code, "BYZ-PROMOTE-001")
        self.assertEqual(
            ctx.exception.edge,
            "runtime-artifact -> promoted-artifact",
        )

    def test_canonical_path_reference_is_enforced(self) -> None:
        root = self._fixture()
        path = root / "Byzantine.manifest.json"
        payload = json.loads(path.read_text())
        payload["source_runtime"]["path"] = "dist/byzantine/not-runtime.per"
        _write_json(path, payload)
        with self.assertRaises(ArtifactLineageError) as ctx:
            verify_byzantine_artifact_lineage(repository_root=root)
        self.assertEqual(ctx.exception.code, "BYZ-LINEAGE-020")

    def test_runtime_artifact_hash_mismatch_is_detected(self) -> None:
        root = self._fixture()
        (root / "dist/byzantine/Byzantine.runtime.per").write_bytes(
            b"(defrule runtime-tampered)\n"
        )
        with self.assertRaises(ArtifactLineageError) as ctx:
            verify_byzantine_artifact_lineage(repository_root=root)
        self.assertEqual(ctx.exception.code, "BYZ-LINEAGE-013")

    def test_runtime_manifest_reference_hash_is_verified(self) -> None:
        root = self._fixture()
        path = root / "dist/byzantine/Byzantine.runtime.manifest.json"
        payload = json.loads(path.read_text())
        payload["inputs"]["overlay"]["manifest_sha256"] = "e" * 64
        _write_json(path, payload)
        with self.assertRaises(ArtifactLineageError) as ctx:
            verify_byzantine_artifact_lineage(repository_root=root)
        self.assertEqual(ctx.exception.code, "BYZ-LINEAGE-011")

    def test_promotion_runtime_manifest_reference_hash_is_verified(self) -> None:
        root = self._fixture()
        path = root / "Byzantine.manifest.json"
        payload = json.loads(path.read_text())
        payload["source_runtime"]["manifest_sha256"] = "f" * 64
        _write_json(path, payload)
        with self.assertRaises(ArtifactLineageError) as ctx:
            verify_byzantine_artifact_lineage(repository_root=root)
        self.assertEqual(ctx.exception.code, "BYZ-LINEAGE-020")

    def test_overlay_artifact_hash_mismatch_is_detected(self) -> None:
        root = self._fixture()
        (root / "runtime/byzantine/Byzantine.runtime-overlay.per").write_bytes(
            b"(defrule overlay-tampered)\n"
        )
        with self.assertRaises(ArtifactLineageError) as ctx:
            verify_byzantine_artifact_lineage(repository_root=root)
        self.assertEqual(ctx.exception.code, "BYZ-LINEAGE-011")

    def test_promoted_artifact_hash_mismatch_is_detected(self) -> None:
        root = self._fixture()
        path = root / "Byzantine.manifest.json"
        payload = json.loads(path.read_text())
        payload["promoted_artifact"]["sha256"] = "f" * 64
        _write_json(path, payload)
        with self.assertRaises(ArtifactLineageError) as ctx:
            verify_byzantine_artifact_lineage(repository_root=root)
        self.assertEqual(ctx.exception.code, "BYZ-LINEAGE-022")

    def test_runtime_source_revision_must_match_compiler(self) -> None:
        root = self._fixture()
        path = root / "dist/byzantine/Byzantine.runtime.manifest.json"
        payload = json.loads(path.read_text())
        payload["compiler_source_revision"] = "d" * 40
        _write_json(path, payload)
        with self.assertRaises(ArtifactLineageError) as ctx:
            verify_byzantine_artifact_lineage(repository_root=root)
        self.assertEqual(ctx.exception.code, "BYZ-LINEAGE-016")


if __name__ == "__main__":
    unittest.main()
