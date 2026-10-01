import unittest

from Compiler.clients.basilisk import ByzantineProfile, build_byzantine_castle_strategy
from Compiler.ir.civ_profile import resolve_effective_civ
from Compiler.ir.strategy_runtime import (
    EvidenceTruth,
    RuntimeObservationSnapshot,
    StrategicDemandRuntimeState,
    evaluate_strategy_runtime,
)
from Compiler.ir.counter_strategy import CounterThreatClass


class ByzantineCounterArbitrationTests(unittest.TestCase):
    def setUp(self):
        effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        self.effective = effective
        self.profile = build_byzantine_castle_strategy(effective)

    def test_byzantine_profile_declares_typed_counter_packages(self):
        self.assertEqual(
            tuple(package.identity for package in self.profile.counter_packages),
            (
                "MOUNTED_PRESSURE_FEUDAL",
                "RANGED_PRESSURE_FEUDAL",
                "MOUNTED_PRESSURE_CASTLE",
                "INFANTRY_PRESSURE_CASTLE",
            ),
        )
        self.assertEqual(
            tuple(package.threat_class for package in self.profile.counter_packages),
            (
                CounterThreatClass.MOUNTED,
                CounterThreatClass.RANGED,
                CounterThreatClass.MOUNTED,
                CounterThreatClass.INFANTRY,
            ),
        )

    def test_ranged_threat_activates_persistent_skirmisher_demand(self):
        snapshot = RuntimeObservationSnapshot(
            fact_results=(
                ("(current-age == feudal-age)", True),
                ("(players-unit-type-count any-enemy archer-line >= 3)", True),
                ("(can-train-with-escrow skirmisher-line)", True),
                ("(unit-type-count-total skirmisher-line < 4)", True),
            ),
        )
        state = evaluate_strategy_runtime(self.profile, self.effective, snapshot)

        self.assertIn(
            "RANGED_PRESSURE_FEUDAL",
            state.active_counter_packages,
        )
        self.assertEqual(
            state.demand_state("counter-ranged-skirmishers"),
            StrategicDemandRuntimeState.STRATEGIC_ACTIVE_EXECUTABLE,
        )

    def test_known_ranged_threat_with_unknown_production_stays_blocked(self):
        snapshot = RuntimeObservationSnapshot(
            fact_results=(
                ("(current-age == feudal-age)", True),
                ("(players-unit-type-count any-enemy archer-line >= 3)", True),
            ),
        )
        state = evaluate_strategy_runtime(self.profile, self.effective, snapshot)

        package = state.counter_package_state("RANGED_PRESSURE_FEUDAL")
        self.assertIs(package.truth, EvidenceTruth.TRUE)
        self.assertEqual(
            state.demand_state("counter-ranged-skirmishers"),
            StrategicDemandRuntimeState.STRATEGIC_ACTIVE_BLOCKED,
        )

    def test_unknown_ranged_observation_keeps_counter_package_unknown_and_demand_inactive(self):
        snapshot = RuntimeObservationSnapshot(
            fact_results=(("(current-age == feudal-age)", True),),
        )
        state = evaluate_strategy_runtime(self.profile, self.effective, snapshot)

        package = state.counter_package_state("RANGED_PRESSURE_FEUDAL")
        self.assertIs(package.truth, EvidenceTruth.UNKNOWN)
        self.assertEqual(
            state.demand_state("counter-ranged-skirmishers"),
            StrategicDemandRuntimeState.STRATEGIC_INACTIVE,
        )

    def test_mounted_feudal_pressure_selects_spear_screen_and_policy(self):
        snapshot = RuntimeObservationSnapshot(
            fact_results=(
                ("(current-age == feudal-age)", True),
                ("(players-unit-type-count any-enemy scout-cavalry-line >= 3)", True),
                ("(can-train-with-escrow spearman-line)", True),
                ("(unit-type-count-total spearman-line < 4)", True),
            ),
        )
        state = evaluate_strategy_runtime(self.profile, self.effective, snapshot)

        self.assertIn("MOUNTED_PRESSURE_FEUDAL", state.active_counter_packages)
        self.assertEqual(
            state.demand_state("counter-mounted-spears"),
            StrategicDemandRuntimeState.STRATEGIC_ACTIVE_EXECUTABLE,
        )

    def test_castle_infantry_pressure_selects_cataphract_response(self):
        snapshot = RuntimeObservationSnapshot(
            fact_results=(
                ("(current-age >= feudal-age)", True),
                ("(current-age >= castle-age)", True),
                ("(players-unit-type-count any-enemy militia-line >= 5)", True),
                ("(can-train-with-escrow cataphract)", True),
                ("(unit-type-count-total cataphract-line < 2)", True),
            ),
        )
        state = evaluate_strategy_runtime(self.profile, self.effective, snapshot)

        self.assertIn("INFANTRY_PRESSURE_CASTLE", state.active_counter_packages)
        self.assertEqual(
            state.demand_state("counter-castle-cataphracts"),
            StrategicDemandRuntimeState.STRATEGIC_ACTIVE_EXECUTABLE,
        )

    def test_counter_production_uses_concrete_train_and_witness_tokens(self):
        for demand_identity, expected_unit in (
            ("counter-castle-camels", "camel-rider"),
            ("counter-castle-cataphracts", "cataphract"),
        ):
            demand = self.profile.demand(demand_identity)
            execution = demand.execution_demands[0]
            self.assertEqual(execution.action, f"(train {expected_unit})")
            self.assertEqual(
                execution.witness,
                f"(unit-type-count {expected_unit} >= "
                f"{demand.target.minimum})",
            )

    def test_counter_package_selection_is_deterministic(self):
        snapshot = RuntimeObservationSnapshot(
            fact_results=(
                ("(current-age >= feudal-age)", True),
                ("(current-age >= castle-age)", True),
                ("(players-unit-type-count any-enemy knight-line >= 3)", True),
                ("(players-unit-type-count any-enemy militia-line >= 5)", True),
                ("(can-train-with-escrow camel-rider)", True),
                ("(unit-type-count-total camel-rider-line < 3)", True),
                ("(can-train-with-escrow cataphract-line)", True),
                ("(unit-type-count-total cataphract-line < 2)", True),
            ),
        )
        first = evaluate_strategy_runtime(self.profile, self.effective, snapshot)
        second = evaluate_strategy_runtime(self.profile, self.effective, snapshot)

        self.assertEqual(first.counter_package_states, second.counter_package_states)
        self.assertEqual(first.fingerprint, second.fingerprint)


if __name__ == "__main__":
    unittest.main()
