import unittest

from Compiler.clients.basilisk import ByzantineProfile, build_byzantine_strategy
from Compiler.ir.camp_control import (
    CampResource,
    default_byzantine_camp_controller,
    lower_byzantine_camp_controller,
)
from Compiler.ir.civ_profile import resolve_effective_civ


class ByzantineCampControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effective = resolve_effective_civ(
            ByzantineProfile.for_update_185872()
        )
        cls.profile = build_byzantine_strategy(cls.effective)

    def test_remote_widen_is_latched_until_remote_front_clears(self):
        plan = default_byzantine_camp_controller()
        lowered = lower_byzantine_camp_controller(plan, self.profile)

        for resource in CampResource:
            widen_id = f"camp-placement-widen-{resource.value}"
            rearm_id = f"camp-placement-rearm-{resource.value}"
            latch = f"camp-placement-widened-{resource.value}"

            self.assertIn(
                latch,
                tuple(state.identifier for state in lowered.states),
            )

            widen = next(
                rule for rule in lowered.rules if rule.identity == widen_id
            )
            widen_facts = tuple(fact.source for fact in widen.facts)
            widen_actions = tuple(action.source for action in widen.actions)

            self.assertIn(
                self.profile.observation(
                    f"camp-front-{resource.value}-remote"
                ).expression,
                widen_facts,
            )
            self.assertIn(f"(goal {latch} 0)", widen_facts)
            self.assertIn(
                f"(strategic-number "
                f"{'sn-lumber-camp-max-distance' if resource is CampResource.WOOD else 'sn-mining-camp-max-distance'} < 36)",
                widen_facts,
            )
            self.assertIn(
                f"(up-modify-sn "
                f"{'sn-lumber-camp-max-distance' if resource is CampResource.WOOD else 'sn-mining-camp-max-distance'} c:+ 4)",
                widen_actions,
            )
            self.assertIn(f"(set-goal {latch} 1)", widen_actions)

            rearm = next(
                rule for rule in lowered.rules if rule.identity == rearm_id
            )
            rearm_facts = tuple(fact.source for fact in rearm.facts)
            rearm_actions = tuple(action.source for action in rearm.actions)
            self.assertIn(
                f"(goal {latch} 1)",
                rearm_facts,
            )
            self.assertIn(
                f"(not {self.profile.observation(f'camp-front-{resource.value}-remote').expression})",
                rearm_facts,
            )
            self.assertEqual(
                rearm_actions,
                (f"(set-goal {latch} 0)",),
            )

    def test_shared_mining_distance_writer_remains_single_owned_native_sn(self):
        plan = default_byzantine_camp_controller()
        lowered = lower_byzantine_camp_controller(plan, self.profile)

        widening_actions = [
            action.source
            for rule in lowered.rules
            for action in rule.actions
            if action.head == "up-modify-sn"
        ]
        self.assertEqual(
            widening_actions.count(
                "(up-modify-sn sn-mining-camp-max-distance c:+ 4)"
            ),
            2,
        )
        states = [
            state.identifier
            for state in lowered.states
            if state.identifier == "sn-mining-camp-max-distance"
        ]
        self.assertEqual(len(states), 1)


if __name__ == "__main__":
    unittest.main()
