import unittest

from Compiler.ir.civ_profile import resolve_effective_civ
from Compiler.clients.basilisk import (
    ByzantineProfile,
    build_byzantine_castle_strategy,
)
from Compiler.semantic.community_engine import EvidenceClass, PracticeStatus
from Compiler.semantic.policy_cause_graph import PolicyCauseRelation
from Compiler.semantic.policy_recipe import (
    PolicyField,
    PolicyOverride,
    PolicyRecipe,
    PolicyStrength,
    PolicyTerm,
    resolve_policy_recipe,
)


class ByzantinePolicyRecipeIntegrationTests(unittest.TestCase):
    def setUp(self):
        effective = resolve_effective_civ(ByzantineProfile.for_update_185872())
        self.profile = build_byzantine_castle_strategy(effective)

    def test_byzantine_strategy_profile_carries_policy_recipes(self):
        self.assertEqual(
            tuple(recipe.identity for recipe in self.profile.policy_recipes),
            (
                "RANGED_HOLD",
                "MOBILE_LOCAL_DEFENSE",
                "STRICT_RAID",
                "PROTECT_SIEGE",
                "DEER_PUSH",
            ),
        )

    def test_profile_resolution_validates_policy_recipe_catalog(self):
        from Compiler.clients.basilisk import resolve_strategy_profile

        resolved = resolve_strategy_profile(
            self.profile,
            resolve_effective_civ(ByzantineProfile.for_update_185872()),
        )
        self.assertEqual(
            tuple(item.recipe_identity for item in resolved.policy_resolutions),
            (
                "DEER_PUSH",
                "MOBILE_LOCAL_DEFENSE",
                "PROTECT_SIEGE",
                "RANGED_HOLD",
                "STRICT_RAID",
            ),
        )

    def test_strategy_profile_resolves_recipe_instance_through_causal_graph(self):
        resolution = self.profile.resolve_policy_recipe(
            "DEER_PUSH",
            bindings={"target": "deer-1", "target_kind": "deer"},
        )
        self.assertTrue(resolution.executable)
        self.assertEqual(len(resolution.causal_graph.nodes), len(resolution.diagnostics))
        self.assertEqual(resolution.suppressions, ())

    def test_ranged_hold_defaults_to_stand_ground(self):
        recipe = self.profile.policy_recipe("RANGED_HOLD")
        resolution = resolve_policy_recipe(recipe)
        self.assertTrue(resolution.executable)
        self.assertEqual(resolution.value_for(PolicyField.STANCE), "stand-ground")

    def test_mobile_local_defense_requires_route_and_attack_consumer(self):
        recipe = self.profile.policy_recipe("MOBILE_LOCAL_DEFENSE")
        unresolved = resolve_policy_recipe(
            recipe,
            bindings={"route": "woodline-patrol"},
        )
        self.assertFalse(unresolved.executable)
        self.assertIn("POL-004", {item.key.code for item in unresolved.diagnostics})

        resolved = resolve_policy_recipe(
            recipe,
            bindings={
                "route": "woodline-patrol",
                "attack_consumer": "raid-attack-1",
            },
        )
        self.assertTrue(resolved.executable)
        self.assertEqual(
            resolved.value_for(PolicyField.ATTACK_RETARGET),
            "patrol-style",
        )

    def test_strict_raid_constraint_rejects_patrol_style_override(self):
        recipe = self.profile.policy_recipe("STRICT_RAID")
        resolution = resolve_policy_recipe(
            recipe,
            overrides=(
                PolicyOverride(
                    PolicyField.ATTACK_RETARGET,
                    "patrol-style",
                ),
            ),
        )
        self.assertFalse(resolution.executable)
        codes = {item.key.code for item in resolution.diagnostics}
        self.assertIn("POL-002", codes)
        self.assertIn("POL-012", codes)
        self.assertTrue(
            any(
                suppression.via_edge is not None
                and suppression.via_edge.relation is PolicyCauseRelation.SUPERSEDES
                for suppression in resolution.suppressions
            )
        )

    def test_contradictory_strict_objective_and_patrol_style_suppresses_downstream_warning(self):
        recipe = PolicyRecipe(
            identity="TEST_STRICT_PATROL",
            terms=(
                PolicyTerm(
                    PolicyField.OBJECTIVE_DISCIPLINE,
                    "strict",
                    PolicyStrength.CONSTRAINT,
                    evidence=EvidenceClass.COMPILER_POLICY,
                    source_refs=("test",),
                ),
                PolicyTerm(
                    PolicyField.ATTACK_RETARGET,
                    "patrol-style",
                    PolicyStrength.DEFAULT,
                    evidence=EvidenceClass.COMMUNITY_PRACTICE,
                    source_refs=("test",),
                ),
            ),
        )
        resolution = resolve_policy_recipe(recipe)
        self.assertFalse(resolution.executable)
        self.assertIn("POL-001", {item.key.code for item in resolution.diagnostics})
        self.assertTrue(
            any(
                suppression.root_cause is not None
                and suppression.root_cause.key.code == "POL-001"
                for suppression in resolution.suppressions
            )
        )

    def test_missing_multiple_bindings_have_distinct_diagnostic_keys(self):
        recipe = self.profile.policy_recipe("PROTECT_SIEGE")
        resolution = resolve_policy_recipe(recipe)
        missing = tuple(
            item for item in resolution.diagnostics if item.key.code == "POL-004"
        )
        self.assertEqual(
            tuple(item.key.binding_identity for item in missing),
            ("target", "target_kind"),
        )

    def test_protect_siege_requires_siege_target_binding(self):
        recipe = self.profile.policy_recipe("PROTECT_SIEGE")
        missing = resolve_policy_recipe(
            recipe,
            bindings={"target": "cataphract"},
        )
        self.assertFalse(missing.executable)
        self.assertIn("POL-005", {item.key.code for item in missing.diagnostics})
        self.assertEqual(
            next(
                item.key.binding_identity
                for item in missing.diagnostics
                if item.key.code == "POL-005"
            ),
            "target_kind",
        )

        resolved = resolve_policy_recipe(
            recipe,
            bindings={"target": "onager-1", "target_kind": "siege"},
        )
        self.assertTrue(resolved.executable)
        self.assertEqual(
            resolved.value_for(PolicyField.RELATIONSHIP),
            "guard",
        )

    def test_deer_push_requires_deer_target_binding(self):
        recipe = self.profile.policy_recipe("DEER_PUSH")
        resolved = resolve_policy_recipe(
            recipe,
            bindings={"target": "deer-1", "target_kind": "deer"},
        )
        self.assertTrue(resolved.executable)
        self.assertEqual(
            resolved.value_for(PolicyField.RELATIONSHIP),
            "follow",
        )

    def test_open_evidence_fails_closed(self):

        recipe = PolicyRecipe(
            identity="TEST_OPEN",
            terms=(
                PolicyTerm(
                    field=PolicyField.STANCE,
                    value="defensive",
                    strength=PolicyStrength.DEFAULT,
                    evidence=EvidenceClass.OPEN_UNKNOWN,
                    practice_status=PracticeStatus.OPEN,
                    source_refs=("test-open",),
                ),
            ),
        )
        resolution = resolve_policy_recipe(recipe)
        self.assertFalse(resolution.executable)
        self.assertIn("POL-008", {item.key.code for item in resolution.diagnostics})

    def test_resolver_is_deterministic(self):
        recipe = self.profile.policy_recipe("DEER_PUSH")
        first = resolve_policy_recipe(
            recipe,
            bindings={"target": "deer-1", "target_kind": "deer"},
        )
        second = resolve_policy_recipe(
            recipe,
            bindings={"target": "deer-1", "target_kind": "deer"},
        )
        self.assertEqual(first, second)
        self.assertEqual(
            tuple(item.key for item in first.diagnostics),
            tuple(item.key for item in second.diagnostics),
        )


if __name__ == "__main__":
    unittest.main()
