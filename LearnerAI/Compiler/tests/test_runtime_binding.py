import unittest

from Compiler.ast import DemandNode, SourceLocation
from Compiler.ir import (
    GoalRole,
    GoalSlotRequest,
    GoalSpanKind,
    GoalSpanRequest,
    LifecycleState,
    SemanticDemand,
    SemanticId,
)
from Compiler.parser import parse
from Compiler.primitives import default_de_registry
from Compiler.runtime_binding import (
    BindingContext,
    BindingManifest,
    GoalId,
    GoalSlot,
    GoalSpan,
    GoalValue,
    LifecycleEncoding,
    NativeParameterContract,
    NativeParameterKind,
    NativeStorageContract,
    RuntimeBinder,
    StorageRequestId,
    GoalStorageShape,
    VolatileGoalPool,
)
from Compiler.semantic import analyze


EXAMPLES = """
demand castle {
    require (can-build castle)
    action (build castle)
    witness (building-type-count castle > 0)
    release (building-type-count castle > 0)
}

demand defensive-spearmen {
    require (can-train spearman)
    action (train spearman)
    witness (unit-type-count spearman >= 2)
    release (unit-type-count spearman >= 2)
}
"""


class RuntimeBindingTests(unittest.TestCase):
    def _ir(self):
        return analyze(parse(EXAMPLES), default_de_registry())

    def test_semantic_demand_has_one_lifecycle_request_per_demand(self):
        ir = self._ir()
        self.assertEqual(len(ir), 2)
        self.assertTrue(all(d.lifecycle.slot.request_id for d in ir))
        self.assertEqual(
            [d.lifecycle.slot.request_id.purpose for d in ir],
            ["lifecycle", "lifecycle"],
        )
        self.assertFalse(any(isinstance(v, int) for d in ir for v in vars(d).values()))

    def test_lifecycle_request_contains_no_resolved_goal_id(self):
        demand = self._ir()[0]
        request = demand.lifecycle.slot
        self.assertIsInstance(request, GoalSlotRequest)
        self.assertFalse(hasattr(request, "goal_id"))
        self.assertFalse(hasattr(request, "value"))

    def test_lifecycle_states_are_values_not_storage(self):
        demand = self._ir()[0]
        self.assertEqual(demand.lifecycle.initial_state, LifecycleState.ACTIVE)
        self.assertIsInstance(demand.lifecycle.initial_state, LifecycleState)
        self.assertNotIsInstance(demand.lifecycle.initial_state, GoalId)
        self.assertNotIsInstance(demand.lifecycle.initial_state, GoalValue)

    def test_binder_allocates_one_goal_slot_per_lifecycle_request(self):
        result = RuntimeBinder(base_goal=1000).bind(
            tuple(d.lifecycle.slot for d in self._ir())
        )
        self.assertEqual(len(result.records), 2)
        self.assertEqual(
            [record.binding.id.value for record in result.records],
            [1000, 1001],
        )

    def test_binder_rejects_goal_zero(self):
        with self.assertRaisesRegex(ValueError, "GoalId base must be in range 1..16000"):
            RuntimeBinder(base_goal=0).bind(tuple(d.lifecycle.slot for d in self._ir()))

    def test_binder_rejects_lifecycle_goal_without_encoding_headroom(self):
        request = self._ir()[0].lifecycle.slot
        with self.assertRaisesRegex(ValueError, "lifecycle GoalId must leave room"):
            RuntimeBinder(base_goal=16000).bind((request,))

    def test_binder_rejects_goal_overflow(self):
        with self.assertRaisesRegex(ValueError, "unable to allocate lifecycle GoalId"):
            RuntimeBinder(base_goal=16000).bind(tuple(d.lifecycle.slot for d in self._ir()))

    def test_binder_respects_occupied_goal_ids(self):
        result = RuntimeBinder(base_goal=1000).bind(
            tuple(d.lifecycle.slot for d in self._ir()),
            BindingContext(occupied_goal_ids=frozenset({1000})),
        )
        self.assertEqual(
            [record.binding.id.value for record in result.records],
            [1001, 1002],
        )

    def test_existing_binding_is_reused(self):
        request = self._ir()[0].lifecycle.slot
        existing = GoalSlot(
            id=GoalId(1200),
            role=GoalRole.LIFECYCLE_STATE,
            provenance_id="existing",
        )
        result = RuntimeBinder(base_goal=1000).bind(
            (request,),
            BindingContext(existing_bindings=((request.request_id, existing),)),
        )
        self.assertEqual(result.binding_for(request.request_id), existing)

    def test_native_four_goal_contract_uses_explicit_bounds(self):
        contract = NativeStorageContract(
            contract_id="up-get-search-state.start",
            command="up-get-search-state",
            parameters=(
                NativeParameterContract(
                    index=0,
                    kind=NativeParameterKind.GOAL_SPAN_START,
                    width=4,
                    contiguous=True,
                    writes=True,
                ),
            ),
            shape=GoalStorageShape.EXTENDED_4,
            start_min=41,
            start_max=508,
        )
        contract.validate_start(41)
        contract.validate_start(508)
        with self.assertRaisesRegex(ValueError, "minimum 41"):
            contract.validate_start(40)
        with self.assertRaisesRegex(ValueError, "maximum 508"):
            contract.validate_start(509)

    def test_same_requests_bind_deterministically(self):
        requests = tuple(d.lifecycle.slot for d in self._ir())
        first = RuntimeBinder(base_goal=1000).bind(requests)
        second = RuntimeBinder(base_goal=1000).bind(requests)
        self.assertEqual(first, second)

    def test_storage_kinds_reserve_strategic_numbers_and_timers(self):
        from Compiler.runtime_binding import StorageKind
        values = {kind.value for kind in StorageKind}
        self.assertIn("STRATEGIC_NUMBER", values)
        self.assertIn("TIMER", values)

    def test_goal_id_and_goal_value_are_distinct_types(self):
        self.assertNotEqual(GoalId(1000), GoalValue(1000))
        self.assertNotEqual(type(GoalId(1000)), type(GoalValue(1000)))

    def test_current_lifecycle_encoding_is_lowering_only(self):
        slot = GoalSlot(
            id=GoalId(1000),
            role="LIFECYCLE_STATE",
            provenance_id="test",
        )
        encoded = LifecycleEncoding.for_goal_slot(slot)
        self.assertEqual(encoded.released, GoalValue(0))
        self.assertEqual(encoded.active, GoalValue(1))
        self.assertEqual(encoded.pending, GoalValue(1001))
        self.assertEqual(encoded.complete, GoalValue(1002))

    def test_native_parameter_contract_distinguishes_storage_argument_families(self):
        goal = NativeParameterContract(
            index=0,
            kind=NativeParameterKind.GOAL_ID,
        )
        span = NativeParameterContract(
            index=1,
            kind=NativeParameterKind.GOAL_SPAN_START,
            width=4,
            contiguous=True,
            writes=True,
        )
        self.assertNotEqual(goal.kind, span.kind)
        self.assertEqual(span.width, 4)
        self.assertTrue(span.contiguous)
        self.assertTrue(span.writes)

    def test_native_storage_contract_carries_command_signature(self):
        contract = NativeStorageContract(
            contract_id="up-get-search-state.start",
            command="up-get-search-state",
            parameters=(
                NativeParameterContract(
                    index=0,
                    kind=NativeParameterKind.GOAL_SPAN_START,
                    width=4,
                    contiguous=True,
                    writes=True,
                ),
            ),
            shape=GoalStorageShape.EXTENDED_4,
            start_min=41,
            start_max=508,
        )
        self.assertEqual(contract.command, "up-get-search-state")
        self.assertEqual(contract.shape, GoalStorageShape.EXTENDED_4)
        self.assertEqual(contract.start_min, 41)
        self.assertEqual(contract.start_max, 508)


if __name__ == "__main__":
    unittest.main()


class GoalSpanAndVolatileStorageTests(unittest.TestCase):
    def _span_request(self):
        return GoalSpanRequest(
            StorageRequestId(SemanticId("native.basilisk", "search"), "search-state"),
            role=GoalRole.NATIVE_OUTPUT,
            width=4,
            shape=GoalSpanKind.EXTENDED_4,
            contract_id="up-get-search-state.start",
            start_min=41,
            start_max=508,
        )

    def test_goal_span_request_allocates_one_contiguous_interval(self):
        request = self._span_request()
        result = RuntimeBinder(base_goal=1000).bind((request,))
        binding = result.binding_for(request.request_id)
        self.assertIsInstance(binding, GoalSpan)
        self.assertEqual(binding.start.value, 41)
        self.assertEqual(binding.width, 4)
        self.assertEqual(binding.shape, GoalStorageShape.EXTENDED_4)

    def test_goal_span_skips_occupied_ids_and_intervals(self):
        request = self._span_request()
        result = RuntimeBinder(base_goal=1000).bind(
            (request,),
            BindingContext(
                occupied_goal_ids=frozenset({41}),
                occupied_goal_intervals=((42, 45),),
            ),
        )
        binding = result.binding_for(request.request_id)
        self.assertEqual(binding.start.value, 46)

    def test_goal_span_rejects_invalid_width_for_shape(self):
        request = GoalSpanRequest(
            StorageRequestId(SemanticId("native.basilisk", "point"), "point"),
            role=GoalRole.NATIVE_OUTPUT,
            width=3,
            shape=GoalSpanKind.POINT_PAIR,
            contract_id="up-get-point.start",
            start_min=41,
            start_max=508,
        )
        with self.assertRaisesRegex(ValueError, "width 2"):
            RuntimeBinder().bind((request,))

    def test_existing_goal_span_binding_is_reused(self):
        request = self._span_request()
        existing = GoalSpan(
            start=GoalId(100),
            width=4,
            shape=GoalStorageShape.EXTENDED_4,
            provenance_id="existing",
        )
        result = RuntimeBinder().bind(
            (request,),
            BindingContext(existing_bindings=((request.request_id, existing),)),
        )
        self.assertEqual(result.binding_for(request.request_id), existing)

    def test_binding_manifest_round_trip_preserves_goal_span(self):
        request = self._span_request()
        result = RuntimeBinder().bind((request,))
        manifest = result.to_manifest(package_inventory_sha="abc123")
        restored = BindingManifest.from_json(manifest.to_json())
        binding = restored.to_context().existing_bindings[0][1]
        self.assertIsInstance(binding, GoalSpan)
        self.assertEqual(binding.start.value, 41)
        self.assertEqual(binding.width, 4)

    def test_volatile_goal_pool_is_deterministic_and_reusable_only_after_release(self):
        pool = VolatileGoalPool(900, 902)
        first = pool.checkout()
        second = pool.checkout()
        self.assertEqual((first.value, second.value), (900, 901))
        pool.release(first)
        self.assertEqual(pool.checkout().value, 900)

    def test_volatile_goal_pool_rejects_double_and_foreign_release(self):
        pool = VolatileGoalPool(900, 901)
        goal = pool.checkout()
        pool.release(goal)
        with self.assertRaisesRegex(ValueError, "not leased"):
            pool.release(goal)
        with self.assertRaisesRegex(ValueError, "outside pool"):
            pool.release(GoalId(902))
