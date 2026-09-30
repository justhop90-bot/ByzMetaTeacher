import unittest

from Compiler.ir import duc as duc_ir
from Compiler.ast import Expression, SourceLocation
from Compiler.semantic.duc import analyze_duc
from Compiler.semantic.rule_execution import EffectiveRule, RuleAction, RulePassBehavior


def _rule(order, actions):
    location = SourceLocation(order, 1, "fixture.per")
    return EffectiveRule(
        rule_order=order,
        source_location=location,
        source_slice_ordinal=0,
        instance_id=f"fixture:{order}",
        facts=(Expression("(true)", "true", (), location),),
        actions=tuple(
            RuleAction(
                expression=Expression(
                    f"({head} {' '.join(args)})".rstrip(),
                    head,
                    tuple(args),
                    location,
                ),
                within_rule_order=index,
            )
            for index, (head, args) in enumerate(actions)
        ),
        pass_behavior=RulePassBehavior.RECURRENT,
        disable_self_action_index=None,
    )


class DucObjectLifecycleTests(unittest.TestCase):
    def _machine_type(self):
        lifecycle_type = getattr(duc_ir, "DucObjectLifecycle", None)
        self.assertIsNotNone(
            lifecycle_type,
            "DUC persistent-object lifecycle state machine is not implemented",
        )
        return lifecycle_type

    def test_discover_store_reacquire_validate_release_round_trip(self):
        lifecycle = self._machine_type()()
        lifecycle = lifecycle.discover()
        self.assertEqual(lifecycle.state.value, "DISCOVERED")

        lifecycle = lifecycle.store_id(identity_ref="goal:41")
        self.assertEqual(lifecycle.state.value, "STORED")
        self.assertEqual(lifecycle.identity_ref, "goal:41")

        lifecycle = lifecycle.reacquire_by_id(success=True)
        self.assertEqual(lifecycle.state.value, "REACQUIRED")

        lifecycle = lifecycle.validate(success=True)
        self.assertEqual(lifecycle.state.value, "VALIDATED")

        lifecycle = lifecycle.release()
        self.assertEqual(lifecycle.state.value, "STORED")

    def test_store_requires_identity(self):
        lifecycle = self._machine_type()().discover()
        with self.assertRaisesRegex(ValueError, "identity"):
            lifecycle.store_id()

    def test_validation_without_current_reacquisition_is_illegal(self):
        lifecycle = self._machine_type()().store_id(identity_ref="goal:41")
        with self.assertRaisesRegex(ValueError, "VALIDATE"):
            lifecycle.validate(success=True)

    def test_failed_native_reacquisition_invalidates_without_claiming_world_death(self):
        lifecycle = self._machine_type()().store_id(identity_ref="goal:41")
        lifecycle = lifecycle.reacquire_by_id(success=False)
        self.assertEqual(lifecycle.state.value, "INVALIDATED_NATIVE")
        self.assertNotEqual(lifecycle.state.value, "INVALIDATED_WORLD")
        self.assertEqual(lifecycle.identity_ref, "goal:41")

    def test_world_invalidation_requires_independent_witness(self):
        lifecycle = self._machine_type()().store_id(identity_ref="goal:41")
        with self.assertRaisesRegex(ValueError, "world witness"):
            lifecycle.invalidate_world(world_witness=False)

        lifecycle = lifecycle.invalidate_world(world_witness=True)
        self.assertEqual(lifecycle.state.value, "INVALIDATED_WORLD")

    def test_invalidated_handle_requires_fresh_discovery(self):
        lifecycle = self._machine_type()().store_id(identity_ref="goal:41")
        lifecycle = lifecycle.invalidate_native()
        with self.assertRaisesRegex(ValueError, "FRESH_DISCOVER"):
            lifecycle.release()

        lifecycle = lifecycle.fresh_discover()
        self.assertEqual(lifecycle.state.value, "DISCOVERED")
        self.assertIsNone(lifecycle.identity_ref)

    def test_search_target_is_discovered_state(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-set-target-object", ("search-local", "c:", "0")),
            )),
        ))

        target = report.final_state.target
        self.assertIsNotNone(target)
        lifecycle = target.object_refs[0].lifecycle
        self.assertEqual(lifecycle.state.value, "DISCOVERED")

    def test_object_data_id_read_stores_symbolic_identity_binding(self):
        location = SourceLocation(2, 1, "fixture.per")
        rule = _rule(1, (
            ("up-find-local", ("c:", "villager", "c:", "1")),
            ("up-set-target-object", ("search-local", "c:", "0")),
            ("up-get-object-data", ("object-data-id", "41")),
        ))
        report = analyze_duc((rule,))

        target = report.final_state.target
        self.assertIsNotNone(target)
        lifecycle = target.object_refs[0].lifecycle
        self.assertEqual(lifecycle.state.value, "STORED")
        self.assertEqual(lifecycle.identity_ref, "goal:41")

    def test_native_id_target_is_reacquired_from_bound_identity(self):
        report = analyze_duc((
            _rule(1, (
                ("up-set-target-by-id", ("c:", "93")),
            )),
        ))

        target = report.final_state.target
        self.assertIsNotNone(target)
        lifecycle = target.object_refs[0].lifecycle
        self.assertEqual(lifecycle.state.value, "REACQUIRED")
        self.assertEqual(lifecycle.identity_ref, "native:93")

    def test_reacquired_native_id_releases_to_stored_across_pass(self):
        first = analyze_duc((
            _rule(1, (
                ("up-set-target-by-id", ("c:", "93")),
            )),
        ))
        self.assertIsNotNone(first.next_pass_state.target)

        second = analyze_duc(
            (_rule(1, ()),),
            initial_state=first.next_pass_state,
        )

        target = second.final_state.target
        self.assertIsNotNone(target)
        self.assertEqual(
            target.object_refs[0].lifecycle.state.value,
            "STORED",
        )

    def test_symbolic_native_id_target_reacquires_from_goal_binding(self):
        report = analyze_duc((
            _rule(1, (
                ("up-set-target-by-id", ("g:", "41")),
            )),
        ))

        target = report.final_state.target
        self.assertIsNotNone(target)
        lifecycle = target.object_refs[0].lifecycle
        self.assertEqual(lifecycle.state.value, "REACQUIRED")
        self.assertEqual(lifecycle.identity_ref, "goal:41")

    def test_failed_target_establishment_does_not_create_lifecycle_handle(self):
        report = analyze_duc((
            _rule(1, (
                ("up-find-local", ("c:", "villager", "c:", "1")),
                ("up-set-target-object", ("search-local", "c:", "240")),
            )),
        ))

        self.assertIsNone(report.final_state.target)


if __name__ == "__main__":
    unittest.main()
