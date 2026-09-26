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
    PackageStorageInventory,
    PackageStorageReservation,
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
    StrategicNumberInventory,
    StrategicNumberRequest,
    StrategicNumberSlot,
    TimerRequest,
    TimerSlot,
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
        result = RuntimeBinder(base_goal=41).bind(
            tuple(d.lifecycle.slot for d in self._ir())
        )
        self.assertEqual(len(result.records), 2)
        self.assertEqual(
            [record.binding.id.value for record in result.records],
            [41, 42],
        )

    def test_binder_rejects_goal_zero(self):
        with self.assertRaisesRegex(ValueError, "ordinary Goal storage base must be in range 41..512"):
            RuntimeBinder(base_goal=0).bind(tuple(d.lifecycle.slot for d in self._ir()))

    def test_binder_rejects_ordinary_goal_base_above_storage_pool(self):
        request = self._ir()[0].lifecycle.slot
        with self.assertRaisesRegex(ValueError, "ordinary Goal storage base must be in range 41..512"):
            RuntimeBinder(base_goal=513).bind((request,))

    def test_binder_rejects_goal_overflow(self):
        with self.assertRaisesRegex(ValueError, "unable to allocate lifecycle GoalId"):
            RuntimeBinder(base_goal=512).bind(tuple(d.lifecycle.slot for d in self._ir()))

    def test_binder_respects_occupied_goal_ids(self):
        result = RuntimeBinder(base_goal=41).bind(
            tuple(d.lifecycle.slot for d in self._ir()),
            BindingContext(occupied_goal_ids=frozenset({41})),
        )
        self.assertEqual(
            [record.binding.id.value for record in result.records],
            [42, 43],
        )

    def test_existing_binding_is_reused(self):
        request = self._ir()[0].lifecycle.slot
        existing = GoalSlot(
            id=GoalId(200),
            role=GoalRole.LIFECYCLE_STATE,
            provenance_id="existing",
        )
        result = RuntimeBinder(base_goal=41).bind(
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
        first = RuntimeBinder(base_goal=41).bind(requests)
        second = RuntimeBinder(base_goal=41).bind(requests)
        self.assertEqual(first, second)

    def test_storage_kinds_reserve_strategic_numbers_and_timers(self):
        from Compiler.runtime_binding import StorageKind
        values = {kind.value for kind in StorageKind}
        self.assertIn("STRATEGIC_NUMBER", values)
        self.assertIn("TIMER", values)

    def test_goal_id_and_goal_value_are_distinct_types(self):
        self.assertNotEqual(GoalId(41), GoalValue(41))
        self.assertNotEqual(type(GoalId(41)), type(GoalValue(41)))

    def test_current_lifecycle_encoding_is_lowering_only(self):
        slot = GoalSlot(
            id=GoalId(41),
            role=GoalRole.LIFECYCLE_STATE,
            provenance_id="test",
        )
        encoded = LifecycleEncoding.for_goal_slot(slot)
        self.assertEqual(encoded.released, GoalValue(0))
        self.assertEqual(encoded.active, GoalValue(1))
        self.assertEqual(encoded.pending, GoalValue(42))
        self.assertEqual(encoded.complete, GoalValue(43))

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



class PackageStorageInventoryTests(unittest.TestCase):
    def _reservation(self, kind, start, end, provenance):
        return PackageStorageReservation(
            kind=kind,
            start=start,
            end=end,
            provenance_id=provenance,
        )

    def test_inventory_rejects_goal_scalar_overlapping_goal_span(self):
        from Compiler.runtime_binding import StorageKind

        with self.assertRaisesRegex(ValueError, "overlapping Goal"):
            PackageStorageInventory(
                package_id="test-package",
                package_revision="r1",
                reservations=(
                    self._reservation(
                        StorageKind.GOAL_SLOT,
                        41,
                        41,
                        "scalar",
                    ),
                    self._reservation(
                        StorageKind.GOAL_SPAN,
                        41,
                        44,
                        "span",
                    ),
                ),
            )

    def test_inventory_hash_is_order_independent(self):
        from Compiler.runtime_binding import StorageKind

        reservations = (
            self._reservation(StorageKind.TIMER, 7, 7, "timer"),
            self._reservation(StorageKind.GOAL_SLOT, 41, 41, "goal"),
            self._reservation(StorageKind.STRATEGIC_NUMBER, 510, 510, "sn"),
        )
        first = PackageStorageInventory(
            package_id="test-package",
            package_revision="r1",
            reservations=reservations,
        )
        second = PackageStorageInventory(
            package_id="test-package",
            package_revision="r1",
            reservations=tuple(reversed(reservations)),
        )
        self.assertEqual(first.inventory_sha, second.inventory_sha)
        self.assertEqual(first.to_json(), second.to_json())

    def test_inventory_round_trip_preserves_fingerprint_and_reservations(self):
        from Compiler.runtime_binding import StorageKind

        inventory = PackageStorageInventory(
            package_id="test-package",
            package_revision="r1",
            reservations=(
                self._reservation(StorageKind.GOAL_SLOT, 40, 40, "goal"),
                self._reservation(StorageKind.GOAL_SPAN, 41, 42, "point"),
                self._reservation(StorageKind.STRATEGIC_NUMBER, 510, 510, "sn"),
                self._reservation(StorageKind.TIMER, 7, 7, "timer"),
            ),
        )
        restored = PackageStorageInventory.from_json(inventory.to_json())
        self.assertEqual(restored, inventory)
        self.assertEqual(restored.inventory_sha, inventory.inventory_sha)

    def test_inventory_rejects_tampered_fingerprint(self):
        from Compiler.runtime_binding import StorageKind

        inventory = PackageStorageInventory(
            package_id="test-package",
            package_revision="r1",
            reservations=(
                self._reservation(StorageKind.GOAL_SLOT, 41, 41, "goal"),
            ),
        )
        payload = inventory.to_dict()
        payload["inventory_sha"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "inventory fingerprint"):
            PackageStorageInventory.from_dict(payload)

    def test_binder_consumes_package_inventory_across_goal_sn_and_timer_namespaces(self):
        from Compiler.runtime_binding import StorageKind

        owner = SemanticId("test-package", "inventory")
        requests = (
            GoalSlotRequest(
                StorageRequestId(owner, "goal"),
                role=GoalRole.LIFECYCLE_STATE,
            ),
            GoalSpanRequest(
                StorageRequestId(owner, "point"),
                width=2,
                shape=GoalSpanKind.POINT_PAIR,
                contract_id="test.point",
                start_min=41,
                start_max=508,
            ),
            StrategicNumberRequest(
                StorageRequestId(owner, "sn"),
                why_not_goal="Native behavior is defined through a Strategic Number.",
                stability_key="sn",
            ),
            TimerRequest(
                StorageRequestId(owner, "timer"),
                initialization_policy="DISABLE_BEFORE_FIRST_USE",
                stability_key="timer",
            ),
        )
        inventory = PackageStorageInventory(
            package_id="test-package",
            package_revision="r1",
            reservations=(
                self._reservation(StorageKind.GOAL_SLOT, 40, 40, "goal"),
                self._reservation(StorageKind.GOAL_SPAN, 41, 42, "point"),
                self._reservation(StorageKind.STRATEGIC_NUMBER, 510, 510, "sn"),
                self._reservation(StorageKind.TIMER, 1, 1, "timer"),
            ),
        )
        sn_inventory = StrategicNumberInventory(
            inventory_sha="sn-inventory",
            documented_ids=frozenset({511}),
            candidate_ids=frozenset({510, 509}),
        )
        context = BindingContext.from_package_inventory(
            inventory,
            strategic_number_inventory=sn_inventory,
        )
        result = RuntimeBinder(base_goal=41).bind(requests, context)

        self.assertEqual(result.binding_for(requests[0].request_id).id.value, 43)
        self.assertEqual(result.binding_for(requests[1].request_id).start.value, 44)
        self.assertEqual(result.binding_for(requests[2].request_id).id, 509)
        self.assertEqual(result.binding_for(requests[3].request_id).id, 2)

    def test_binding_context_rejects_stale_package_inventory_sha(self):
        from Compiler.runtime_binding import StorageKind

        inventory = PackageStorageInventory(
            package_id="test-package",
            package_revision="r1",
            reservations=(
                self._reservation(StorageKind.GOAL_SLOT, 41, 41, "goal"),
            ),
        )
        with self.assertRaisesRegex(ValueError, "package inventory fingerprint mismatch"):
            BindingContext(
                package_inventory=inventory,
                package_inventory_sha="stale",
            )

    def test_inventory_rejects_missing_reservation_fields(self):
        from Compiler.runtime_binding import StorageKind

        with self.assertRaisesRegex(ValueError, "missing or extra fields"):
            PackageStorageInventory.from_dict(
                {
                    "format_version": 1,
                    "package_id": "test-package",
                    "package_revision": "r1",
                    "inventory_sha": "0" * 64,
                    "reservations": [
                        {
                            "kind": StorageKind.GOAL_SLOT.value,
                            "start": 41,
                            "end": 41,
                        }
                    ],
                }
            )

    def test_inventory_rejects_extra_reservation_fields(self):
        from Compiler.runtime_binding import StorageKind

        inventory = PackageStorageInventory.empty("test-package", "r1")
        payload = inventory.to_dict()
        payload["reservations"] = [
            {
                "kind": StorageKind.GOAL_SLOT.value,
                "start": 41,
                "end": 41,
                "provenance_id": "goal",
                "unexpected": True,
            }
        ]
        payload["inventory_sha"] = PackageStorageInventory(
            package_id="test-package",
            package_revision="r1",
            reservations=(
                PackageStorageReservation(
                    kind=StorageKind.GOAL_SLOT,
                    start=41,
                    end=41,
                    provenance_id="goal",
                ),
            ),
        ).inventory_sha
        with self.assertRaisesRegex(ValueError, "missing or extra fields"):
            PackageStorageInventory.from_dict(payload)

    def test_existing_binding_cannot_reuse_package_occupied_goal(self):
        from Compiler.runtime_binding import StorageKind

        request = GoalSlotRequest(
            StorageRequestId(SemanticId("test-package", "inventory"), "goal"),
            role=GoalRole.LIFECYCLE_STATE,
        )
        inventory = PackageStorageInventory(
            package_id="test-package",
            package_revision="r1",
            reservations=(
                self._reservation(StorageKind.GOAL_SLOT, 200, 200, "external-goal"),
            ),
        )
        existing = GoalSlot(
            id=GoalId(200),
            role=GoalRole.LIFECYCLE_STATE,
            provenance_id="existing",
        )
        context = BindingContext.from_package_inventory(
            inventory,
            existing_bindings=((request.request_id, existing),),
        )
        with self.assertRaisesRegex(ValueError, "conflicts with occupied GoalId"):
            RuntimeBinder().bind((request,), context)

    def test_binding_manifest_records_package_inventory_fingerprint(self):
        from Compiler.runtime_binding import StorageKind

        inventory = PackageStorageInventory(
            package_id="test-package",
            package_revision="r1",
            reservations=(
                self._reservation(StorageKind.GOAL_SLOT, 41, 41, "goal"),
            ),
        )
        context = BindingContext.from_package_inventory(inventory)
        request = GoalSlotRequest(
            StorageRequestId(SemanticId("test-package", "inventory"), "goal"),
            role=GoalRole.LIFECYCLE_STATE,
        )
        result = RuntimeBinder(base_goal=41).bind((request,), context)
        manifest = result.to_manifest(
            package_inventory_sha=context.package_inventory_sha,
            allocator_version=context.allocator_version,
        )
        self.assertEqual(manifest.package_inventory_sha, inventory.inventory_sha)
        self.assertEqual(
            BindingManifest.from_json(manifest.to_json()).package_inventory_sha,
            inventory.inventory_sha,
        )


class NativeMemoryBindingTests(unittest.TestCase):
    def _request_id(self, name: str) -> StorageRequestId:
        return StorageRequestId(SemanticId('generic.compiler', name), 'state')

    def test_strategic_number_requires_inventory(self):
        request = StrategicNumberRequest(
            self._request_id('sn'),
            why_not_goal='Goal semantics do not map onto engine behavior settings',
            stability_key='sn-test',
        )
        with self.assertRaisesRegex(ValueError, 'explicit AIRef inventory'):
            RuntimeBinder().bind((request,))

    def test_strategic_number_allocates_highest_candidate(self):
        request = StrategicNumberRequest(
            self._request_id('sn'),
            why_not_goal='Goal semantics do not map onto engine behavior settings',
            stability_key='sn-test',
        )
        inventory = StrategicNumberInventory(
            inventory_sha='inventory-test',
            documented_ids=frozenset({510}),
            candidate_ids=frozenset({509, 508}),
        )
        result = RuntimeBinder().bind(
            (request,),
            BindingContext(strategic_number_inventory=inventory),
        )
        binding = result.binding_for(request.request_id)
        self.assertIsInstance(binding, StrategicNumberSlot)
        self.assertEqual(binding.id, 509)

    def test_strategic_number_skips_occupied_candidate(self):
        request = StrategicNumberRequest(
            self._request_id('sn'),
            why_not_goal='A Goal is already allocated to lifecycle state',
            stability_key='sn-test',
        )
        inventory = StrategicNumberInventory(
            inventory_sha='inventory-test',
            documented_ids=frozenset({510}),
            candidate_ids=frozenset({509, 508}),
        )
        result = RuntimeBinder().bind(
            (request,),
            BindingContext(
                occupied_sn_ids=frozenset({509}),
                strategic_number_inventory=inventory,
            ),
        )
        self.assertEqual(result.binding_for(request.request_id).id, 508)

    def test_strategic_number_rejects_empty_why_not_goal(self):
        request = StrategicNumberRequest(
            self._request_id('sn'),
            why_not_goal='',
            stability_key='sn-test',
        )
        inventory = StrategicNumberInventory(
            inventory_sha='inventory-test',
            documented_ids=frozenset(),
            candidate_ids=frozenset({510}),
        )
        with self.assertRaisesRegex(ValueError, 'WHY_NOT_GOAL'):
            RuntimeBinder().bind(
                (request,),
                BindingContext(strategic_number_inventory=inventory),
            )

    def test_timer_allocates_lowest_free_id_and_records_initialization_policy(self):
        request = TimerRequest(
            self._request_id('timer'),
            initialization_policy='DISABLE_BEFORE_FIRST_USE',
            stability_key='timer-test',
        )
        result = RuntimeBinder().bind(
            (request,),
            BindingContext(occupied_timer_ids=frozenset({1, 2})),
        )
        binding = result.binding_for(request.request_id)
        self.assertIsInstance(binding, TimerSlot)
        self.assertEqual(binding.id, 3)
        self.assertEqual(binding.initialization_policy, 'DISABLE_BEFORE_FIRST_USE')

    def test_timer_rejects_out_of_range_occupied_id(self):
        request = TimerRequest(
            self._request_id('timer'),
            initialization_policy='DISABLE_BEFORE_FIRST_USE',
            stability_key='timer-test',
        )
        with self.assertRaisesRegex(ValueError, 'Timer id must be in range 1..50'):
            RuntimeBinder().bind(
                (request,),
                BindingContext(occupied_timer_ids=frozenset({51})),
            )

    def test_manifest_round_trip_preserves_sn_and_timer(self):
        sn = StrategicNumberRequest(
            self._request_id('sn'),
            why_not_goal='Goal cannot represent the engine strategic-number behavior',
            stability_key='sn-test',
        )
        timer = TimerRequest(
            self._request_id('timer'),
            initialization_policy='DISABLE_BEFORE_FIRST_USE',
            stability_key='timer-test',
        )
        inventory = StrategicNumberInventory(
            inventory_sha='inventory-test',
            documented_ids=frozenset({511}),
            candidate_ids=frozenset({510, 509}),
        )
        result = RuntimeBinder().bind(
            (sn, timer),
            BindingContext(strategic_number_inventory=inventory),
        )
        manifest = result.to_manifest(package_inventory_sha='package-test')
        restored = BindingManifest.from_json(manifest.to_json())
        restored_bindings = {
            record.request_id.owner.local_name: record.binding
            for record in restored.records
        }
        self.assertIsInstance(restored_bindings['sn'], StrategicNumberSlot)
        self.assertIsInstance(restored_bindings['timer'], TimerSlot)
        self.assertEqual(restored_bindings['sn'].id, 510)
        self.assertEqual(restored_bindings['timer'].id, 1)

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
        result = RuntimeBinder(base_goal=41).bind((request,))
        binding = result.binding_for(request.request_id)
        self.assertIsInstance(binding, GoalSpan)
        self.assertEqual(binding.start.value, 41)
        self.assertEqual(binding.width, 4)
        self.assertEqual(binding.shape, GoalStorageShape.EXTENDED_4)

    def test_goal_span_skips_occupied_ids_and_intervals(self):
        request = self._span_request()
        result = RuntimeBinder(base_goal=41).bind(
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
