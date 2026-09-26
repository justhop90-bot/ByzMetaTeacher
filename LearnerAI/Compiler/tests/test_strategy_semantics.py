import unittest

from LearnerAI.Compiler.ir.civ_profile import ByzantineProfile, resolve_effective_civ
from LearnerAI.Compiler.ir.strategy import (
    StrategyPosture,
    StrategicEvidenceKind,
    StrategicTargetKind,
    build_byzantine_castle_strategy,
    lower_strategy_profile,
    resolve_strategy_profile,
)


class StrategySemanticsTests(unittest.TestCase):
    def setUp(self):
        self.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        self.profile = build_byzantine_castle_strategy(self.effective)

    def test_castle_strategy_resolves_against_effective_civ_data(self):
        resolved = resolve_strategy_profile(self.profile, self.effective)

        self.assertEqual(resolved.profile_id, "byzantine-land-castle-v1")
        self.assertIn("castle-commitment", resolved.demand_ids)

    def test_lowering_preserves_strategic_identity_and_opportunity_cost(self):
        compilation = lower_strategy_profile(self.profile, self.effective)

        demand = next(
            item for item in compilation.demands
            if item.name == "castle-commitment"
        )
        binding = compilation.bindings["castle-commitment"]

        self.assertEqual(binding.strategic_id, "castle-commitment")
        self.assertEqual(binding.posture, StrategyPosture.CASTLE_POWER)
        self.assertEqual(binding.opportunity_cost.owner, "castle-commitment")
        self.assertEqual(demand.strategic_binding, binding)

    def test_castle_target_is_a_persistent_exact_target_not_an_execution_witness(self):
        spec = next(
            item for item in self.profile.demands
            if item.identity == "castle-commitment"
        )

        self.assertEqual(spec.target.kind, StrategicTargetKind.EXACT)
        self.assertEqual(spec.target.entity_id, 82)
        self.assertTrue(
            any(
                evidence.kind is StrategicEvidenceKind.PERSISTENT
                for evidence in spec.reason
            )
        )

    def test_timing_only_reason_is_rejected(self):
        bad = self.profile.with_demand_override(
            "castle-commitment",
            reason=(
                self.profile.demand("castle-commitment").reason[0].__class__(
                    kind=StrategicEvidenceKind.TIMING,
                    expression="(game-time >= 1200)",
                    label="timing-only",
                ),
            ),
        )

        with self.assertRaisesRegex(ValueError, "persistent strategic evidence"):
            resolve_strategy_profile(bad, self.effective)

    def test_unavailable_entity_is_rejected(self):
        bad = self.profile.with_demand_override(
            "castle-commitment",
            capability_entity_id=999999,
        )

        with self.assertRaisesRegex(ValueError, "unknown building"):
            resolve_strategy_profile(bad, self.effective)

    def test_missing_opportunity_cost_owner_is_rejected(self):
        bad = self.profile.with_demand_override(
            "castle-commitment",
            opportunity_cost_owner="someone-else",
        )

        with self.assertRaisesRegex(ValueError, "opportunity-cost owner"):
            resolve_strategy_profile(bad, self.effective)

    def test_posture_has_no_timer_transition(self):
        for transition in self.profile.transitions:
            self.assertTrue(
                all(evidence.kind is not StrategicEvidenceKind.TIMING
                    for evidence in transition.evidence)
            )


if __name__ == "__main__":
    unittest.main()
