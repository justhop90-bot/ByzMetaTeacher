"""Phase 4 (ROADMAP): explicit escrow ownership handoff.

Slice: an explicit, zero-native-command ownership edge excuses exactly
one pairwise same-resource multi-owner conflict. Without the edge the
conflict still fires; chains, starvation, and engine handoff behavior
stay out of scope.

Hard invariants pinned here (ESC-015/016/017/018/022):
- one owner per contract; percentage is not identity; balance is not
  entitlement; shared resources diagnose unless an explicit edge exists;
- the edge emits nothing: releases, policy resets, and consumption
  still lower through their own operations (terminality enforced there);
- no implicit handoff: self edges, same-owner edges, unknown contracts,
  unclaimed resources, and duplicates all fail closed.
"""
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.ast import Expression
from Compiler.ir import (
    EscrowAdmissionMode,
    EscrowConsumption,
    EscrowConsumptionMode,
    EscrowContract,
    EscrowOwnershipHandoff,
    EscrowRelease,
    EscrowReleaseKind,
    EscrowReserve,
    EscrowReserveKind,
    EscrowRetentionPolicy,
    SemanticId,
)
from Compiler.semantic.resource_control import (
    ResourceControlErrorCode,
    validate_escrow_contract_set,
)


def _contract(identity, owner, *, resources=("food",)):
    return EscrowContract(
        identity=identity,
        owner=owner,
        resources=resources,
        admission_mode=EscrowAdmissionMode.NORMAL_STOCKPILE_ONLY,
        reserve=EscrowReserve(
            kind=EscrowReserveKind.SET_PERCENTAGE,
            command="set-escrow-percentage",
            percentage=50,
        ),
        release=EscrowRelease(
            kind=EscrowReleaseKind.RELEASE_TO_STOCKPILE,
            command="release-escrow",
            trigger=Expression("(always)", "always", ()),
        ),
        consumption=EscrowConsumption(
            mode=EscrowConsumptionMode.NON_ESCROW_ACTION,
            action_primitive="research",
        ),
        retention_policy=EscrowRetentionPolicy.REQUIRE_RELEASE_OR_CONSUMPTION,
    )


def _edge(predecessor, successor, resources=("food",), **order):
    return EscrowOwnershipHandoff(
        predecessor=predecessor,
        successor=successor,
        resources=tuple(resources),
        **order,
    )


class EscrowOwnershipHandoffTests(unittest.TestCase):
    def test_explicit_handoff_passes(self):
        first = _contract("feudal-research", SemanticId("test", "feudal"))
        second = _contract("castle-military", SemanticId("test", "castle"))
        report = validate_escrow_contract_set(
            (first, second),
            (_edge("feudal-research", "castle-military"),),
        )
        self.assertTrue(report.valid, report.errors)
        self.assertEqual(report.errors, ())

    def test_handoff_without_edge_still_conflicts(self):
        first = _contract("feudal-research", SemanticId("test", "feudal"))
        second = _contract("castle-military", SemanticId("test", "castle"))
        report = validate_escrow_contract_set((first, second))
        self.assertEqual(
            tuple(error.code for error in report.errors),
            (ResourceControlErrorCode.ESCROW_RESOURCE_OWNER_CONFLICT,),
        )

    def test_handoff_unknown_contract_rejected(self):
        first = _contract("feudal-research", SemanticId("test", "feudal"))
        second = _contract("castle-military", SemanticId("test", "castle"))
        for predecessor, successor in (
            ("missing", "castle-military"),
            ("feudal-research", "missing"),
        ):
            report = validate_escrow_contract_set(
                (first, second),
                (_edge(predecessor, successor),),
            )
            self.assertIn(
                ResourceControlErrorCode.ESCROW_HANDOFF_UNKNOWN_CONTRACT,
                tuple(error.code for error in report.errors),
            )
            # The underlying owner conflict still fires: an invalid edge
            # excuses nothing.
            self.assertIn(
                ResourceControlErrorCode.ESCROW_RESOURCE_OWNER_CONFLICT,
                tuple(error.code for error in report.errors),
            )

    def test_handoff_self_and_same_owner_rejected(self):
        first = _contract("feudal-research", SemanticId("test", "feudal"))
        twin = _contract("feudal-again", SemanticId("test", "feudal"))
        with_self = validate_escrow_contract_set(
            (first, twin),
            (_edge("feudal-research", "feudal-research"),),
        )
        self.assertIn(
            ResourceControlErrorCode.ESCROW_HANDOFF_SELF,
            tuple(error.code for error in with_self.errors),
        )
        same_owner = validate_escrow_contract_set(
            (first, twin),
            (_edge("feudal-research", "feudal-again"),),
        )
        self.assertIn(
            ResourceControlErrorCode.ESCROW_HANDOFF_SELF,
            tuple(error.code for error in same_owner.errors),
        )

    def test_handoff_unclaimed_resource_rejected(self):
        first = _contract("feudal-research", SemanticId("test", "feudal"))
        second = _contract(
            "castle-military",
            SemanticId("test", "castle"),
            resources=("food", "gold"),
        )
        for resources in (("gold",), ("oil",), ("food", "oil")):
            report = validate_escrow_contract_set(
                (first, second),
                (_edge("feudal-research", "castle-military", resources),),
            )
            self.assertIn(
                ResourceControlErrorCode.ESCROW_HANDOFF_RESOURCE_MISMATCH,
                tuple(error.code for error in report.errors),
                resources,
            )

    def test_handoff_duplicate_rejected(self):
        first = _contract("feudal-research", SemanticId("test", "feudal"))
        second = _contract("castle-military", SemanticId("test", "castle"))
        edge = _edge("feudal-research", "castle-military")
        report = validate_escrow_contract_set(
            (first, second), (edge, edge)
        )
        self.assertIn(
            ResourceControlErrorCode.ESCROW_HANDOFF_DUPLICATE,
            tuple(error.code for error in report.errors),
        )

    def test_handoff_empty_resources_rejected_at_construction(self):
        with self.assertRaisesRegex(ValueError, "non-empty tuple"):
            EscrowOwnershipHandoff(
                predecessor="feudal-research",
                successor="castle-military",
                resources=(),
            )

    def test_three_claimants_still_conflict(self):
        contracts = (
            _contract("feudal", SemanticId("test", "feudal")),
            _contract("castle", SemanticId("test", "castle")),
            _contract("imperial", SemanticId("test", "imperial")),
        )
        report = validate_escrow_contract_set(
            contracts,
            (_edge("feudal", "castle"),),
        )
        # Handoff chains are a later slice: one edge excuses exactly one
        # pair, never a three-way claimant set.
        self.assertIn(
            ResourceControlErrorCode.ESCROW_RESOURCE_OWNER_CONFLICT,
            tuple(error.code for error in report.errors),
        )

    def test_handoff_covers_only_named_resources(self):
        first = _contract(
            "feudal-research",
            SemanticId("test", "feudal"),
            resources=("food", "gold"),
        )
        second = _contract(
            "castle-military",
            SemanticId("test", "castle"),
            resources=("food", "gold"),
        )
        report = validate_escrow_contract_set(
            (first, second),
            (_edge("feudal-research", "castle-military", ("food",)),),
        )
        subjects = tuple(error.subject for error in report.errors)
        self.assertIn("gold", subjects)
        self.assertNotIn("food", subjects)

    def test_handoff_validation_is_order_independent(self):
        first = _contract("feudal-research", SemanticId("test", "feudal"))
        second = _contract("castle-military", SemanticId("test", "castle"))
        edge = _edge("feudal-research", "castle-military")
        forward = validate_escrow_contract_set(
            (first, second), (edge,)
        )
        backward = validate_escrow_contract_set(
            (second, first), (edge,)
        )
        self.assertEqual(forward.errors, backward.errors)
        self.assertTrue(forward.valid)


if __name__ == "__main__":
    unittest.main()
