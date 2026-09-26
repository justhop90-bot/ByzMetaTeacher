import unittest
from unittest.mock import patch
from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.ir import (
    AccessKind,
    DemandOwnership,
    LifecycleAccessPhase,
    SemanticId,
    StateAccess,
)
from Compiler.compiler import compile_source
from Compiler.diagnostics import DiagnosticSeverity
from Compiler.errors import CompileError
from Compiler.parser import parse
from Compiler.primitives import default_de_registry
from Compiler.semantic import analyze
from Compiler.semantic.demand_ownership import (
    OwnershipDiagnostic,
    OwnershipDiagnosticCode,
    OwnershipReport,
    OwnershipStatus,
    analyze_demand_ownership,
)


SOURCE = """
demand castle {
    require (can-build castle)
    action (build castle)
    witness (building-type-count castle > 0)
    release (building-type-count castle > 0)
}
"""


def signature(diagnostic):
    state = diagnostic.state
    access = diagnostic.access
    return (
        diagnostic.code.value,
        diagnostic.severity.value,
        diagnostic.status.value,
        (
            state.owner.source_unit,
            state.purpose,
        ) if state is not None else None,
        (
            access.operation,
            access.source_order,
            access.owner.source_unit if access.owner else None,
            access.owner.local_name if access.owner else None,
        ) if access is not None else None,
        diagnostic.message,
    )


class DemandOwnershipTests(unittest.TestCase):
    def _demand(self):
        return analyze(
            parse(SOURCE),
            default_de_registry(),
            source_unit="test",
        )[0]

    def test_semantic_demand_has_explicit_typed_owner_contract(self):
        demand = self._demand()
        ownership = demand.ownership

        self.assertIsNotNone(ownership)
        self.assertIsInstance(ownership, DemandOwnership)
        self.assertEqual(ownership.owner, SemanticId("test", "castle"))
        self.assertEqual(ownership.demand, SemanticId("test", "castle"))
        self.assertEqual(
            ownership.state,
            demand.lifecycle.slot.request_id,
        )

    def test_first_writer_and_first_consumer_are_deterministic(self):
        demand = self._demand()
        first = analyze_demand_ownership((demand,))
        second = analyze_demand_ownership((demand,))

        self.assertTrue(first.valid)
        self.assertEqual(first.diagnostics, ())
        self.assertEqual(first, second)
        self.assertEqual(len(first.boundaries), 1)

        boundary = first.boundaries[0]
        self.assertEqual(
            boundary.first_writer.operation,
            "initialize",
        )
        self.assertEqual(
            boundary.first_writer.phase,
            LifecycleAccessPhase.INITIALIZATION,
        )
        self.assertEqual(boundary.first_writer.source_order, 0)
        self.assertEqual(
            boundary.first_consumer.operation,
            "release",
        )
        self.assertEqual(
            boundary.first_consumer.phase,
            LifecycleAccessPhase.RELEASE,
        )
        self.assertEqual(boundary.first_consumer.source_order, 1)
        self.assertEqual(boundary.first_consumer.owner, SemanticId("test", "castle"))

    def test_compile_pipeline_uses_ownership_validation_gate(self):
        diagnostic = OwnershipDiagnostic(
            code=OwnershipDiagnosticCode.DEMAND_MISSING_OWNERSHIP,
            severity=DiagnosticSeverity.ERROR,
            message="demand 'castle' has no semantic owner",
            status=OwnershipStatus.BLOCKED,
        )
        report = OwnershipReport(
            diagnostics=(diagnostic,),
            boundaries=(),
        )

        with patch(
            "Compiler.compiler.validate_demand_ownership",
            return_value=report,
        ) as validator:
            with self.assertRaisesRegex(
                CompileError,
                r"OWN-001: demand 'castle' has no semantic owner",
            ):
                compile_source(SOURCE)

            validator.assert_called_once()

    def test_missing_owner_has_exact_diagnostic(self):
        demand = self._demand()
        broken = replace(demand, ownership=None)

        report = analyze_demand_ownership((broken,))

        self.assertEqual(
            tuple(signature(item) for item in report.diagnostics),
            (
                (
                    "OWN-001",
                    "error",
                    "BLOCKED",
                    ("test", "lifecycle"),
                    None,
                    "demand 'castle' has no semantic owner",
                ),
            ),
        )

    def test_conflicting_writer_owners_have_exact_diagnostic(self):
        demand = self._demand()
        foreign_writer = StateAccess(
            state=demand.lifecycle.slot.request_id,
            owner=SemanticId("other", "strategy"),
            demand=demand.identity,
            kind=AccessKind.WRITE,
            phase=LifecycleAccessPhase.ACTION,
            source_order=99,
            operation="foreign-action",
        )
        broken = replace(
            demand,
            state_accesses=demand.state_accesses + (foreign_writer,),
        )

        report = analyze_demand_ownership((broken,))

        self.assertEqual(
            tuple(signature(item) for item in report.diagnostics),
            (
                (
                    "OWN-004",
                    "error",
                    "CONFLICTING",
                    ("test", "lifecycle"),
                    None,
                    "lifecycle state 'test:lifecycle' has conflicting writers: "
                    "other:strategy, test:castle",
                ),
            ),
        )

    def test_first_writer_consumer_order_tracks_multiple_emission_rules(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        demand monastery {
            require (can-build monastery)
            action (build monastery)
            witness (building-type-count monastery > 0)
            release (building-type-count monastery > 0)
        }
        """
        demands = analyze(
            parse(source),
            default_de_registry(),
            source_unit="test",
        )
        report = analyze_demand_ownership(demands)

        self.assertTrue(report.valid)
        first, second = report.boundaries
        self.assertEqual(first.first_writer.source_order, 0)
        self.assertEqual(first.first_consumer.source_order, 2)
        self.assertEqual(second.first_writer.source_order, 1)
        self.assertEqual(second.first_consumer.source_order, 10)

    def test_owner_state_mismatch_has_exact_diagnostic(self):
        demand = self._demand()
        ownership = replace(
            demand.ownership,
            owner=SemanticId("strategy", "castle"),
        )
        broken = replace(demand, ownership=ownership)

        report = analyze_demand_ownership((broken,))

        self.assertEqual(
            tuple(signature(item) for item in report.diagnostics),
            (
                (
                    "OWN-002",
                    "error",
                    "CONFLICTING",
                    ("test", "lifecycle"),
                    None,
                    "demand 'castle' owner 'strategy:castle' does not own lifecycle "
                    "state 'test:lifecycle'",
                ),
            ),
        )

    def test_consumer_before_writer_has_exact_diagnostic(self):
        demand = self._demand()
        accesses = tuple(
            replace(
                access,
                source_order=access.source_order + 100
                if access.kind is AccessKind.WRITE
                else access.source_order,
            )
            for access in demand.state_accesses
        )
        broken = replace(demand, state_accesses=accesses)

        report = analyze_demand_ownership((broken,))

        self.assertEqual(
            tuple(signature(item) for item in report.diagnostics),
            (
                (
                    "OWN-008",
                    "error",
                    "ORDER-VIOLATION",
                    ("test", "lifecycle"),
                    ("release", 1, "test", "castle"),
                    "lifecycle state 'test:lifecycle' consumer 'release' "
                    "precedes first writer 'initialize'",
                ),
            ),
        )

    def test_unconsumed_state_has_exact_diagnostic(self):
        demand = self._demand()
        broken = replace(
            demand,
            state_accesses=tuple(
                access
                for access in demand.state_accesses
                if access.kind is AccessKind.WRITE
            ),
        )

        report = analyze_demand_ownership((broken,))

        self.assertEqual(
            tuple(signature(item) for item in report.diagnostics),
            (
                (
                    "OWN-007",
                    "error",
                    "UNCONSUMED",
                    ("test", "lifecycle"),
                    None,
                    "lifecycle state 'test:lifecycle' is never consumed",
                ),
            ),
        )

    def test_duplicate_writers_in_one_phase_are_diagnosed(self):
        demand = self._demand()
        duplicate = StateAccess(
            state=demand.lifecycle.slot.request_id,
            owner=SemanticId("test", "castle"),
            demand=demand.identity,
            kind=AccessKind.WRITE,
            phase=LifecycleAccessPhase.ACTION,
            source_order=99,
            operation="duplicate-action",
        )
        broken = replace(
            demand,
            state_accesses=demand.state_accesses + (duplicate,),
        )

        report = analyze_demand_ownership((broken,))

        self.assertEqual(
            tuple(signature(item) for item in report.diagnostics),
            (
                (
                    "OWN-005",
                    "error",
                    "CONFLICTING",
                    ("test", "lifecycle"),
                    ("duplicate-action", 99, "test", "castle"),
                    "lifecycle state 'test:lifecycle' has multiple writers "
                    "in phase 'ISSUANCE'",
                ),
            ),
        )


if __name__ == "__main__":
    unittest.main()
