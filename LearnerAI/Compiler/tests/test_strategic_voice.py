from __future__ import annotations

import unittest

from LearnerAI.Compiler.ir.model import GoalRole, GoalSlotRequest, SemanticId, StorageRequestId
from LearnerAI.Compiler.ir.native_control import NativeControlState
from LearnerAI.Compiler.ir.recurrent import TimerRequest
from LearnerAI.Compiler.ir.strategic_voice import (
    NativeVoiceBudget,
    NativeVoicePlan,
    VoiceAudience,
    VoiceLatchMode,
    VoicePriority,
    VoiceRule,
    validate_native_voice_plan,
)


def expr(source: str):
    from LearnerAI.Compiler.semantic.analyzer import parse_expression
    return parse_expression(source, None)


def goal_state(profile: str, name: str) -> NativeControlState:
    return NativeControlState(
        name,
        GoalSlotRequest(
            StorageRequestId(SemanticId(profile, name), name),
            role=GoalRole.PERSISTENT_STATE,
        ),
    )


def timer_state(profile: str, name: str) -> NativeControlState:
    return NativeControlState(
        name,
        TimerRequest(
            StorageRequestId(SemanticId(profile, f"timer:{name}"), f"timer:{name}"),
            initialization_policy="DISABLE_BEFORE_FIRST_USE",
            stability_key=f"{profile}:{name}",
        ),
    )


class NativeStrategosVoiceTests(unittest.TestCase):
    def _plan(self, rule: VoiceRule) -> NativeVoicePlan:
        return NativeVoicePlan(
            states=(
                goal_state("test", "voice-global-lock"),
                goal_state("test", "voice-match-count"),
                goal_state("test", rule.latch_state),
                timer_state("test", "voice-global-cooldown"),
                timer_state("test", rule.rearm_timer),
            ),
            rules=(rule,),
        )

    def test_valid_transition_rule_is_accepted(self) -> None:
        plan = self._plan(
            VoiceRule(
                identity="army-ready",
                order=0,
                priority=VoicePriority.TACTICAL,
                trigger=expr("(goal byzantine-army-attack-ready 1)"),
                clear=expr("(goal byzantine-army-attack-ready 0)"),
                message="The army is assembled. More preparation would be waste.",
                latch_state="voice-latch-army-ready",
                rearm_timer="voice-rearm-army-ready",
                audience=VoiceAudience.PLAYER,
                latch_mode=VoiceLatchMode.REARM_ON_CLEAR,
                cooldown_seconds=45,
            )
        )
        validate_native_voice_plan(plan)

    def test_polling_rule_without_clear_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "VOICE-POLLING-RULE"):
            VoiceRule(
                identity="bad-poll",
                order=0,
                priority=VoicePriority.CONTEXT,
                trigger=expr("(current-age >= castle-age)"),
                clear=None,
                message="I am in Castle Age.",
                latch_state="voice-latch-bad-poll",
                rearm_timer="voice-rearm-bad-poll",
                cooldown_seconds=120,
            )

    def test_budget_invariants_are_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            NativeVoiceBudget(soft_match_limit=49, hard_match_limit=48)
        with self.assertRaises(ValueError):
            NativeVoiceBudget(soft_match_limit=0, hard_match_limit=0)

    def test_critical_rule_requires_critical_cooldown_floor(self) -> None:
        plan = self._plan(
            VoiceRule(
                identity="critical-short",
                order=0,
                priority=VoicePriority.CRITICAL,
                trigger=expr("(true)"),
                clear=expr("(false)"),
                message="Critical.",
                latch_state="voice-latch-critical",
                rearm_timer="voice-rearm-critical",
                cooldown_seconds=2,
            )
        )
        with self.assertRaisesRegex(ValueError, "VOICE-COOLDOWN-CRITICAL"):
            validate_native_voice_plan(plan)

    def test_storage_requests_are_unique(self) -> None:
        plan = self._plan(
            VoiceRule(
                identity="one",
                order=0,
                priority=VoicePriority.CONTEXT,
                trigger=expr("(true)"),
                clear=expr("(false)"),
                message="One.",
                latch_state="voice-latch-one",
                rearm_timer="voice-rearm-one",
                cooldown_seconds=45,
            )
        )
        requests = plan.storage_requests
        self.assertEqual(len(requests), len({request.request_id for request in requests}))
        validate_native_voice_plan(plan)


if __name__ == "__main__":
    unittest.main()
