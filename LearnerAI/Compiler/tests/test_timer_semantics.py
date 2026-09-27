import unittest

from Compiler.ir.recurrent import (
    TimerRuntimeState,
    TimerStatus,
    create_initialized_timer,
    read_timer_triggered,
)


class TimerGenerationIRTests(unittest.TestCase):
    def test_initialized_timer_starts_disabled_at_generation_zero(self):
        timer = create_initialized_timer("1")

        self.assertTrue(timer.initialized)
        self.assertEqual(timer.status, TimerStatus.DISABLED)
        self.assertEqual(timer.generation, 0)
        self.assertIsNone(timer.deadline)
        self.assertIsNone(timer.trigger_generation)

    def test_enable_creates_generation_one_and_clears_old_trigger(self):
        timer = create_initialized_timer("1")

        enabled = timer.enable(duration_seconds=30, now_seconds=10)

        self.assertEqual(enabled.generation, 1)
        self.assertEqual(enabled.status, TimerStatus.RUNNING)
        self.assertEqual(enabled.deadline, 40)
        self.assertIsNone(enabled.trigger_generation)

    def test_reenable_creates_new_generation_from_triggered_state(self):
        timer = create_initialized_timer("1").enable(0, 0)
        triggered = timer.commit_expiry()

        restarted = triggered.enable(30, 5)

        self.assertEqual(triggered.status, TimerStatus.TRIGGERED)
        self.assertEqual(restarted.generation, 2)
        self.assertEqual(restarted.status, TimerStatus.RUNNING)
        self.assertEqual(restarted.deadline, 35)
        self.assertIsNone(restarted.trigger_generation)

    def test_disable_invalidates_generation_and_clears_trigger(self):
        timer = create_initialized_timer("1").enable(5, 0).commit_expiry()

        disabled = timer.disable()

        self.assertEqual(disabled.generation, 2)
        self.assertEqual(disabled.status, TimerStatus.DISABLED)
        self.assertIsNone(disabled.deadline)
        self.assertIsNone(disabled.trigger_generation)
        self.assertFalse(read_timer_triggered(disabled))

    def test_current_generation_trigger_read_is_non_consuming(self):
        timer = create_initialized_timer("1").enable(0, 0).commit_expiry()

        self.assertTrue(read_timer_triggered(timer))
        self.assertTrue(read_timer_triggered(timer))
        self.assertEqual(timer.status, TimerStatus.TRIGGERED)

    def test_stale_pending_expiry_cannot_trigger_new_generation(self):
        timer = create_initialized_timer("1").enable(1, 0)
        pending = timer.stage_expiry(1)
        restarted = timer.disable().enable(30, 1)

        self.assertEqual(pending.generation, 1)
        self.assertEqual(restarted.generation, 3)
        self.assertFalse(restarted.can_commit_pending_expiry(pending))

    def test_runtime_state_does_not_expose_mismatched_trigger_generation(self):
        timer = TimerRuntimeState(
            timer_id="7",
            initialized=True,
            generation=4,
            status=TimerStatus.TRIGGERED,
            deadline=None,
            trigger_generation=3,
        )

        self.assertFalse(read_timer_triggered(timer))


if __name__ == "__main__":
    unittest.main()
