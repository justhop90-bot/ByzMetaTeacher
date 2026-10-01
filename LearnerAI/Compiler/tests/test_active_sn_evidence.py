"""Phase 5 (ROADMAP): active Strategic Number evidence closure.

Slice: evidence-closed records for the 15 actively used SNs (14
controller-surfaced + 264), carrying pinned AIRef facts verbatim plus
checked-in community prevalence and compiler roles. Per-SN engine
effects, auto-mutation, and version deltas stay in the UNKNOWN boundary:
records prove evidence status, never native behavior.

Hard invariants pinned here:
- id/name/version/default/range/effective come from the pinned DE
  inventory only (never synthesized); loader fails closed on unknown
  ids, name drift, and non-DE scope;
- auto-mutation admits only UNKNOWN (nothing proven);
- prevalence is checked-in research data (Promisory/Naga hits), never a
  live filesystem scan;
- corpus-frequent non-SNs (sn-current-age, sn-military-superiority) are
  excluded explicitly: frequent in scripts, absent from the DE inventory;
- roles are descriptive controller links (all EVIDENCE_ONLY); 264 stays
  UNMAPPED OPEN evidence, never a promoted surface.
"""
import unittest
from dataclasses import replace

from Compiler.primitives.strategic_number_catalog import (
    ACTIVE_SN_SEEDS,
    ActiveSNRecord,
    ActiveSNSeed,
    load_active_sn_records,
    default_strategic_number_catalog,
)
from Compiler.semantic.native_controller import (
    NativeControlSurfaceKind,
    PracticeStatus,
    default_native_controller_catalog,
)


class ActiveSNEvidenceTests(unittest.TestCase):
    def test_loads_fifteen_records_sorted_deterministically(self):
        first = load_active_sn_records()
        second = load_active_sn_records()
        self.assertEqual(len(first), 15)
        self.assertEqual(
            tuple(record.sn_id for record in first),
            (0, 1, 2, 18, 20, 36, 42, 74, 117, 118, 119, 120, 167, 227, 264),
        )
        self.assertEqual(first, second)

    def test_golden_records_carry_pinned_facts_verbatim(self):
        by_id = {record.sn_id: record for record in load_active_sn_records()}
        town = by_id[74]
        self.assertEqual(town.canonical_name, "sn-maximum-town-size")
        self.assertEqual(town.default, 20)
        self.assertEqual(town.required_range, "0 to 255")
        self.assertEqual(town.effective, 1)
        self.assertEqual(town.version, "AoE1")
        self.assertIn("DE", town.supported_versions)
        self.assertEqual(town.semantic_role, "town-size-defense-targeting")
        self.assertEqual(town.prevalence_total, 356)
        explore = by_id[42]
        self.assertEqual(explore.canonical_name, "sn-number-explore-groups")
        self.assertEqual(explore.required_range, "0 to Max")
        attack = by_id[227]
        self.assertEqual(attack.default, 75)
        queue = by_id[264]
        self.assertEqual(queue.canonical_name, "sn-enable-training-queue")
        self.assertEqual(queue.version, "UP")
        self.assertEqual(queue.required_range, "0 to 15")
        self.assertEqual(queue.semantic_role, "UNMAPPED")

    def test_names_match_catalog_loader(self):
        catalog = default_strategic_number_catalog()
        for record in load_active_sn_records():
            self.assertEqual(
                catalog.record_name(record.sn_id), record.canonical_name
            )

    def test_effective_status_carried_verbatim_including_zero(self):
        by_id = {record.sn_id: record for record in load_active_sn_records()}
        # effective=0 despite descriptive surfacing: data, not executable proof.
        self.assertEqual(by_id[1].effective, 0)
        self.assertEqual(by_id[2].effective, 0)
        self.assertEqual(by_id[0].effective, 1)

    def test_auto_mutation_admits_only_unknown(self):
        for record in load_active_sn_records():
            self.assertEqual(record.auto_mutation, "UNKNOWN")
        with self.assertRaisesRegex(ValueError, "only UNKNOWN is admissible"):
            replace(load_active_sn_records()[0], auto_mutation="ENGINE")

    def test_unknown_boundary_required(self):
        for record in load_active_sn_records():
            self.assertTrue(record.unknown_boundary.strip())
        with self.assertRaisesRegex(ValueError, "UNKNOWN boundary must not be empty"):
            replace(
                load_active_sn_records()[0], unknown_boundary="  "
            )

    def test_evidence_hash_fails_closed_on_tampering(self):
        record = load_active_sn_records()[0]
        with self.assertRaisesRegex(ValueError, "evidence hash does not match"):
            replace(record, default=9999)
        with self.assertRaisesRegex(ValueError, "evidence hash does not match"):
            replace(record, semantic_role="attack-group-control")

    def test_roles_match_controller_surfaces_descriptively(self):
        controllers = default_native_controller_catalog()
        for record in load_active_sn_records():
            if record.semantic_role == "UNMAPPED":
                continue
            surface = controllers.resolve_surface(
                NativeControlSurfaceKind.STRATEGIC_NUMBER,
                record.canonical_name,
            )
            self.assertEqual(surface.controller_id, record.semantic_role)
            self.assertIs(surface.status, PracticeStatus.EVIDENCE_ONLY)

    def test_queue_capacity_sn_stays_unsurfaced(self):
        controllers = default_native_controller_catalog()
        with self.assertRaises(KeyError):
            controllers.resolve_surface(
                NativeControlSurfaceKind.STRATEGIC_NUMBER,
                "sn-enable-training-queue",
            )

    def test_corpus_frequent_non_sns_excluded(self):
        names = {
            record.canonical_name for record in load_active_sn_records()
        }
        self.assertNotIn("sn-current-age", names)
        self.assertNotIn("sn-military-superiority", names)

    def test_unmapped_seed_id_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "not a DE-documented"):
            load_active_sn_records(
                seeds=(
                    ActiveSNSeed(
                        sn_id=510,
                        prevalence=(("naga", 0),),
                        semantic_role="UNMAPPED",
                        unknown_boundary="probe",
                    ),
                )
            )

    def test_prevalence_totals_pinned(self):
        by_id = {record.sn_id: record for record in load_active_sn_records()}
        self.assertEqual(by_id[227].prevalence_total, 72)
        self.assertEqual(by_id[167].prevalence_total, 4)
        self.assertEqual(by_id[264].prevalence_total, 39)
        for record in load_active_sn_records():
            sources = tuple(source for source, _ in record.prevalence)
            self.assertEqual(tuple(sorted(sources)), sources)

    def test_seeds_cover_fifteen_ids(self):
        self.assertEqual(len(ACTIVE_SN_SEEDS), 15)
        self.assertEqual(
            tuple(sorted(seed.sn_id for seed in ACTIVE_SN_SEEDS)),
            (0, 1, 2, 18, 20, 36, 42, 74, 117, 118, 119, 120, 167, 227, 264),
        )


if __name__ == "__main__":
    unittest.main()
