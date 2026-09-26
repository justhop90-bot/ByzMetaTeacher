import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))
from Compiler.compiler import CompileError, compile_source
from Compiler.parser import parse
from Compiler.semantic import parse_expression

EXAMPLES = (Path(__file__).parents[1] / "examples" / "basics.basilisk").read_text(encoding="utf-8")

class CompilerTests(unittest.TestCase):
    def test_three_examples_parse(self):
        self.assertEqual([d.name for d in parse(EXAMPLES)], ["castle", "defensive-spearmen", "wheelbarrow"])

    def test_output_is_deterministic_and_has_separate_lifecycle_stages(self):
        a = compile_source(EXAMPLES)
        self.assertEqual(a, compile_source(EXAMPLES))
        self.assertIn("(set-goal demand-castle 1)", a)
        self.assertIn("(build castle)", a)
        self.assertIn("(set-goal demand-castle 1001)", a)
        self.assertIn("(set-goal demand-castle 1002)", a)
        self.assertIn("(set-goal demand-castle 0)", a)
        self.assertEqual(a.count("(defrule"), 10)

    def test_unknown_primitive_rejected(self):
        source = """
        demand bad {
            require (not-a-real-fact castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        with self.assertRaises(CompileError):
            compile_source(source)

    def test_action_must_be_action_primitive(self):
        source = """
        demand bad {
            require (can-build castle)
            action (can-build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        with self.assertRaises(CompileError):
            compile_source(source)

    def test_witness_cannot_be_feasibility(self):
        source = """
        demand bad {
            require (can-build castle)
            action (build castle)
            witness (can-build castle)
            release (building-type-count castle > 0)
        }
        """
        with self.assertRaises(CompileError):
            compile_source(source)

    def test_logical_arity_is_checked(self):
        source = """
        demand bad {
            require (and (can-build castle) (building-available castle) (can-build castle))
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        with self.assertRaises(CompileError):
            compile_source(source)

    def test_nested_logical_expression_is_supported(self):
        source = """
        demand castle {
            require (and (building-available castle) (can-build castle))
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        output = compile_source(source)
        self.assertIn("(and (building-available castle) (can-build castle))", output)

    def test_native_expression_parser_exposes_root_primitive(self):
        expr = parse_expression("(current-age >= castle)")
        self.assertEqual(expr.head, "current-age")
        self.assertEqual(expr.args, (">=", "castle"))

    def test_missing_witness_rejected(self):
        source = """
        demand bad {
            require (can-build castle)
            action (build castle)
            release (building-type-count castle > 0)
        }
        """
        with self.assertRaises(CompileError):
            compile_source(source)

    def test_native_per_expression_is_required(self):
        source = """
        demand bad {
            require can-build castle
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        with self.assertRaises(CompileError):
            compile_source(source)


    def test_lifecycle_rule_order_prevents_same_pass_collapse(self):
        output = compile_source(EXAMPLES)
        release = output.find("; Release: castle | COMPLETE -> RELEASED")
        witness = output.find("; Completion witness: castle | PENDING -> COMPLETE")
        action = output.find("; Demand: castle | ACTIVE -> PENDING")
        self.assertGreaterEqual(release, 0)
        self.assertGreaterEqual(witness, 0)
        self.assertGreaterEqual(action, 0)
        self.assertLess(release, witness)
        self.assertLess(witness, action)

    def test_lifecycle_needs_three_script_passes_when_witness_and_release_are_true(self):
        output = compile_source(EXAMPLES)

        def run_pass(goal: int, rule_order: tuple[str, ...]) -> int:
            for stage in rule_order:
                if stage == "release" and goal == 1002:
                    goal = 0
                elif stage == "witness" and goal == 1001:
                    goal = 1002
                elif stage == "action" and goal == 1:
                    goal = 1001
            return goal

        markers = {
            "release": output.find("; Release: castle | COMPLETE -> RELEASED"),
            "witness": output.find("; Completion witness: castle | PENDING -> COMPLETE"),
            "action": output.find("; Demand: castle | ACTIVE -> PENDING"),
        }
        self.assertTrue(all(index >= 0 for index in markers.values()))
        rule_order = tuple(stage for stage, _ in sorted(markers.items(), key=lambda item: item[1]))
        goal = 1
        states = []
        for _ in range(3):
            goal = run_pass(goal, rule_order)
            states.append(goal)

        self.assertEqual(states, [1001, 1002, 0])
        self.assertNotEqual(states[0], 0)
        self.assertNotEqual(states[1], 0)
    def test_castle_enters_pending_and_cannot_reissue_while_pending(self):
        output = compile_source(EXAMPLES)
        action_block = output[output.find("; Demand: castle | ACTIVE -> PENDING"):output.find("; Completion witness: castle")]
        self.assertIn("(build castle)", action_block)
        self.assertIn("(set-goal demand-castle 1001)", action_block)
        pending_block = output[output.find("; Completion witness: castle"):output.find("; Release: castle")]
        self.assertIn("(goal demand-castle 1001)", pending_block)
        self.assertNotIn("(build castle)", pending_block)

    def test_spearmen_pending_state_prevents_repeated_train(self):
        output = compile_source(EXAMPLES)
        action_block = output[output.find("; Demand: defensive-spearmen | ACTIVE -> PENDING"):output.find("; Completion witness: defensive-spearmen")]
        self.assertIn("(train spearman)", action_block)
        self.assertIn("(set-goal demand-defensive-spearmen 1004)", action_block)
        pending_block = output[output.find("; Completion witness: defensive-spearmen"):output.find("; Release: defensive-spearmen")]
        self.assertIn("(goal demand-defensive-spearmen 1004)", pending_block)
        self.assertNotIn("(train spearman)", pending_block)

    def test_wheelbarrow_pending_state_prevents_repeated_research(self):
        output = compile_source(EXAMPLES)
        action_block = output[output.find("; Demand: wheelbarrow | ACTIVE -> PENDING"):output.find("; Completion witness: wheelbarrow")]
        self.assertIn("(research ri-wheelbarrow)", action_block)
        self.assertIn("(set-goal demand-wheelbarrow 1007)", action_block)
        pending_block = output[output.find("; Completion witness: wheelbarrow"):output.find("; Release: wheelbarrow")]
        self.assertIn("(goal demand-wheelbarrow 1007)", pending_block)
        self.assertNotIn("(research ri-wheelbarrow)", pending_block)

    def test_pending_diagnostics_are_emitted_for_each_demand(self):
        output = compile_source(EXAMPLES)
        self.assertIn("; Pending diagnostics: castle", output)
        self.assertIn(
            "; PENDING-DIAGNOSTIC [INFO] PENDING-ACTION-GUARD: "
            "action is gated by active goal 1000 and cannot reissue from pending goal 1001",
            output,
        )
        self.assertIn(
            "; PENDING-DIAGNOSTIC [INFO] PENDING-WITNESS-GUARD: "
            "completion witness is evaluated only while pending goal 1001 is active",
            output,
        )
        self.assertIn(
            "; PENDING-DIAGNOSTIC [INFO] PENDING-RELEASE-GUARD: "
            "release is evaluated only after completion goal 1002 is reached",
            output,
        )

    def test_pending_diagnostics_are_deterministic(self):
        first = compile_source(EXAMPLES)
        second = compile_source(EXAMPLES)
        first_diags = [line for line in first.splitlines() if "PENDING-DIAGNOSTIC" in line]
        second_diags = [line for line in second.splitlines() if "PENDING-DIAGNOSTIC" in line]
        self.assertEqual(first_diags, second_diags)
        self.assertEqual(len(first_diags), 15)

    def test_pending_negative_repeated_action_is_guarded(self):
        source = """
        demand repeated {
            require (can-train spearman)
            action (train spearman)
            witness (unit-type-count spearman >= 1)
            release (unit-type-count spearman >= 1)
        }
        """
        output = compile_source(source)
        self.assertIn(
            "PENDING-ACTION-GUARD",
            output,
        )
        pending = output[output.find("; Completion witness: repeated"):output.find("; Release: repeated")]
        self.assertNotIn("(train spearman)", pending)

    def test_pending_negative_missing_witness_is_rejected(self):
        source = """
        demand missing {
            require (can-build castle)
            action (build castle)
            witness ()
            release (building-type-count castle > 0)
        }
        """
        with self.assertRaisesRegex(CompileError, "PENDING-WITNESS-MISSING"):
            compile_source(source)

    def test_pending_negative_premature_release_is_rejected(self):
        source = """
        demand premature {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (build castle)
        }
        """
        with self.assertRaisesRegex(CompileError, "PENDING-RELEASE-PREMATURE"):
            compile_source(source)

    def test_pending_negative_witness_cannot_fire_before_action(self):
        output = compile_source(EXAMPLES)
        action_end = output.find("; Completion witness: castle")
        witness_start = action_end
        witness_end = output.find("; Release: castle")
        witness_block = output[witness_start:witness_end]
        self.assertIn("(goal demand-castle 1001)", witness_block)
        self.assertNotIn("(goal demand-castle 1)", witness_block)
        self.assertNotIn("(set-goal demand-castle 1002)", output[:action_end])

    def test_pending_negative_completion_requires_pending_transition(self):
        output = compile_source(EXAMPLES)
        action_start = output.find("; Demand: castle | ACTIVE -> PENDING")
        witness_start = output.find("; Completion witness: castle")
        action_block = output[action_start:witness_start]
        witness_end = output.find("; Release: castle")
        witness_block = output[witness_start:witness_end]
        self.assertIn("(set-goal demand-castle 1001)", action_block)
        self.assertIn("(goal demand-castle 1001)", witness_block)
        self.assertIn("(set-goal demand-castle 1002)", witness_block)
        self.assertNotIn("(goal demand-castle 1)", witness_block)
        self.assertNotIn("(set-goal demand-castle 1002)", action_block)

    def test_release_requires_completed_state(self):
        output = compile_source(EXAMPLES)
        castle_release = output[output.find("; Release: castle"):output.find("; Demand: defensive-spearmen")]
        self.assertIn("(goal demand-castle 1002)", castle_release)
        self.assertIn("(set-goal demand-castle 0)", castle_release)
        self.assertNotIn("(goal demand-castle 1001)", castle_release)

    def test_pending_engine_fact_is_available_as_requirement(self):
        source = """
        demand castle {
            require (up-pending-objects c: castle < 1)
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        compile_source(source)

    def test_pending_and_total_state_cannot_be_completion_witness(self):
        for witness in (
            "(up-pending-objects c: castle >= 1)",
            "(building-type-count-total castle >= 1)",
            "(unit-type-count-total spearman >= 1)",
        ):
            source = f"""
            demand bad {{
                require (can-build castle)
                action (build castle)
                witness {witness}
                release (building-type-count castle > 0)
            }}
            """
            with self.assertRaisesRegex(CompileError, "completion witness"):
                compile_source(source)

    def test_escrow_capability_primitives_are_feasibility_facts(self):
        for capability, subject, action, witness in (
            ("can-build-with-escrow", "castle", "build castle", "building-type-count castle > 0"),
            ("can-train-with-escrow", "spearman-line", "train spearman-line", "unit-type-count spearman-line >= 1"),
            ("can-research-with-escrow", "ri-wheelbarrow", "research ri-wheelbarrow", "research-completed ri-wheelbarrow"),
        ):
            source = f"""
            demand capability {{
                require ({capability} {subject})
                action ({action})
                witness ({witness})
                release ({witness})
            }}
            """
            compile_source(source)


    def test_game_time_is_a_timing_primitive(self):
        expr = parse_expression("(game-time >= 600)")
        self.assertEqual(expr.head, "game-time")
        self.assertEqual(expr.args, (">=", "600"))

    def test_timing_only_action_is_rejected(self):
        source = """
        demand timed-spears {
            require (game-time >= 600)
            action (train spearman)
            witness (unit-type-count spearman >= 2)
            release (unit-type-count spearman >= 2)
        }
        """
        with self.assertRaisesRegex(CompileError, "TIMING-WITHOUT-WORLD-EVIDENCE"):
            compile_source(source)

    def test_timing_plus_world_observation_is_valid(self):
        source = """
        demand timed-spears {
            require (game-time >= 600)
            require (unit-type-count scout-unit >= 2)
            action (train spearman)
            witness (unit-type-count spearman >= 2)
            release (unit-type-count scout-unit == 0)
        }
        """
        output = compile_source(source)
        self.assertIn("(game-time >= 600)", output)
        self.assertIn("(unit-type-count scout-unit >= 2)", output)

    def test_timing_cannot_be_completion_witness(self):
        source = """
        demand timed-spears {
            require (unit-type-count scout-unit >= 2)
            action (train spearman)
            witness (game-time >= 600)
            release (unit-type-count scout-unit == 0)
        }
        """
        with self.assertRaisesRegex(CompileError, "completion witness"):
            compile_source(source)

    def test_timing_only_release_is_rejected(self):
        source = """
        demand timed-spears {
            require (unit-type-count scout-unit >= 2)
            action (train spearman)
            witness (unit-type-count spearman >= 2)
            release (game-time >= 900)
        }
        """
        with self.assertRaisesRegex(CompileError, "TIMING-RELEASE-WITHOUT-WORLD-EVIDENCE"):
            compile_source(source)


    def test_timing_inside_composite_requirement_still_requires_non_timing_evidence(self):
        source = """
        demand maa-archers {
            require (and (game-time >= 510) (current-age >= feudal-age))
            action (train archer)
            witness (unit-type-count archer >= 3)
            release (unit-type-count archer < 3)
        }
        """
        output = compile_source(source)
        self.assertIn("(and (game-time >= 510) (current-age >= feudal-age))", output)

    def test_timing_plus_specific_maa_observation_is_valid(self):
        source = """
        demand maa-response {
            require (game-time >= 510)
            require (unit-type-count man-at-arms >= 2)
            action (train archer)
            witness (unit-type-count archer >= 3)
            release (unit-type-count man-at-arms == 0)
        }
        """
        output = compile_source(source)
        self.assertIn("(game-time >= 510)", output)
        self.assertIn("(unit-type-count man-at-arms >= 2)", output)

    def test_timing_cannot_release_an_active_maa_response_by_clock(self):
        source = """
        demand maa-response {
            require (unit-type-count man-at-arms >= 2)
            action (train archer)
            witness (unit-type-count archer >= 3)
            release (and (game-time >= 750) (unit-type-count man-at-arms >= 2))
        }
        """
        with self.assertRaisesRegex(CompileError, "TIMING.*release"):
            compile_source(source)


    def test_timing_only_composite_requirement_is_rejected(self):
        source = """
        demand timed-maa {
            require (and (game-time >= 510) (game-time < 750))
            action (train archer)
            witness (unit-type-count archer >= 3)
            release (unit-type-count man-at-arms == 0)
        }
        """
        with self.assertRaisesRegex(CompileError, "TIMING-WITHOUT-WORLD-EVIDENCE"):
            compile_source(source)


    def test_dropsite_min_distance_is_a_positional_observation(self):
        expr = parse_expression("(dropsite-min-distance gold > 12)")
        self.assertEqual(expr.head, "dropsite-min-distance")
        self.assertEqual(expr.args, ("gold", ">", "12"))

    def test_tower_response_can_require_timing_maa_and_positional_evidence(self):
        source = """
        demand maa-tower-defense {
            require (game-time >= 510)
            require (unit-type-count man-at-arms >= 2)
            require (dropsite-min-distance gold > 12)
            require (can-build watch-tower)
            action (build watch-tower)
            witness (building-type-count watch-tower > 0)
            release (building-type-count watch-tower > 0)
        }
        """
        output = compile_source(source)
        self.assertIn("(game-time >= 510)", output)
        self.assertIn("(unit-type-count man-at-arms >= 2)", output)
        self.assertIn("(dropsite-min-distance gold > 12)", output)
        self.assertIn("(can-build watch-tower)", output)

    def test_positional_observation_cannot_be_completion_witness(self):
        source = """
        demand bad-tower {
            require (can-build watch-tower)
            action (build watch-tower)
            witness (dropsite-min-distance gold > 12)
            release (building-type-count watch-tower > 0)
        }
        """
        with self.assertRaisesRegex(CompileError, "completion witness"):
            compile_source(source)

    def test_cli_entrypoint_compiles_from_repository_root(self):
        repo = Path(__file__).resolve().parents[3]
        source = Path(__file__).resolve().parents[1] / "examples" / "basics.basilisk"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "Basilisk.per"
            run = subprocess.run(
                [sys.executable, str(Path(__file__).resolve().parents[1] / "compiler.py"), str(source), str(output)],
                cwd=repo, capture_output=True, text=True,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue(output.exists())
            self.assertIn("BASILISK GENERATED .PER", output.read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
