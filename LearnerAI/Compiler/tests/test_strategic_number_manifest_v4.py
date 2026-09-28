import hashlib
import json
import unittest

from Compiler.ir import GoalRole, SemanticId, StorageRequestId
from Compiler.runtime_binding import (
    BindingManifest,
    BindingContext,
    RuntimeBinder,
    StrategicNumberInventory,
    StrategicNumberRequest,
    StrategicNumberSlot,
)


class StrategicNumberManifestV4Tests(unittest.TestCase):
    def _request(self, name="castle-posture"):
        return StrategicNumberRequest(
            StorageRequestId(
                SemanticId("controller.per", name),
                "controller.posture",
            ),
            why_not_goal="Native controller state requires Strategic Number storage.",
            stability_key="controller.posture.v1",
            role=GoalRole.PERSISTENT_STATE,
        )

    def _inventory(self):
        return StrategicNumberInventory(
            inventory_sha="a" * 64,
            documented_ids=frozenset({511}),
            candidate_ids=frozenset({510, 509, 508}),
        )

    def _manifest(self):
        request = self._request()
        result = RuntimeBinder().bind(
            (request,),
            BindingContext(strategic_number_inventory=self._inventory()),
        )
        return result.to_manifest(package_inventory_sha="b" * 64)

    def test_v4_serializes_request_contract_and_integrity(self):
        manifest = self._manifest()
        payload = json.loads(manifest.to_json())

        self.assertEqual(payload["format_version"], 4)
        self.assertEqual(
            payload["schema"],
            "aoe2.compiler.binding-manifest",
        )
        self.assertIn("integrity", payload)
        self.assertEqual(
            payload["integrity"]["algorithm"],
            "SHA-256",
        )
        record = payload["records"][0]
        self.assertEqual(record["request_contract"]["stability_key"], "controller.posture.v1")
        self.assertEqual(
            record["provenance"]["strategic_number_inventory_sha"],
            "a" * 64,
        )
        self.assertEqual(
            len(record["provenance"]["request_fingerprint"]),
            64,
        )

    def test_v4_round_trip_is_byte_stable(self):
        text = self._manifest().to_json()
        restored = BindingManifest.from_json(text)
        self.assertEqual(restored.to_json(), text)

    def test_v4_rejects_tampered_numeric_binding(self):
        payload = json.loads(self._manifest().to_json())
        payload["records"][0]["strategic_number_id"] = 508
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        with self.assertRaisesRegex(ValueError, "integrity"):
            BindingManifest.from_json(text)

    def test_v4_rejects_tampered_request_contract(self):
        payload = json.loads(self._manifest().to_json())
        payload["records"][0]["request_contract"]["stability_key"] = "controller.posture.v2"
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
            BindingManifest.from_json(text)

    def test_v4_external_digest_detects_coordinated_tamper(self):
        manifest = self._manifest()
        text = manifest.to_json()
        original_payload = json.loads(text)
        canonical = manifest.canonical_content_bytes()
        expected = hashlib.sha256(canonical).hexdigest()

        payload = dict(original_payload)
        payload["records"] = list(payload["records"])
        payload["records"][0] = dict(payload["records"][0])
        payload["records"][0]["strategic_number_id"] = 508

        tampered_payload_without_integrity = dict(payload)
        tampered_payload_without_integrity.pop("integrity")
        tampered_manifest_seed = BindingManifest.from_json(
            json.dumps(tampered_payload_without_integrity, indent=2, sort_keys=True)
            + "\n",
            verify_integrity=False,
        )
        tampered_content_sha256 = tampered_manifest_seed.content_sha256()
        payload["integrity"] = {
            "algorithm": "SHA-256",
            "content_sha256": tampered_content_sha256,
        }
        tampered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        tampered_manifest = BindingManifest.from_json(
            tampered,
            verify_integrity=True,
        )
        with self.assertRaisesRegex(ValueError, "expected external digest"):
            tampered_manifest.verify_integrity(expected_content_sha256=expected)

    def test_v3_requires_explicit_migration_context_for_sn_reuse(self):
        payload = {
            "format_version": 3,
            "package_inventory_sha": "b" * 64,
            "allocator_version": "native-storage-v4",
            "records": [
                {
                    "source_unit": "controller.per",
                    "local_name": "castle-posture",
                    "purpose": "controller.posture",
                    "role": "PERSISTENT_STATE",
                    "provenance_id": "legacy",
                    "binding_kind": "STRATEGIC_NUMBER",
                    "strategic_number_id": 509,
                    "strategic_number_inventory_sha": "a" * 64,
                }
            ],
        }
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        with self.assertRaisesRegex(ValueError, "explicit migration to v4"):
            BindingManifest.from_json(text)
        with self.assertRaisesRegex(ValueError, "migration context"):
            BindingManifest.migrate_to_v4(
                text,
                strategic_number_inventory=self._inventory(),
            )

    def test_v3_migration_preserves_numeric_binding(self):
        request = self._request()
        payload = {
            "format_version": 3,
            "package_inventory_sha": "b" * 64,
            "allocator_version": "native-storage-v4",
            "records": [
                {
                    "source_unit": request.request_id.owner.source_unit,
                    "local_name": request.request_id.owner.local_name,
                    "purpose": request.request_id.purpose,
                    "role": request.role.value,
                    "provenance_id": "legacy",
                    "binding_kind": "STRATEGIC_NUMBER",
                    "strategic_number_id": 509,
                    "strategic_number_inventory_sha": "a" * 64,
                }
            ],
        }
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        migrated = BindingManifest.migrate_to_v4(
            text,
            strategic_number_requests=(request,),
            strategic_number_inventory=self._inventory(),
            package_inventory_sha="b" * 64,
            allocator_version="native-storage-v5",
        )
        record = migrated.to_json()
        round_trip = BindingManifest.from_json(record)
        self.assertEqual(
            round_trip.binding_for(request.request_id).id,
            509,
        )

    def test_v3_migration_does_not_reallocate(self):
        request = self._request()
        inventory = StrategicNumberInventory(
            inventory_sha="a" * 64,
            documented_ids=frozenset({511}),
            candidate_ids=frozenset({510, 509, 508}),
        )
        payload = {
            "format_version": 3,
            "package_inventory_sha": "b" * 64,
            "allocator_version": "native-storage-v4",
            "records": [
                {
                    "source_unit": request.request_id.owner.source_unit,
                    "local_name": request.request_id.owner.local_name,
                    "purpose": request.request_id.purpose,
                    "role": request.role.value,
                    "provenance_id": "legacy",
                    "binding_kind": "STRATEGIC_NUMBER",
                    "strategic_number_id": 508,
                    "strategic_number_inventory_sha": "a" * 64,
                }
            ],
        }
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        migrated = BindingManifest.migrate_to_v4(
            text,
            strategic_number_requests=(request,),
            strategic_number_inventory=inventory,
            package_inventory_sha="b" * 64,
            allocator_version="native-storage-v5",
        )
        self.assertEqual(
            migrated.binding_for(request.request_id).id,
            508,
        )


if __name__ == "__main__":
    unittest.main()
