from __future__ import annotations

import unittest

from LearnerAI.Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_strategy,
)
from LearnerAI.Compiler.ir.civ_profile import resolve_effective_civ
from LearnerAI.Compiler.ir.strategic_voice import (
    VoicePriority,
    validate_native_voice_plan,
)


class ByzantineVoicePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        self.profile = build_byzantine_strategy(effective)

    def test_default_byzantine_voice_plan_has_the_canonical_event_set(self) -> None:
        plan = self.profile.voice_plan
        self.assertIsNotNone(plan)
        assert plan is not None

        expected = {
            "strategos-posture-castle-power",
            "strategos-cavalry-pressure",
            "strategos-ranged-pressure",
            "strategos-severe-counter",
            "strategos-resource-abundance",
            "strategos-army-preparation",
            "strategos-army-ready",
            "strategos-siege-blocker",
            "strategos-attack-issued",
            "strategos-attack-witness",
            "strategos-push-failed",
            "strategos-gold-recovery",
            "strategos-reassessment",
            "strategos-endgame-advance",
            "strategos-online",
        }
        self.assertEqual({rule.identity for rule in plan.rules}, expected)
        self.assertEqual(len(plan.rules), 15)
        online = next(rule for rule in plan.rules if rule.identity == "strategos-online")
        self.assertIs(online.priority, VoicePriority.FLAVOR)
        self.assertEqual(online.audience.value, "ALL")
        self.assertEqual(online.trigger.source, "(game-time >= 30)")
        self.assertEqual(online.clear.source, "(game-time < 30)")
        validate_native_voice_plan(plan)

    def test_voice_priorities_keep_critical_combat_events_above_context(self) -> None:
        plan = self.profile.voice_plan
        assert plan is not None
        priorities = {rule.identity: rule.priority for rule in plan.rules}

        self.assertIs(priorities["strategos-attack-issued"], VoicePriority.CRITICAL)
        self.assertIs(priorities["strategos-attack-witness"], VoicePriority.CRITICAL)
        self.assertIs(priorities["strategos-push-failed"], VoicePriority.CRITICAL)
        self.assertIs(priorities["strategos-resource-abundance"], VoicePriority.CONTEXT)

    def test_voice_rules_have_clear_witnesses_and_unique_storage(self) -> None:
        plan = self.profile.voice_plan
        assert plan is not None
        self.assertTrue(all(rule.clear is not None for rule in plan.rules))
        self.assertEqual(
            len(plan.storage_requests),
            len({request.request_id for request in plan.storage_requests}),
        )
        self.assertIn("voice-global-lock", {state.identifier for state in plan.states})
        self.assertIn("voice-match-count", {state.identifier for state in plan.states})
        self.assertIn("voice-global-cooldown", {state.identifier for state in plan.states})


if __name__ == "__main__":
    unittest.main()
