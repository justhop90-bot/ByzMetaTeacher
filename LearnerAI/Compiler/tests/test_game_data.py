from LearnerAI.Compiler.ir.game_data_aoe2techtree import (
    Aoe2TechTreeNodeKind,
    Aoe2TechTreeNodeStatus,
    parse_aoe2techtree_byzantine_tree_json,
)
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
    FactStatus,
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
    VariableCost,
    ResearchProvider,
    SelectorKind,
    TechId,
    UnitDef,
    UnitId,
    UnitLineId,
)
from LearnerAI.Compiler.ir.versioning import PatchId


class GameDataTests(unittest.TestCase):
    def test_variable_cost_is_typed_and_deterministic(self):
        variable = VariableCost(
            "spies-treason-gold-per-enemy-civilian",
            parameters=(("minimum_gold", 200), ("maximum_gold", 30000), ("gold_per_civilian", 200)),
        )
        self.assertEqual(variable.formula_id, "spies-treason-gold-per-enemy-civilian")
        self.assertEqual(variable.parameters[2], ("gold_per_civilian", 200))
        self.assertEqual(variable, VariableCost(
            "spies-treason-gold-per-enemy-civilian",
            parameters=(("minimum_gold", 200), ("maximum_gold", 30000), ("gold_per_civilian", 200)),
        ))

    def test_variable_technology_cost_fails_closed_in_fixed_cost_api(self):
        profile = ByzantineProfile.for_update_185872()
        effective = resolve_effective_civ(profile)
        spies = effective.tech(408)
        self.assertIsInstance(spies.base_cost, VariableCost)
        with self.assertRaisesRegex(ValueError, "variable base cost"):
            effective.cost_of("tech:408")

    def test_spies_treason_is_materialized_as_variable_cost_without_fabricated_fixed_cost(self):
        profile = ByzantineProfile.for_update_185872()
        effective = resolve_effective_civ(profile)
        spies = effective.tech(408)
        self.assertEqual(spies.name, "Spies/Treason")
        self.assertEqual(spies.available_age, Age.IMPERIAL)
        self.assertEqual(spies.providers, (ResearchProvider(BuildingId(82)),))
        self.assertEqual(spies.research_time_seconds, 1)
        self.assertIsInstance(spies.base_cost, VariableCost)
        self.assertEqual(spies.base_cost.formula_id, "spies-treason-gold-per-enemy-civilian")
        self.assertEqual(
            spies.base_cost.parameters,
            (("minimum_gold", 200), ("maximum_gold", 30000), ("gold_per_civilian", 200)),
        )

    def test_manifest_coverage_leaves_only_unresolved_demolition_chain(self):
        from pathlib import Path

        profile = ByzantineProfile.for_update_185872()
        effective = resolve_effective_civ(profile)
        manifest = parse_byzantine_manifest(
            (Path(__file__).parents[3] / "docs" / "reference" / "BYZANTINES_manifest.txt").read_text(encoding="utf-8")
        )
        report = classify_byzantine_manifest_coverage(manifest, effective)
        self.assertEqual(report.modeled_count, 157)
        self.assertEqual(report.unmodeled_count, 2)
        self.assertEqual(
            {(node.kind, int(node.id)) for node in report.unmodeled_nodes},
            {(ManifestNodeKind.UNIT, 527), (ManifestNodeKind.UNIT, 528)},
        )

    def test_aoe2techtree_byzantine_tree_snapshot_parses_structure_and_status(self):
        raw = """
        {
          "buildings": [
            {
              "age_id": 3,
              "building_id": 82,
              "building_upgraded_from_id": -1,
              "link_id": null,
              "name": "Castle",
              "node_id": 82,
              "node_status": "ResearchedCompleted",
              "node_type": "BuildingTech",
              "use_type": "Building"
            }
          ],
          "units_techs": [
            {
              "age_id": 3,
              "building_id": 12,
              "link_id": 93,
              "name": "Pikeman",
              "node_id": 358,
              "node_status": "ResearchedCompleted",
              "node_type": "UnitUpgrade",
              "use_type": "Unit"
            },
            {
              "age_id": 3,
              "building_id": 82,
              "link_id": null,
              "name": "Logistica",
              "node_id": 61,
              "node_status": "ResearchRequired",
              "node_type": "Research",
              "use_type": "Tech"
            },
            {
              "age_id": 4,
              "building_id": 87,
              "link_id": null,
              "name": "Parthian Tactics",
              "node_id": 436,
              "node_status": "NotAvailable",
              "node_type": "Research",
              "use_type": "Tech"
            }
          ]
        }
        """
        snapshot = parse_aoe2techtree_byzantine_tree_json(
            raw,
            source="https://github.com/SiegeEngineers/aoe2techtree/blob/main/data/trees/BYZANTINES.json",
            revision="b554983ddae4466f22c98f4d71f35aa6da1fd4e2",
            patch=PatchId("AOE2DE", "185872", None, "2026-09-22"),
            content_hash="sha256:test-byzantine-tree",
        )

        self.assertEqual(snapshot.civ_name, "Byzantines")
        self.assertEqual(len(snapshot.buildings), 1)
        self.assertEqual(len(snapshot.units_techs), 3)
        castle = snapshot.node(Aoe2TechTreeNodeKind.BUILDING, 82)
        self.assertEqual(castle.status, Aoe2TechTreeNodeStatus.RESEARCHED_COMPLETED)
        self.assertEqual(castle.age, Age.CASTLE)
        pikeman = snapshot.node(Aoe2TechTreeNodeKind.UNIT, 358)
        self.assertEqual(pikeman.link_id, 93)
        self.assertEqual(snapshot.node(Aoe2TechTreeNodeKind.TECHNOLOGY, 436).status, Aoe2TechTreeNodeStatus.NOT_AVAILABLE)

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

    def test_byzantine_manifest_unavailable_nodes_are_exposed_as_verified_unavailable(self):
        data = resolve_effective_civ(ByzantineProfile.for_update_185872())
        expected_units = frozenset({
            UnitId(420),
            UnitId(542),
            UnitId(588),
            UnitId(691),
        })
        expected_technologies = frozenset({
            TechId(435),
            TechId(436),
            TechId(50),
            TechId(51),
            TechId(75),
            TechId(377),
            TechId(380),
            TechId(441),
            TechId(321),
        })
        self.assertEqual(data.verified_unavailable_units, expected_units)
        self.assertEqual(
            data.verified_unavailable_technologies,
            expected_technologies | frozenset({TechId(239)}),
        )
        for unit_id in expected_units:
            self.assertEqual(
                data.factual_status("unit", unit_id),
                FactStatus.VERIFIED_UNAVAILABLE,
            )
        for tech_id in expected_technologies:
            self.assertEqual(
                data.factual_status("technology", tech_id),
                FactStatus.VERIFIED_UNAVAILABLE,
            )

    def test_byzantine_manifest_coverage_counts_native_age_advance_nodes_as_modeled(self):
        profile = ByzantineProfile.for_update_185872()
        effective = resolve_effective_civ(profile)
        from pathlib import Path

        manifest_path = Path(__file__).parents[3] / "docs" / "reference" / "BYZANTINES_manifest.txt"
        manifest = parse_byzantine_manifest(manifest_path.read_text(encoding="utf-8"))
        report = classify_byzantine_manifest_coverage(manifest, effective)

        for tech_id in (101, 102, 103):
            self.assertNotIn(
                tech_id,
                {int(node.id) for node in report.unmodeled_nodes if node.kind is ManifestNodeKind.TECHNOLOGY},
            )
        self.assertEqual(
            report.modeled_count
            + report.unmodeled_count
            + report.verified_unavailable_count,
            len(manifest.nodes),
        )

    def test_pinned_snapshot_materializes_safe_manifest_building(self):
        from pathlib import Path
        import json

        from LearnerAI.Compiler.ir.game_data_manifest_buildings import (
            BYZANTINE_MANIFEST_BUILDING_SEEDS,
        )

        profile = ByzantineProfile.for_update_185872()
        effective = resolve_effective_civ(profile)

        source_path = (
            Path(__file__).parents[3]
            / "docs"
            / "reference"
            / "BYZANTINES_manifest.txt"
        )
        payload_path = (
            Path(__file__).parents[3]
            / "docs"
            / "reference"
            / "game-data"
            / "aoe2techtree-185872-buildings.json"
        )
        manifest = parse_byzantine_manifest(source_path.read_text(encoding="utf-8"))
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], "aoe2techtree-building-snapshot-v1")
        self.assertEqual(
            payload["source_revision"],
            "3bb43b1439eef88dfe7fe892d7f7dc41ac9dd76f",
        )
        self.assertEqual(
            payload["source_blob_sha"],
            "c4f7da961e82a8231b1ba49459949c4d6e479bc8",
        )
        self.assertEqual(payload["patch"], "AOE2DE:185872:2026-09-22")
        self.assertEqual(payload["building_count"], 1)
        self.assertEqual(len(payload["buildings"]), 1)

        seed_ids = {int(seed.id) for seed in BYZANTINE_MANIFEST_BUILDING_SEEDS}
        self.assertEqual(seed_ids, {199})
        self.assertEqual(payload["schema"], "aoe2techtree-building-snapshot-v1")
        self.assertEqual(payload["building_count"], 1)
        self.assertTrue(seed_ids.issubset({int(item["id"]) for item in payload["buildings"]}))

        building = effective.building(199)
        seed = BYZANTINE_MANIFEST_BUILDING_SEEDS[0]
        self.assertEqual(building.name, seed.name)
        self.assertEqual(building.available_age, seed.available_age)
        self.assertEqual(building.base_cost, seed.base_cost)
        self.assertIn(EvidenceKind.ENGINE_DATA, {ref.kind for ref in building.provenance})
        self.assertIn(EvidenceKind.REPOSITORY_MANIFEST, {ref.kind for ref in building.provenance})

        report = classify_byzantine_manifest_coverage(manifest, effective)
        self.assertEqual(
            {
                (node.kind, int(node.id))
                for node in report.unmodeled_nodes
            },
            {
                (ManifestNodeKind.UNIT, 527),
                (ManifestNodeKind.UNIT, 528),
                (ManifestNodeKind.TECHNOLOGY, 408),
            },
        )

    def test_pinned_snapshot_materializes_safe_manifest_units(self):
        from pathlib import Path
        import json

        from LearnerAI.Compiler.ir.game_data_manifest_units import (
            BYZANTINE_MANIFEST_UNIT_SEEDS,
        )

        profile = ByzantineProfile.for_update_185872()
        effective = resolve_effective_civ(profile)

        source_path = (
            Path(__file__).parents[3]
            / "docs"
            / "reference"
            / "BYZANTINES_manifest.txt"
        )
        payload_path = (
            Path(__file__).parents[3]
            / "docs"
            / "reference"
            / "game-data"
            / "aoe2techtree-185872-units.json"
        )
        manifest = parse_byzantine_manifest(source_path.read_text(encoding="utf-8"))
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], "aoe2techtree-unit-snapshot-v1")
        self.assertEqual(
            payload["source_revision"],
            "3bb43b1439eef88dfe7fe892d7f7dc41ac9dd76f",
        )
        self.assertEqual(
            payload["source_blob_sha"],
            "c4f7da961e82a8231b1ba49459949c4d6e479bc8",
        )
        self.assertEqual(payload["patch"], "AOE2DE:185872:2026-09-22")
        self.assertEqual(payload["unit_count"], 12)
        self.assertEqual(len(payload["units"]), 12)
        snapshot_ids = {int(item["id"]) for item in payload["units"]}

        seed_ids = {int(seed.id) for seed in BYZANTINE_MANIFEST_UNIT_SEEDS}
        self.assertEqual(len(seed_ids), 12)
        self.assertTrue(seed_ids.issubset(snapshot_ids))
        self.assertTrue(seed_ids.issubset({int(item.id) for item in effective.units}))

        for seed in BYZANTINE_MANIFEST_UNIT_SEEDS:
            unit = effective.unit(seed.id)
            self.assertEqual(unit.name, seed.name)
            self.assertEqual(unit.base_cost, seed.base_cost)
            self.assertEqual(unit.train_time_seconds, seed.train_time_seconds)
            self.assertEqual(unit.line, seed.line)
            self.assertIn(EvidenceKind.ENGINE_DATA, {ref.kind for ref in unit.provenance})
            self.assertIn(EvidenceKind.REPOSITORY_MANIFEST, {ref.kind for ref in unit.provenance})

        self.assertEqual(effective.unit(550).upgrades_from, UnitId(280))
        self.assertEqual(effective.unit(539).upgrades_to, UnitId(21))
        self.assertEqual(effective.unit(21).upgrades_from, UnitId(539))
        self.assertEqual(effective.unit(21).upgrades_to, UnitId(442))
        self.assertEqual(effective.unit(442).upgrades_from, UnitId(21))
        self.assertEqual(effective.unit(2626).upgrades_to, UnitId(2627))
        self.assertEqual(effective.unit(2627).upgrades_from, UnitId(2626))

        self.assertIn(UnitId(550), effective.unit_line("mangonel-line").members)
        self.assertIn(UnitId(539), effective.unit_line("galley-line").members)
        self.assertIn(UnitId(21), effective.unit_line("galley-line").members)
        self.assertIn(UnitId(442), effective.unit_line("galley-line").members)

        report = classify_byzantine_manifest_coverage(manifest, effective)
        self.assertEqual(
            {(node.kind, int(node.id)) for node in report.unmodeled_nodes},
            {
                (ManifestNodeKind.UNIT, 527),
                (ManifestNodeKind.UNIT, 528),
                (ManifestNodeKind.TECHNOLOGY, 408),
            },
        )

    def test_manifest_carrack_materializes_from_explicit_unit_source(self):
        from pathlib import Path

        profile = ByzantineProfile.for_update_185872()
        effective = resolve_effective_civ(profile)

        carrack = effective.unit(2628)
        self.assertEqual(carrack.name, "Carrack")
        self.assertEqual(carrack.available_age, Age.IMPERIAL)
        self.assertEqual(carrack.providers[0].building, BuildingId(45))
        self.assertEqual(carrack.line, UnitLineId("hulk-line"))
        self.assertEqual(carrack.base_cost, ResourceCost(wood=75, gold=35))
        self.assertEqual(carrack.train_time_seconds, 27)
        self.assertEqual(carrack.upgrades_from, UnitId(2627))
        self.assertIsNone(carrack.upgrades_to)
        self.assertEqual(effective.unit(2627).upgrades_to, UnitId(2628))

        self.assertIn(UnitId(2628), effective.unit_line("hulk-line").members)

        relation = next(
            item
            for item in effective.upgrade_relations
            if item.previous == UnitId(2627)
            and item.current == UnitId(2628)
        )
        self.assertEqual(relation.research, TechId(35))
        self.assertIn(EvidenceKind.REPOSITORY_MANIFEST, {ref.kind for ref in relation.provenance})
        self.assertIn(EvidenceKind.OFFICIAL_PATCH, {ref.kind for ref in relation.provenance})

        self.assertIn(
            EvidenceKind.REPOSITORY_MANIFEST,
            {ref.kind for ref in carrack.provenance},
        )
        self.assertIn(
            EvidenceKind.COMMUNITY_REFERENCE,
            {ref.kind for ref in carrack.provenance},
        )
        self.assertIn(
            EvidenceKind.OFFICIAL_PATCH,
            {ref.kind for ref in carrack.provenance},
        )

        report = classify_byzantine_manifest_coverage(
            parse_byzantine_manifest(
                (
                    Path(__file__).parents[3]
                    / "docs"
                    / "reference"
                    / "BYZANTINES_manifest.txt"
                ).read_text(encoding="utf-8")
            ),
            effective,
        )
        self.assertEqual(report.modeled_count, 157)
        self.assertEqual(report.unmodeled_count, 2)
        self.assertEqual(
            {
                (node.kind, int(node.id))
                for node in report.unmodeled_nodes
            },
            {
                (ManifestNodeKind.UNIT, 527),
                (ManifestNodeKind.UNIT, 528),
                (ManifestNodeKind.TECHNOLOGY, 408),
            },
        )

    def test_manifest_technology_conflicts_materialize_from_explicit_override_sources(self):
        from pathlib import Path

        profile = ByzantineProfile.for_update_185872()
        effective = resolve_effective_civ(profile)

        treadmill = effective.tech(54)
        siphons = effective.tech(909)

        self.assertEqual(treadmill.name, "Treadmill Crane")
        self.assertEqual(
            treadmill.base_cost,
            ResourceCost(wood=200, stone=50),
        )
        self.assertEqual(treadmill.research_time_seconds, 20)
        self.assertEqual(treadmill.providers[0].building, BuildingId(209))

        self.assertEqual(siphons.name, "Siphons")
        self.assertEqual(
            siphons.base_cost,
            ResourceCost(food=100, gold=175),
        )
        self.assertEqual(siphons.research_time_seconds, 45)
        self.assertEqual(siphons.providers[0].building, BuildingId(209))

        self.assertIn(
            EvidenceKind.REPOSITORY_MANIFEST,
            {ref.kind for ref in treadmill.provenance},
        )
        self.assertIn(
            EvidenceKind.COMMUNITY_REFERENCE,
            {ref.kind for ref in treadmill.provenance},
        )
        self.assertIn(
            EvidenceKind.REPOSITORY_MANIFEST,
            {ref.kind for ref in siphons.provenance},
        )
        self.assertIn(
            EvidenceKind.OFFICIAL_PATCH,
            {ref.kind for ref in siphons.provenance},
        )

        report = classify_byzantine_manifest_coverage(
            parse_byzantine_manifest(
                (
                    Path(__file__).parents[3]
                    / "docs"
                    / "reference"
                    / "BYZANTINES_manifest.txt"
                ).read_text(encoding="utf-8")
            ),
            effective,
        )
        self.assertEqual(report.modeled_count, 156)
        self.assertEqual(report.unmodeled_count, 3)
        self.assertEqual(
            {
                int(node.id)
                for node in report.unmodeled_nodes
                if node.kind is ManifestNodeKind.TECHNOLOGY
            },
            set(),
        )

    def test_pinned_snapshot_materializes_safe_unmodeled_manifest_technologies(self):
        from pathlib import Path
        import json

        from LearnerAI.Compiler.ir.game_data_manifest_technologies import (
            BYZANTINE_MANIFEST_TECHNOLOGY_SEEDS,
        )

        profile = ByzantineProfile.for_update_185872()
        effective = resolve_effective_civ(profile)

        manifest_path = Path(__file__).parents[3] / "docs" / "reference" / "BYZANTINES_manifest.txt"
        snapshot_path = (
            Path(__file__).parents[3]
            / "docs"
            / "reference"
            / "game-data"
            / "aoe2techtree-185872-technologies.json"
        )
        manifest = parse_byzantine_manifest(manifest_path.read_text(encoding="utf-8"))
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot_ids = {int(item["id"]) for item in payload["technologies"]}

        seed_ids = {int(seed.id) for seed in BYZANTINE_MANIFEST_TECHNOLOGY_SEEDS}
        self.assertEqual(len(seed_ids), 51)
        self.assertTrue(seed_ids.issubset(snapshot_ids))
        self.assertTrue(seed_ids.issubset({int(item.id) for item in effective.technologies}))

        for seed in BYZANTINE_MANIFEST_TECHNOLOGY_SEEDS:
            tech = effective.tech(seed.id)
            self.assertIsNotNone(tech.base_cost)
            self.assertIsNotNone(tech.research_time_seconds)
            self.assertIn(
                EvidenceKind.ENGINE_DATA,
                {ref.kind for ref in tech.provenance},
            )
            self.assertIn(
                EvidenceKind.REPOSITORY_MANIFEST,
                {ref.kind for ref in tech.provenance},
            )

        report = classify_byzantine_manifest_coverage(manifest, effective)
        self.assertEqual(
            {
                int(node.id)
                for node in report.unmodeled_nodes
                if node.kind is ManifestNodeKind.TECHNOLOGY
            },
            set(),
        )


    def test_byzantine_manifest_coverage_distinguishes_modeled_and_unmodeled(self):
        profile = ByzantineProfile.for_update_185872()
        effective = resolve_effective_civ(profile)
        from pathlib import Path

        manifest_path = Path(__file__).parents[3] / "docs" / "reference" / "BYZANTINES_manifest.txt"
        manifest = parse_byzantine_manifest(manifest_path.read_text(encoding="utf-8"))
        report = classify_byzantine_manifest_coverage(manifest, effective)

        self.assertEqual(report.modeled_count, 156)
        self.assertEqual(report.unmodeled_count, 3)
        self.assertEqual(report.verified_unavailable_count, 14)
        self.assertEqual(
            {
                int(node.id)
                for node in report.unmodeled_nodes
                if node.kind is ManifestNodeKind.TECHNOLOGY
            },
            set(),
        )
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

    def test_pinned_185872_aoe2techtree_snapshot_fills_unresolved_byzantine_tech_fields(self):
        from pathlib import Path
        import json

        snapshot_path = (
            Path(__file__).parents[3]
            / "docs"
            / "reference"
            / "game-data"
            / "aoe2techtree-185872-technologies.json"
        )
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], "aoe2techtree-technology-snapshot-v1")
        self.assertEqual(payload["source_revision"], "3bb43b1439eef88dfe7fe892d7f7dc41ac9dd76f")
        self.assertEqual(
            payload["source_blob_sha"],
            "c4f7da961e82a8231b1ba49459949c4d6e479bc8",
        )
        self.assertEqual(payload["patch"], "AOE2DE:185872:2026-09-22")
        self.assertEqual(payload["technology_count"], 201)
        self.assertEqual(len(payload["technologies"]), 201)

        source_patch = PatchId("AOE2DE", "185872", None, "2026-09-22")
        snapshot = parse_dat_technologies_json(
            json.dumps({"technologies": payload["technologies"]}),
            source=payload["source"],
            revision=payload["source_revision"],
            patch=source_patch,
            content_hash=payload["source_blob_sha"],
            extraction_version=payload["extraction_version"],
        )
        tech = next(item for item in snapshot.records if int(item.tech_id) == 47)
        self.assertEqual(tech.name, "Chemistry")
        self.assertEqual(tech.base_cost, ResourceCost(food=300, gold=200))
        self.assertEqual(tech.research_time_seconds, 100)
        self.assertEqual(tech.native_civ, -1)

        profile = ByzantineProfile.for_update_185872()
        base = profile.base_data
        original = base.tech(47)
        self.assertIsNone(original.base_cost)
        self.assertIsNone(original.research_time_seconds)

        merged = enrich_game_data_from_dat_snapshot(
            replace(
                base,
                technologies=tuple(
                    item for item in base.technologies if item.id == TechId(47)
                ),
            ),
            DatTechnologySnapshot(
                patch=snapshot.patch,
                evidence=snapshot.evidence,
                records=(tech,),
            ),
        )
        merged_tech = merged.tech(47)
        self.assertEqual(merged_tech.base_cost, ResourceCost(food=300, gold=200))
        self.assertEqual(merged_tech.research_time_seconds, 100)
        self.assertEqual(merged_tech.providers, original.providers)
        self.assertEqual(merged_tech.prerequisites, original.prerequisites)
        self.assertEqual(merged_tech.effects, original.effects)

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
