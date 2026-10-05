"""Focused tests for Byzantine runtime promotion."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.assemble_byzantine_runtime import assemble_byzantine_runtime
from tools.promote_byzantine_runtime import promote_byzantine_runtime
from .test_artifact_lineage import ByzantineArtifactLineageTests


class ByzantineRuntimePromotionTests(unittest.TestCase):
    def test_promotion_copies_runtime_bytes_and_writes_receipt(self):
        root = ByzantineArtifactLineageTests()._fixture()
        assemble_byzantine_runtime(repository_root=root)
        destination, manifest = promote_byzantine_runtime(repository_root=root)
        runtime = root / "dist/byzantine/Byzantine.runtime.per"
        self.assertEqual(destination.read_bytes(), runtime.read_bytes())
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(payload["source_runtime"]["sha256"], payload["promoted_artifact"]["sha256"])
        self.assertTrue(payload["promotion"]["atomic"])
        self.assertTrue(payload["promotion"]["source_matches_destination"])

    def test_promotion_replaces_stale_root_bytes(self):
        root = ByzantineArtifactLineageTests()._fixture()
        assemble_byzantine_runtime(repository_root=root)
        (root / "Byzantine.per").write_bytes(b"stale\n")
        destination, _ = promote_byzantine_runtime(repository_root=root)
        self.assertEqual(
            destination.read_bytes(),
            (root / "dist/byzantine/Byzantine.runtime.per").read_bytes(),
        )


if __name__ == "__main__":
    unittest.main()
