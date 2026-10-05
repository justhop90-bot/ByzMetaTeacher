"""Focused tests for Byzantine runtime assembly."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.assemble_byzantine_runtime import assemble_byzantine_runtime
from LearnerAI.Compiler.artifacts.lineage import ArtifactLineageError


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _fixture() -> Path:
    root = Path(tempfile.mkdtemp())
    compiler = root / "dist/byzantine/Byzantine.compiler.per"
    compiler.parent.mkdir(parents=True, exist_ok=True)
    compiler.write_text("(defrule compiler)\n", encoding="utf-8")
    overlay = root / "runtime/byzantine/Byzantine.runtime-overlay.per"
    overlay.parent.mkdir(parents=True, exist_ok=True)
    overlay.write_text("(defrule overlay)\n", encoding="utf-8")

    compiler_sha = _sha(compiler.read_bytes())
    overlay_sha = _sha(overlay.read_bytes())
    _write_json(
        root / "dist/byzantine/Byzantine.compiler.manifest.json",
        {
            "schema": "byzantine-compiler-artifact-1",
            "artifact_kind": "compiler",
            "artifact": {
                "path": "dist/byzantine/Byzantine.compiler.per",
                "manifest_path": "dist/byzantine/Byzantine.compiler.manifest.json",
                "sha256": compiler_sha,
                "byte_length": compiler.stat().st_size,
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
        },
    )
    _write_json(
        root / "runtime/byzantine/Byzantine.runtime-overlay.json",
        {
            "schema": "byzantine-runtime-overlay-1",
            "artifact_kind": "runtime-overlay",
            "id": "byzantine-runtime-overlay",
            "artifact": {
                "path": "runtime/byzantine/Byzantine.runtime-overlay.per",
                "manifest_path": "runtime/byzantine/Byzantine.runtime-overlay.json",
                "sha256": overlay_sha,
                "byte_length": overlay.stat().st_size,
                "line_count": 1,
                "rule_count": 1,
            },
            "ownership": {"conflict_mode": "reject"},
        },
    )
    return root


class ByzantineRuntimeAssemblyTests(unittest.TestCase):
    def test_assembly_is_deterministic_and_manifested(self):
        root = _fixture()
        first_root = root / "dist/byzantine"
        first_artifact, first_manifest = assemble_byzantine_runtime(
            repository_root=root,
            output_dir=first_root,
        )
        first_bytes = first_artifact.read_bytes()
        second_dir = root / "dist/second"
        second_artifact, second_manifest = assemble_byzantine_runtime(
            repository_root=root,
            output_dir=second_dir,
        )
        self.assertEqual(first_bytes, second_artifact.read_bytes())
        self.assertEqual(
            json.loads(first_manifest.read_text(encoding="utf-8"))["artifact"]["sha256"],
            _sha(first_bytes),
        )
        self.assertEqual(
            json.loads(first_manifest.read_text(encoding="utf-8")),
            json.loads(second_manifest.read_text(encoding="utf-8")),
        )

    def test_missing_overlay_fails_closed(self):
        root = _fixture()
        (root / "runtime/byzantine/Byzantine.runtime-overlay.per").unlink()
        with self.assertRaises(ArtifactLineageError):
            assemble_byzantine_runtime(repository_root=root)

    def test_duplicate_rule_body_is_rejected(self):
        root = _fixture()
        (root / "runtime/byzantine/Byzantine.runtime-overlay.per").write_text(
            "(defrule compiler)\n",
            encoding="utf-8",
        )
        overlay = root / "runtime/byzantine/Byzantine.runtime-overlay.per"
        manifest = json.loads(
            (root / "runtime/byzantine/Byzantine.runtime-overlay.json").read_text(
                encoding="utf-8"
            )
        )
        manifest["artifact"]["sha256"] = _sha(overlay.read_bytes())
        _write_json(root / "runtime/byzantine/Byzantine.runtime-overlay.json", manifest)
        with self.assertRaises(ArtifactLineageError) as ctx:
            assemble_byzantine_runtime(repository_root=root)
        self.assertEqual(ctx.exception.code, "BYZ-ASSEMBLY-002")


if __name__ == "__main__":
    unittest.main()
