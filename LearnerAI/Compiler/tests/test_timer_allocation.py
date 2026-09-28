import unittest

from Compiler.errors import CompileError
from Compiler.parser import parse
from Compiler.semantic.analyzer import analyze
from Compiler.primitives import default_de_registry
from Compiler.ir import GoalRole
from Compiler.ir.recurrent import TimerRequest, TimerState


class TimerAllocationIRTests(unittest.TestCase):
    def test_parser_accepts_symbolic_timer_declaration(self):
        source = """
        demand timer_gate {
            timer cooldown
            action (research ri-loom)
            witness (up-research-status c: ri-loom >= research-complete)
            release (research-available ri-loom)
        }
        """
        demand = parse(source, source_unit="timer-fixture")[0]

        self.assertEqual(len(demand.timer_states), 1)
        name, location = demand.timer_states[0]
        self.assertEqual(name, "cooldown")
        self.assertEqual(location.source_unit, "timer-fixture")

    def test_duplicate_timer_name_within_demand_is_rejected(self):
        source = """
        demand timer_gate {
            timer cooldown
            timer cooldown
            require (true)
            action (research ri-loom)
            witness (up-research-status c: ri-loom >= research-complete)
            release (research-available ri-loom)
        }
        """
        with self.assertRaisesRegex(CompileError, "duplicate timer state"):
            parse(source)

    def test_analyzer_creates_explicit_timer_request(self):
        source = """
        demand timer_gate {
            timer cooldown
            require (up-timer-status cooldown = timer-disabled)
            action (research ri-loom)
            witness (up-research-status c: ri-loom >= research-complete)
            release (research-available ri-loom)
        }
        """
        demand = analyze(parse(source, source_unit="timer-fixture"), default_de_registry())[0]

        self.assertEqual(len(demand.timer_states), 1)
        timer_state = demand.timer_states[0]
        self.assertIsInstance(timer_state, TimerState)
        self.assertIsInstance(timer_state.request, TimerRequest)
        self.assertEqual(timer_state.name, "cooldown")
        self.assertEqual(timer_state.request.request_id.purpose, "timer:cooldown")
        self.assertIs(timer_state.request.role, GoalRole.EXECUTION_MEMORY)
        self.assertEqual(
            timer_state.request.initialization_policy,
            "DISABLE_BEFORE_FIRST_USE",
        )
        self.assertEqual(
            timer_state.request.stability_key,
            "timer-state:v1:timer-fixture:timer_gate:cooldown",
        )

    def test_compiler_binds_timer_and_emits_symbolic_alias_and_initialization(self):
        from Compiler.compiler import compile_source

        source = """
        demand timer_gate {
            timer cooldown
            require (up-timer-status cooldown = timer-disabled)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        artifact = compile_source(source, source_unit="timer-fixture")

        self.assertIn("(defconst cooldown 1)", artifact)
        self.assertIn("(disable-timer cooldown)", artifact)

    def test_timer_binding_manifest_preserves_slot_and_initialization_policy(self):
        from Compiler.compiler import _binding_manifest_text, _compile_source_parts

        source = """
        demand timer_gate {
            timer cooldown
            require (up-timer-status cooldown = timer-disabled)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        artifact, bindings, context = _compile_source_parts(
            source,
            source_unit="timer-fixture",
            registry=default_de_registry(),
        )
        manifest = _binding_manifest_text(bindings, context)

        self.assertIn("(defconst cooldown 1)", artifact)
        self.assertIn("(disable-timer cooldown)", artifact)
        self.assertIn('"binding_kind": "TIMER"', manifest)
        self.assertIn('"timer_id": 1', manifest)
        self.assertIn(
            '"initialization_policy": "DISABLE_BEFORE_FIRST_USE"',
            manifest,
        )

    def test_timer_storage_is_deterministic_when_multiple_names_are_declared(self):
        from Compiler.compiler import compile_source

        source = """
        demand timer_gate {
            timer cooldown
            timer scouting-window
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        first = compile_source(source, source_unit="timer-fixture")
        second = compile_source(source, source_unit="timer-fixture")

        self.assertEqual(first, second)
        self.assertLess(
            first.index("(defconst cooldown"),
            first.index("(defconst scouting-window"),
        )

    def test_timer_names_are_compiler_owned_and_unique_across_demands(self):
        source = """
        demand first {
            timer cooldown
            require (true)
            action (research ri-loom)
            witness (up-research-status c: ri-loom >= research-complete)
            release (research-available ri-loom)
        }

        demand second {
            timer cooldown
            require (true)
            action (research ri-loom)
            witness (up-research-status c: ri-loom >= research-complete)
            release (research-available ri-loom)
        }
        """
        with self.assertRaisesRegex(CompileError, "duplicate compiler-owned Timer state"):
            analyze(parse(source), default_de_registry())


if __name__ == "__main__":
    unittest.main()
