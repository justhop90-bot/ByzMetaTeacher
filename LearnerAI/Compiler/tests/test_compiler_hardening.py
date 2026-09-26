"""Hardening tests for compiler/native/community contract edges."""
import unittest
from pathlib import Path

from Compiler.compiler import compile_source
from Compiler.errors import CompileError
from Compiler.ir import GoalRole, GoalSlotRequest, SemanticId, StorageRequestId
from Compiler.primitives import default_de_registry
from Compiler.runtime_binding import (
    BindingContext,
    BindingManifest,
    GoalId,
    GoalSlot,
    RuntimeBinder,
)


class NestedAndNativeContractTests(unittest.TestCase):
    def test_nested_logical_arity_is_checked_recursively(self):
        source = """
        demand nested {
            require (and (or (current-age >= feudal-age) (current-age >= castle-age) (current-age >= imperial-age)) (current-age >= dark-age))
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        with self.assertRaisesRegex(
            CompileError,
            "logical operator 'or' requires 2 operands",
        ):
            compile_source(source)

    def test_logical_operator_cannot_be_an_action(self):
        source = """
        demand compound-action {
            require (can-build castle)
            action (and (build castle) (build town-center))
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        with self.assertRaisesRegex(CompileError, "action must be one native action"):
            compile_source(source)

    def test_known_native_command_without_semantic_adapter_is_rejected_explicitly(self):
        source = """
        demand raw-command {
            require (true)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        with self.assertRaisesRegex(CompileError, "no Basilisk semantic adapter"):
            compile_source(source)

    def test_checked_in_ai_ref_schema_is_authoritative_for_native_arity(self):
        registry = default_de_registry()
        search_state = registry.require_native("up-get-search-state")
        self.assertEqual(search_state.parameter_count, 1)
        self.assertEqual(search_state.parameters[0].type, "Goal")
        with self.assertRaisesRegex(ValueError, "expects exactly 1 argument"):
            registry.validate_native_signature("up-get-search-state", 2)

    def test_schema_load_is_stable_from_explicit_repo_path(self):
        schema_path = (
            Path(__file__).resolve().parents[3]
            / "docs"
            / "reference"
            / "inventories"
            / "airef-command-schema.json"
        )
        registry = default_de_registry(schema_path)
        self.assertEqual(registry.native("build").parameter_count, 1)
        self.assertEqual(registry.native("build").command_type, "Action")


class BindingHardeningTests(unittest.TestCase):
    def _request(self, source_unit, name):
        semantic_id = SemanticId(source_unit, name)
        return GoalSlotRequest(
            StorageRequestId(semantic_id, "lifecycle"),
            GoalRole.LIFECYCLE_STATE,
        )

    def test_existing_bindings_are_self_consistent(self):
        request_a = self._request("z.basilisk", "late")
        request_b = self._request("a.basilisk", "early")
        with self.assertRaisesRegex(ValueError, "duplicate existing binding GoalId"):
            RuntimeBinder().bind(
                (request_a, request_b),
                BindingContext(
                    existing_bindings=(
                        (
                            request_a.request_id,
                            GoalSlot(GoalId(1200), GoalRole.LIFECYCLE_STATE, "a"),
                        ),
                        (
                            request_b.request_id,
                            GoalSlot(GoalId(1200), GoalRole.LIFECYCLE_STATE, "b"),
                        ),
                    )
                ),
            )

    def test_new_binding_never_collides_with_existing_manifest(self):
        existing_request = self._request("z.basilisk", "late")
        new_request = self._request("a.basilisk", "early")
        result = RuntimeBinder(base_goal=1000).bind(
            (existing_request, new_request),
            BindingContext(
                existing_bindings=(
                    (
                        existing_request.request_id,
                        GoalSlot(
                            GoalId(1000),
                            GoalRole.LIFECYCLE_STATE,
                            "existing",
                        ),
                    ),
                )
            ),
        )
        self.assertEqual(
            result.binding_for(existing_request.request_id).id.value,
            1000,
        )
        self.assertEqual(
            result.binding_for(new_request.request_id).id.value,
            1001,
        )

    def test_binding_manifest_round_trip_is_deterministic(self):
        request = self._request("main.basilisk", "castle")
        result = RuntimeBinder(base_goal=1000).bind((request,))
        manifest = result.to_manifest(package_inventory_sha="abc123")
        text = manifest.to_json()
        restored = BindingManifest.from_json(text)
        self.assertEqual(restored.to_json(), text)
        self.assertEqual(
            restored.to_context().existing_bindings[0][1].id.value,
            1000,
        )


class EmitterBudgetAndArbitrationTests(unittest.TestCase):
    def test_build_actions_share_one_per_pass_claim(self):
        source = """
        demand castle {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        demand monastery {
            require (can-build monastery)
            action (build monastery)
            witness (building-type-count monastery > 0)
            release (building-type-count monastery > 0)
        }
        """
        output = compile_source(source)
        self.assertIn(
            "(defconst action-claim-build-pass-singleton 1002)",
            output,
        )
        self.assertEqual(
            output.count("(set-goal action-claim-build-pass-singleton 0)"),
            1,
        )
        self.assertEqual(
            output.count("(goal action-claim-build-pass-singleton 0)"),
            2,
        )
        self.assertEqual(
            output.count("(set-goal action-claim-build-pass-singleton 1)"),
            2,
        )

    def test_initialization_is_chunked(self):
        blocks = []
        for index in range(33):
            blocks.append(
                f"""
                demand demand-{index} {{
                    require (can-train spearman)
                    action (train spearman)
                    witness (unit-type-count spearman >= 2)
                    release (unit-type-count spearman >= 2)
                }}
                """
            )
        output = compile_source("\n".join(blocks))
        init_section = output[
            output.index("; Demand initialization"):
            output.index("; Pending diagnostics: demand-0")
        ]
        self.assertEqual(init_section.count("(defrule"), 2)
        self.assertEqual(init_section.count("(disable-self)"), 1)

    def test_emitter_rejects_rule_that_exceeds_engine_element_budget(self):
        requirements = "\n".join(
            "            require (can-train spearman)" for _ in range(31)
        )
        source = f"""
        demand too-wide {{
{requirements}
            action (train spearman)
            witness (unit-type-count spearman >= 2)
            release (unit-type-count spearman >= 2)
        }}
        """
        with self.assertRaisesRegex(
            CompileError,
            "EMITTER-RULE-ELEMENT-LIMIT",
        ):
            compile_source(source)


if __name__ == "__main__":
    unittest.main()
