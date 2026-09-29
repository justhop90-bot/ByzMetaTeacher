from LearnerAI.Compiler.ir.game_data_dat_snapshot import (
    DatTechnologySnapshot,
    DatTechnologyRecord,
    enrich_game_data_from_aoe2techtree_json,
    enrich_game_data_from_dat_snapshot,
    parse_aoe2techtree_technologies_json,
    parse_dat_technologies_json,
)
from LearnerAI.Compiler.ir.versioning import EvidenceKind, EvidenceRef, PatchId

from dataclasses import replace
import unittest

from LearnerAI.Compiler.ir.civ_profile import (
    ByzantineProfile,
    EffectiveCivData,
    resolve_effective_civ,
)
from LearnerAI.Compiler.ir.game_data_manifest import (
    ManifestNodeKind,
    ManifestNodeStatus,
    classify_byzantine_manifest_coverage,
    parse_byzantine_manifest,
)
from LearnerAI.Compiler.ir.game_data import (
    Age,
    BuildingId,
    CoverageStatus,
    GameDataScope,
    Prerequisite,
    PrerequisiteKind,
    ResourceCost,
    SelectorKind,
    UnitDef,
)
from LearnerAI.Compiler.ir.versioning import PatchId


class GameDataTests(unittest.TestCase):
    def test_byzantine_185872_resolves_current_factual_snapshot(self):
        data = resolve_effective_civ(ByzantineProfile.for_update_185872())

        self.assertIsInstance(data, EffectiveCivData)
        self.assertEqual(data.patch.update, "185872")
        self.assertEqual(data.civ_name, "Byzantines")
        self.assertIn(BuildingId(82), data.available_buildings)
        self.assertEqual(data.building(82).name, "Castle")
        self.assertEqual(data.unit(358).name, "Pikeman")
        self.assertEqual(data.unit(358).base_cost, ResourceCost(food=35, wood=25))
        self.assertEqual(data.tech(61).name, "Logistica")
        self.assertEqual(data.coverage.status, CoverageStatus.FACTUAL_SUBSET)
        self.assertEqual(data.scope, GameDataScope.CIVILIZATION)
        self.assertEqual(int(data.scope_civ_id), 7)


    def test_byzantine_manifest_declares_complete_node_counts(self):
        from pathlib import Path

        manifest_path = Path(__file__).parents[3] / "docs" / "reference" / "BYZANTINES_manifest.txt"
        manifest = parse_byzantine_manifest(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest.building_count, 28)
        self.assertEqual(manifest.unit_tech_count, 145)
        self.assertEqual(len(manifest.nodes), 173)
        self.assertEqual(
            sum(node.kind is ManifestNodeKind.BUILDING for node in manifest.nodes),
            29,
        )
        self.assertTrue(any(
            node.status is ManifestNodeStatus.VERIFIED_UNAVAILABLE
            for node in manifest.nodes
        ))

    def test_byzantine_manifest_coverage_distinguishes_modeled_and_unmodeled(self):
        profile = ByzantineProfile.for_update_185872()
        effective = resolve_effective_civ(profile)
        from pathlib import Path

        manifest_path = Path(__file__).parents[3] / "docs" / "reference" / "BYZANTINES_manifest.txt"
        manifest = parse_byzantine_manifest(manifest_path.read_text(encoding="utf-8"))
        report = classify_byzantine_manifest_coverage(manifest, effective)

        self.assertEqual(report.modeled_count, 86)
        self.assertEqual(report.unmodeled_count, 73)
        self.assertEqual(report.verified_unavailable_count, 14)
        self.assertEqual(
            report.modeled_count
            + report.unmodeled_count
            + report.verified_unavailable_count,
            len(manifest.nodes),
        )

    def test_manifest_rejects_declared_count_drift(self):
        raw = (
            "Buildings: 28\n"
            "Units/tech nodes: 145\n"
            "BUILDINGS\n"
            "12 | Barracks | TYPE=BuildingTech | USE=Building | STATUS=ResearchedCompleted | AGE=1 | BUILDING=12 | LINK=<MISSING> | TRIGGER=<MISSING>\n"
            "AVAILABLE UNIT / TECH NODES\n"
            "4 | Archer | TYPE=Unit | USE=Unit | STATUS=ResearchedCompleted | AGE=2 | BUILDING=87 | LINK=<MISSING> | TRIGGER=<MISSING>\n"
        )
        with self.assertRaisesRegex(ValueError, "declared building count"):
            parse_byzantine_manifest(raw)


    def test_aoe2techtree_adapter_rejects_key_id_mismatch(self):
        raw = """
        {
          "data": {
            "Tech": {
              "61": {
                "Cost": {},
                "ID": 62,
                "ResearchTime": 50,
                "internal_name": "Byzantine Logistica"
              }
            }
          }
        }
        """
        with self.assertRaisesRegex(ValueError, "disagrees with embedded ID"):
            parse_aoe2techtree_technologies_json(
                raw,
                source="test://aoe2techtree/data.json",
                revision="test-revision",
                patch=PatchId("AOE2DE", "185872", None, "2026-09-22"),
                content_hash="sha256:test-aoe2techtree",
            )

    def test_aoe2techtree_adapter_parses_machine_readable_tech_shape(self):
        raw = """
        {
          "data": {
            "Tech": {
              "61": {
                "Cost": {"Food": 800, "Gold": 600},
                "ID": 61,
                "ResearchTime": 50,
                "internal_name": "Byzantine Logistica"
              }
            }
          }
        }
        """
        snapshot = parse_aoe2techtree_technologies_json(
            raw,
            source="https://github.com/SiegeEngineers/aoe2techtree/blob/main/data/data.json",
            revision="c4f7da961e82a8231b1ba49459949c4d6e479bc8",
            patch=PatchId("AOE2DE", "185872", None, "2026-09-22"),
            content_hash="sha256:test-aoe2techtree",
        )

        self.assertEqual(len(snapshot.records), 1)
        record = snapshot.records[0]
        self.assertEqual(int(record.tech_id), 61)
        self.assertEqual(record.name, "Byzantine Logistica")
        self.assertEqual(record.base_cost, ResourceCost(food=800, gold=600))
        self.assertEqual(record.research_time_seconds, 50)
        self.assertEqual(record.native_civ, -1)
        self.assertIsNone(record.research_location)
        self.assertEqual(record.effect_id, -1)

    def test_dat_technology_snapshot_parser_normalizes_cost_and_time(self):
        raw = """
        [
          {"id": 101, "name": "Feudal Age", "research_time": 130, "civ": -1,
           "effect_id": 0, "required_tech": -1, "required_tech_count": 0,
           "research_location": 109,
           "cost": {"food": 500, "gold": 0}},
          {"id": 102, "name": "Castle Age", "research_time": 160, "civ": -1,
           "effect_id": 1, "required_tech": 101, "required_tech_count": 1,
           "research_location": 109,
           "cost": {"food": 800, "gold": 200}}
        ]
        """
        snapshot = parse_dat_technologies_json(
            raw,
            source="dat://empires2_x2_p1.dat",
            revision="test-dat-build-185872",
            patch=PatchId("AOE2DE", "185872", None, "2026-09-22"),
            content_hash="sha256:test-snapshot",
        )

        self.assertEqual(snapshot.records[0].base_cost, ResourceCost(food=500))
        self.assertEqual(snapshot.records[1].research_time_seconds, 160)
        self.assertEqual(snapshot.records[0].native_civ, -1)

    def test_dat_snapshot_merge_fills_only_unresolved_technology_fields(self):
        profile = ByzantineProfile.for_update_185872()
        data = profile.base_data
        source_patch = PatchId("AOE2DE", "185872", None, "2026-09-22")
        tech = data.technologies[0]
        data = replace(
            data,
            technologies=tuple(
                replace(
                    item,
                    base_cost=None,
                    research_time_seconds=None,
                )
                if item.id == tech.id
                else item
                for item in data.technologies
            ),
        )
        snapshot = DatTechnologySnapshot(
            patch=source_patch,
            evidence=EvidenceRef(
                EvidenceKind.ENGINE_DATA,
                "dat://empires2_x2_p1.dat",
                "test-dat-build-185872",
                "technologies.json",
                source_patch,
                content_hash="sha256:test-snapshot",
                extraction_version="aoe2dat-json-v1",
            ),
            records=(
                DatTechnologyRecord(
                    tech_id=tech.id,
                    name=tech.name,
                    native_civ=-1,
                    base_cost=ResourceCost(food=123),
                    research_time_seconds=77,
                    research_location=109,
                    effect_id=0,
                    required_tech_ids=(),
                ),
            ),
        )

        merged = enrich_game_data_from_dat_snapshot(data, snapshot)
        merged_tech = merged.tech(int(tech.id))
        self.assertEqual(merged_tech.base_cost, ResourceCost(food=123))
        self.assertEqual(merged_tech.research_time_seconds, 77)
        self.assertIn(snapshot.evidence, merged_tech.provenance)

    def test_dat_snapshot_merge_rejects_name_mismatch(self):
        profile = ByzantineProfile.for_update_185872()
        data = profile.base_data
        tech = data.technologies[0]
        patch = PatchId("AOE2DE", "185872", None, "2026-09-22")
        snapshot = DatTechnologySnapshot(
            patch=patch,
            evidence=EvidenceRef(
                EvidenceKind.ENGINE_DATA,
                "dat://empires2_x2_p1.dat",
                "test-dat-build-185872",
                "technologies.json",
                patch,
                content_hash="sha256:test-snapshot",
            ),
            records=(
                DatTechnologyRecord(
                    tech_id=tech.id,
                    name="NOT " + tech.name,
                    native_civ=-1,
                    base_cost=ResourceCost(food=1),
                    research_time_seconds=1,
                    research_location=109,
                    effect_id=0,
                    required_tech_ids=(),
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "name mismatch"):
            enrich_game_data_from_dat_snapshot(data, snapshot)

    def test_dat_snapshot_merge_rejects_snapshot_patch_newer_than_game_data(self):
        profile = ByzantineProfile.for_update_185872()
        data = resolve_effective_civ(profile)
        newer = PatchId("AOE2DE", "999999", None, "2027-01-01")
        snapshot = DatTechnologySnapshot(
            patch=newer,
            evidence=EvidenceRef(
                EvidenceKind.ENGINE_DATA,
                "dat://empires2_x2_p1.dat",
                "future-build",
                "technologies.json",
                newer,
                content_hash="sha256:test-snapshot",
            ),
            records=(),
        )
        with self.assertRaisesRegex(ValueError, "does not exactly match"):
            enrich_game_data_from_dat_snapshot(data, snapshot)

    def test_byzantine_cost_modifier_resolves_without_mutating_base_game_cost(self):
        profile = ByzantineProfile.for_update_185872()
        effective = resolve_effective_civ(profile)

        self.assertEqual(effective.unit(358).base_cost, ResourceCost(food=35, wood=25))
        self.assertEqual(
            effective.cost_of("unit:358"),
            ResourceCost(food=26, wood=19),
        )

    def test_patch_identity_is_part_of_the_effective_snapshot_fingerprint(self):
        profile = ByzantineProfile.for_update_185872()
        first = resolve_effective_civ(profile)
        self.assertEqual(first.fingerprint, resolve_effective_civ(profile).fingerprint)
        with self.assertRaisesRegex(ValueError, "GameData snapshot patch"):
            resolve_effective_civ(
                replace(
                    profile,
                    patch=PatchId(
                        product="AOE2DE",
                        update="185873",
                        build=None,
                        release_date="2026-09-23",
                    ),
                )
            )

    def test_verified_unavailable_facts_are_part_of_snapshot_identity(self):
        profile = ByzantineProfile.for_update_185872()
        first = resolve_effective_civ(profile)
        self.assertTrue(profile.availability)
        altered = resolve_effective_civ(
            replace(profile, availability=profile.availability[:-1])
        )
        self.assertNotEqual(first.fingerprint, altered.fingerprint)

    def test_strategy_semantics_are_not_available_in_game_data(self):
        unit = UnitDef(
            id=358,
            name="Pikeman",
            line="pikeman-line",
            available_age=Age.CASTLE,
            providers=(),
            base_cost=ResourceCost(food=35, wood=25),
            train_time_seconds=None,
            prerequisites=(),
            classes=("INFANTRY",),
        )

        self.assertFalse(hasattr(unit, "strategic_tags"))

    def test_n_of_prerequisite_rejects_invalid_shape(self):
        with self.assertRaises(ValueError):
            Prerequisite(PrerequisiteKind.N_OF, count=0, children=(Prerequisite(PrerequisiteKind.AGE, age=Age.DARK),))
        with self.assertRaises(ValueError):
            Prerequisite(PrerequisiteKind.N_OF, count=2, children=(Prerequisite(PrerequisiteKind.AGE, age=Age.DARK),))

    def test_invalid_selector_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            SelectorKind("BEST_RESPONSE")


if __name__ == "__main__":
    unittest.main()
