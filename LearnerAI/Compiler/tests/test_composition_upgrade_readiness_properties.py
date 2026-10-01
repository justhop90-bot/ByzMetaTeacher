"""Property-based regression tests for composition upgrade readiness.

The project intentionally keeps the property generator dependency-free.  The
compiler suite uses unittest, so these tests use deterministic seeded
generators with many arbitrary mixed-package cases rather than adding a new
test framework for one semantic algebra.
"""

from __future__ import annotations

import random
import unittest

from LearnerAI.Compiler.ir.counter_strategy import CompositionUpgradeRequirement
from LearnerAI.Compiler.ir.strategy_runtime import (
    CompositionUpgradeReadiness,
    EvidenceTruth,
    aggregate_composition_upgrade_readiness,
)


class CompositionUpgradeReadinessPropertyTests(unittest.TestCase):
    ITERATIONS = 400

    @staticmethod
    def _requirement(identity: str, technology_id: int, observation_ref: str):
        return CompositionUpgradeRequirement(
            identity=identity,
            technology_id=technology_id,
            observation_ref=observation_ref,
        )

    @classmethod
    def _generate_case(cls, rng: random.Random):
        package_count = rng.randint(1, 8)
        package_ids = [f"package-{index}" for index in range(package_count)]
        identity_pool = [f"upgrade-{index:02d}" for index in range(rng.randint(1, 14))]

        canonical: dict[str, CompositionUpgradeRequirement] = {}
        package_requirements: dict[str, tuple[CompositionUpgradeRequirement, ...]] = {}

        for package_id in package_ids:
            requirements: list[CompositionUpgradeRequirement] = []
            for _ in range(rng.randint(0, 7)):
                identity = rng.choice(identity_pool)
                requirement = canonical.get(identity)
                if requirement is None:
                    requirement = cls._requirement(
                        identity=identity,
                        technology_id=rng.randint(1, 4000),
                        observation_ref=f"research-completed-{identity}",
                    )
                    canonical[identity] = requirement
                if requirement not in requirements:
                    requirements.append(requirement)
            rng.shuffle(requirements)
            package_requirements[package_id] = tuple(requirements)

        selected = [package_id for package_id in package_ids if rng.choice((True, False))]
        if not selected:
            selected = [rng.choice(package_ids)]

        # Deliberately permit duplicate selected package identities.  They must
        # not change semantic output.
        if rng.choice((True, False)):
            selected.append(rng.choice(selected))
        rng.shuffle(selected)

        requirement_truths = {
            identity: rng.choice(
                (EvidenceTruth.TRUE, EvidenceTruth.FALSE, EvidenceTruth.UNKNOWN)
            )
            for identity in canonical
            if rng.choice((True, False))
        }

        return selected, package_requirements, requirement_truths, canonical

    @staticmethod
    def _expected_requirements(selected, package_requirements, canonical):
        identities = {
            requirement.identity
            for package_id in set(selected)
            for requirement in package_requirements[package_id]
        }
        return tuple(
            sorted(
                (canonical[identity] for identity in identities),
                key=lambda item: (
                    item.technology_id,
                    item.identity,
                    item.observation_ref,
                ),
            )
        )

    @staticmethod
    def _expected_status(requirements, truths):
        values = tuple(
            truths.get(requirement.identity, EvidenceTruth.UNKNOWN)
            for requirement in requirements
        )
        if any(value is EvidenceTruth.UNKNOWN for value in values):
            return CompositionUpgradeReadiness.UNKNOWN
        if any(value is EvidenceTruth.FALSE for value in values):
            return CompositionUpgradeReadiness.BLOCKED
        return CompositionUpgradeReadiness.READY

    def test_property_tri_state_matches_three_valued_conjunction(self):
        rng = random.Random(0xA02E7)
        for case_index in range(self.ITERATIONS):
            selected, package_requirements, truths, canonical = self._generate_case(rng)
            with self.subTest(case_index=case_index):
                state = aggregate_composition_upgrade_readiness(
                    tuple(selected),
                    package_requirements,
                    truths,
                )
                expected_requirements = self._expected_requirements(
                    selected,
                    package_requirements,
                    canonical,
                )
                self.assertEqual(
                    state.status,
                    self._expected_status(expected_requirements, truths),
                )
                self.assertEqual(
                    tuple(item.requirement for item in state.requirements),
                    expected_requirements,
                )

    def test_property_requirement_union_is_semantically_deduplicated(self):
        rng = random.Random(0xD3D0F)
        for case_index in range(self.ITERATIONS):
            selected, package_requirements, truths, canonical = self._generate_case(rng)
            with self.subTest(case_index=case_index):
                state = aggregate_composition_upgrade_readiness(
                    tuple(selected),
                    package_requirements,
                    truths,
                )
                identities = tuple(
                    item.requirement.identity for item in state.requirements
                )
                self.assertEqual(
                    len(identities),
                    len(set(identities)),
                )
                expected_ids = {
                    requirement.identity
                    for package_id in set(selected)
                    for requirement in package_requirements[package_id]
                }
                self.assertEqual(set(identities), expected_ids)
                for identity in expected_ids:
                    self.assertEqual(
                        sum(item.requirement.identity == identity for item in state.requirements),
                        1,
                    )

    def test_property_requirement_order_is_independent_of_input_order(self):
        rng = random.Random(0x0FD3)
        for case_index in range(self.ITERATIONS):
            selected, package_requirements, truths, canonical = self._generate_case(rng)

            shuffled_selected = list(selected)
            rng.shuffle(shuffled_selected)

            shuffled_requirements = {
                package_id: tuple(
                    rng.sample(
                        list(requirements),
                        k=len(requirements),
                    )
                )
                for package_id, requirements in package_requirements.items()
            }

            shuffled_truths = dict(
                rng.sample(
                    list(truths.items()),
                    k=len(truths),
                )
            )

            first = aggregate_composition_upgrade_readiness(
                tuple(selected),
                package_requirements,
                truths,
            )
            second = aggregate_composition_upgrade_readiness(
                tuple(shuffled_selected),
                shuffled_requirements,
                shuffled_truths,
            )

            with self.subTest(case_index=case_index):
                self.assertEqual(first, second)
                self.assertEqual(
                    tuple(
                        (
                            item.requirement.technology_id,
                            item.requirement.identity,
                            item.requirement.observation_ref,
                        )
                        for item in first.requirements
                    ),
                    tuple(
                        sorted(
                            (
                                item.requirement.technology_id,
                                item.requirement.identity,
                                item.requirement.observation_ref,
                            )
                            for item in first.requirements
                        )
                    ),
                )

    def test_property_duplicate_selected_package_is_semantically_irrelevant(self):
        rng = random.Random(0xD0B)
        for case_index in range(self.ITERATIONS):
            selected, package_requirements, truths, _ = self._generate_case(rng)
            unique_selected = tuple(sorted(set(selected)))
            duplicated_selected = list(selected)
            duplicated_selected.extend(selected[: rng.randint(0, len(selected))])
            rng.shuffle(duplicated_selected)

            first = aggregate_composition_upgrade_readiness(
                unique_selected,
                package_requirements,
                truths,
            )
            second = aggregate_composition_upgrade_readiness(
                tuple(duplicated_selected),
                package_requirements,
                truths,
            )

            with self.subTest(case_index=case_index):
                self.assertEqual(first, second)

    def test_property_conflicting_duplicate_definitions_always_fail_closed_at_structure_boundary(self):
        rng = random.Random(0xC0FF)
        for case_index in range(self.ITERATIONS):
            identity = f"upgrade-{case_index:04d}"
            first = self._requirement(
                identity,
                technology_id=rng.randint(1, 1000),
                observation_ref=f"research-completed-{identity}",
            )
            second = self._requirement(
                identity,
                technology_id=first.technology_id,
                observation_ref=f"research-completed-{identity}-different",
            )
            if second.observation_ref == first.observation_ref:
                raise AssertionError("generator failed to create a conflicting observation")
            package_requirements = {
                "primary": (first,),
                "supporting": (second,),
            }

            with self.subTest(case_index=case_index):
                with self.assertRaisesRegex(
                    ValueError,
                    "conflicting composition upgrade requirement",
                ):
                    aggregate_composition_upgrade_readiness(
                        ("primary", "supporting"),
                        package_requirements,
                        {identity: EvidenceTruth.TRUE},
                    )

    def test_property_missing_truth_is_unknown_for_every_arbitrary_requirement_union(self):
        rng = random.Random(0xA11)
        for case_index in range(self.ITERATIONS):
            selected, package_requirements, truths, canonical = self._generate_case(rng)

            expected_requirements = self._expected_requirements(
                selected,
                package_requirements,
                canonical,
            )
            if expected_requirements:
                missing_identity = rng.choice(
                    [item.identity for item in expected_requirements]
                )
                truths = dict(truths)
                truths.pop(missing_identity, None)

                state = aggregate_composition_upgrade_readiness(
                    tuple(selected),
                    package_requirements,
                    truths,
                )

                with self.subTest(case_index=case_index, identity=missing_identity):
                    self.assertEqual(
                        state.status,
                        CompositionUpgradeReadiness.UNKNOWN,
                    )
                    self.assertTrue(
                        any(
                            item.requirement.identity == missing_identity
                            and item.truth is EvidenceTruth.UNKNOWN
                            for item in state.requirements
                        )
                    )

    def test_property_empty_selected_union_is_always_ready(self):
        rng = random.Random(0xE7)
        for case_index in range(self.ITERATIONS):
            with self.subTest(case_index=case_index):
                state = aggregate_composition_upgrade_readiness((), {}, {})
                self.assertEqual(state.status, CompositionUpgradeReadiness.READY)
                self.assertEqual(state.selected_packages, ())
                self.assertEqual(state.requirements, ())


if __name__ == "__main__":
    unittest.main()
