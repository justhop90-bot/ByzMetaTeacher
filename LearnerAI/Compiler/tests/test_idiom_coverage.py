"""Phase 8 (ROADMAP): typed idiom-coverage ledger instrument tests.

Pins the measurement instrument itself (stage taxonomy, evidence
gates, determinism) plus the honesty properties of the seed: stages
never exceed their evidence, VERIFIED is claimed only with named
regression tests, and every LOWERABLE-or-higher evidence pointer
resolves to a real file or directory in the tree.
"""
import re
import unittest
from dataclasses import replace
from pathlib import Path

from Compiler.semantic.idiom_coverage import (
    IDIOM_COVERAGE_SEED,
    IdiomCoverageRecord,
    IdiomStage,
    validate_idiom_coverage,
)

COMPILER_DIR = Path(__file__).parents[1]

_PATH_TOKEN = re.compile(r"(?:tests|fixtures|assert|semantic|ir|emitter|clients)/[\w/.-]+")


def _evidence_paths(record):
    paths = []
    for field in (
        record.lowering_evidence,
        *record.verification_tests,
        record.semantic_surface,
        record.construction_entry,
    ):
        paths.extend(_PATH_TOKEN.findall(field))
    return paths


class IdiomCoverageTests(unittest.TestCase):
    def test_seed_validates_sorted_and_deterministic(self):
        first = validate_idiom_coverage()
        second = validate_idiom_coverage(tuple(first))
        self.assertEqual(first, second)
        self.assertEqual(
            tuple(record.idiom_id for record in first),
            tuple(sorted(record.idiom_id for record in first)),
        )
        self.assertEqual(len(first), 10)

    def test_verified_claims_stay_conservative(self):
        by_id = {record.idiom_id: record for record in validate_idiom_coverage()}
        self.assertEqual(
            {
                idiom_id
                for idiom_id, record in by_id.items()
                if record.stage is IdiomStage.VERIFIED
            },
            {"IDIOM-019", "IDIOM-021", "IDIOM-028"},
        )

    def test_stage_gates_reject_missing_evidence(self):
        base = IDIOM_COVERAGE_SEED[0]
        with self.assertRaisesRegex(ValueError, "corroboration must not be empty"):
            replace(base, corroboration="  ")
        with self.assertRaisesRegex(ValueError, "must name its semantic surface"):
            replace(
                base,
                stage=IdiomStage.SEMANTICIZED,
                semantic_surface="",
                construction_entry="",
                lowering_evidence="",
                verification_tests=(),
            )
        with self.assertRaisesRegex(ValueError, "must name its construction entry"):
            replace(
                base,
                stage=IdiomStage.EXPRESSIBLE,
                construction_entry="",
                lowering_evidence="",
                verification_tests=(),
            )
        with self.assertRaisesRegex(ValueError, "must name its lowering evidence"):
            replace(
                base,
                stage=IdiomStage.LOWERABLE,
                lowering_evidence="",
                verification_tests=(),
            )
        with self.assertRaisesRegex(ValueError, "must name regression tests"):
            replace(
                base,
                stage=IdiomStage.VERIFIED,
                verification_tests=(),
            )
        with self.assertRaisesRegex(ValueError, "must look like IDIOM-001"):
            replace(base, idiom_id="GOAL-FSM")
        with self.assertRaisesRegex(ValueError, "open boundary"):
            replace(base, open_boundary="")

    def test_duplicate_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate idiom coverage id"):
            validate_idiom_coverage(
                (IDIOM_COVERAGE_SEED[0], IDIOM_COVERAGE_SEED[0])
            )

    def test_lowering_evidence_paths_resolve_in_tree(self):
        missing = []
        for record in validate_idiom_coverage():
            if record.stage in (IdiomStage.DISCOVERED, IdiomStage.CORROBORATED):
                continue
            for token in _evidence_paths(record):
                candidate = COMPILER_DIR / token
                if not candidate.exists():
                    missing.append((record.idiom_id, token))
        self.assertEqual(missing, [])

    def test_every_record_states_open_boundary(self):
        for record in validate_idiom_coverage():
            self.assertTrue(record.open_boundary.strip())
            self.assertGreater(len(record.open_boundary), 20)


if __name__ == "__main__":
    unittest.main()
