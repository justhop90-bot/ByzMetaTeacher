"""Property-based regression tests for composition upgrade readiness.

The compiler suite intentionally remains dependency-free and unittest-based.
Each generated case carries a deterministic seed and can be greedily shrunk
to a smaller semantic counterexample when a property fails.
"""

from __future__ import annotations

import random
import unittest
from dataclasses import dataclass

from LearnerAI.Compiler.ir.counter_strategy import CompositionUpgradeRequirement
from LearnerAI.Compiler.ir.strategy_runtime import (
    CompositionUpgradeReadiness,
    EvidenceTruth,
    aggregate_composition_upgrade_readiness,
)


@dataclass(frozen=True)
class _PropertyCase:
    selected_packages: tuple[str, ...]
    package_requirements: dict[
        str, tuple[CompositionUpgradeRequirement, ...]
    ]
    requirement_truths: dict[str, EvidenceTruth]

    @property
    def selected_package_set(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.selected_packages)))

    @property
    def requirements(self) -> tuple[CompositionUpgradeRequirement, ...]:
        unique: dict[str, CompositionUpgradeRequirement] = {}
        for package_id in self.selected_package_set:
            for requirement in self.package_requirements[package_id]:
                unique.setdefault(requirement.identity, requirement)
        return tuple(
            sorted(
                unique.values(),
                key=lambda item: (
                    item.technology_id,
                    item.identity,
                    item.observation_ref,
                ),
            )
        )

    def description(self) -> str:
        requirements = {
            package_id: [
                {
                    "identity": item.identity,
                    "technology_id": item.technology_id,
                    "observation_ref": item.observation_ref,
                }
                for item in self.package_requirements[package_id]
            ]
            for package_id in sorted(self.package_requirements)
        }
        truths = {
            identity: truth.value
            for identity, truth in sorted(self.requirement_truths.items())
        }
        return (
            "selected="
            + repr(self.selected_packages)
            + ", packages="
            + repr(requirements)
            + ", truths="
            + repr(truths)
        )


class CompositionUpgradeReadinessPropertyTests(unittest.TestCase):
    ITERATIONS = 400

    @staticmethod
    def _requirement(
        identity: str,
        technology_id: int,
        observation_ref: str,
    ) -> CompositionUpgradeRequirement:
        return CompositionUpgradeRequirement(
            identity=identity,
            technology_id=technology_id,
            observation_ref=observation_ref,
        )

    @classmethod
    def _generate_case(cls, rng: random.Random) -> _PropertyCase:
        package_count = rng.randint(1, 8)
        package_ids = [f"package-{index}" for index in range(package_count)]
        identity_pool = [
            f"upgrade-{index:02d}"
            for index in range(rng.randint(1, 14))
        ]

        canonical: dict[str, CompositionUpgradeRequirement] = {}
        package_requirements: dict[
            str, tuple[CompositionUpgradeRequirement, ...]
        ] = {}

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

        selected = [
            package_id
            for package_id in package_ids
            if rng.choice((True, False))
        ]
        if not selected:
            selected = [rng.choice(package_ids)]

        if rng.choice((True, False)):
            selected.append(rng.choice(selected))
        rng.shuffle(selected)

        requirement_truths = {
            identity: rng.choice(
                (
                    EvidenceTruth.TRUE,
                    EvidenceTruth.FALSE,
                    EvidenceTruth.UNKNOWN,
                )
            )
            for identity in canonical
            if rng.choice((True, False))
        }

        return _PropertyCase(
            selected_packages=tuple(selected),
            package_requirements=package_requirements,
            requirement_truths=requirement_truths,
        )

    @staticmethod
    def _expected_requirements(
        case: _PropertyCase,
    ) -> tuple[CompositionUpgradeRequirement, ...]:
        return case.requirements

    @staticmethod
    def _expected_status(
        requirements: tuple[CompositionUpgradeRequirement, ...],
        truths: dict[str, EvidenceTruth],
    ) -> CompositionUpgradeReadiness:
        values = tuple(
            truths.get(requirement.identity, EvidenceTruth.UNKNOWN)
            for requirement in requirements
        )
        if any(value is EvidenceTruth.UNKNOWN for value in values):
            return CompositionUpgradeReadiness.UNKNOWN
        if any(value is EvidenceTruth.FALSE for value in values):
            return CompositionUpgradeReadiness.BLOCKED
        return CompositionUpgradeReadiness.READY

    @staticmethod
    def _property_tri_state(case: _PropertyCase) -> None:
        state = aggregate_composition_upgrade_readiness(
            case.selected_packages,
            case.package_requirements,
            case.requirement_truths,
        )
        expected_requirements = CompositionUpgradeReadinessPropertyTests._expected_requirements(
            case
        )
        if state.status is not CompositionUpgradeReadinessPropertyTests._expected_status(
            expected_requirements,
            case.requirement_truths,
        ):
            raise AssertionError(
                f"status mismatch: got {state.status.value}, "
                f"expected "
                f"{CompositionUpgradeReadinessPropertyTests._expected_status(expected_requirements, case.requirement_truths).value}"
            )
        actual_requirements = tuple(
            item.requirement for item in state.requirements
        )
        if actual_requirements != expected_requirements:
            raise AssertionError(
                f"requirement union mismatch: got {actual_requirements!r}, "
                f"expected {expected_requirements!r}"
            )

    @staticmethod
    def _property_dedup(case: _PropertyCase) -> None:
        state = aggregate_composition_upgrade_readiness(
            case.selected_packages,
            case.package_requirements,
            case.requirement_truths,
        )
        identities = tuple(
            item.requirement.identity for item in state.requirements
        )
        if len(identities) != len(set(identities)):
            raise AssertionError(
                f"duplicate requirement identities: {identities!r}"
            )
        expected_ids = {
            requirement.identity
            for package_id in case.selected_package_set
            for requirement in case.package_requirements[package_id]
        }
        if set(identities) != expected_ids:
            raise AssertionError(
                f"deduplicated identities {set(identities)!r} "
                f"!= expected {expected_ids!r}"
            )
        for identity in expected_ids:
            count = sum(
                item.requirement.identity == identity
                for item in state.requirements
            )
            if count != 1:
                raise AssertionError(
                    f"requirement {identity!r} appears {count} times"
                )

    @staticmethod
    def _permuted_case(case: _PropertyCase) -> _PropertyCase:
        selected = tuple(reversed(case.selected_packages))
        package_requirements = {
            package_id: tuple(reversed(requirements))
            for package_id, requirements in reversed(
                tuple(case.package_requirements.items())
            )
        }
        requirement_truths = dict(
            reversed(tuple(case.requirement_truths.items()))
        )
        return _PropertyCase(
            selected_packages=selected,
            package_requirements=package_requirements,
            requirement_truths=requirement_truths,
        )

    @staticmethod
    def _property_order(case: _PropertyCase) -> None:
        first = aggregate_composition_upgrade_readiness(
            case.selected_packages,
            case.package_requirements,
            case.requirement_truths,
        )
        permuted = CompositionUpgradeReadinessPropertyTests._permuted_case(case)
        second = aggregate_composition_upgrade_readiness(
            permuted.selected_packages,
            permuted.package_requirements,
            permuted.requirement_truths,
        )
        if first != second:
            raise AssertionError(
                "permutation changed readiness state: "
                f"first={first!r}, second={second!r}"
            )
        ordering = tuple(
            (
                item.requirement.technology_id,
                item.requirement.identity,
                item.requirement.observation_ref,
            )
            for item in first.requirements
        )
        if ordering != tuple(sorted(ordering)):
            raise AssertionError(
                f"requirements are not canonically ordered: {ordering!r}"
            )

    @staticmethod
    def _shrink_candidates(case: _PropertyCase):
        package_ids = list(case.package_requirements)

        # First minimize package selection. Keep at least one selected package.
        if len(case.selected_packages) > 1:
            for index in range(len(case.selected_packages)):
                selected = (
                    case.selected_packages[:index]
                    + case.selected_packages[index + 1 :]
                )
                if selected:
                    yield _PropertyCase(
                        selected_packages=selected,
                        package_requirements=case.package_requirements,
                        requirement_truths=case.requirement_truths,
                    )

        # Remove duplicate selections before touching semantic requirements.
        unique_selected = tuple(dict.fromkeys(case.selected_packages))
        if unique_selected != case.selected_packages:
            yield _PropertyCase(
                selected_packages=unique_selected,
                package_requirements=case.package_requirements,
                requirement_truths=case.requirement_truths,
            )

        # Remove one requirement at a time from any selected package.
        for package_id in package_ids:
            requirements = case.package_requirements[package_id]
            if not requirements:
                continue
            for index in range(len(requirements)):
                updated_requirements = requirements[:index] + requirements[index + 1 :]
                updated_packages = dict(case.package_requirements)
                updated_packages[package_id] = updated_requirements
                yield _PropertyCase(
                    selected_packages=case.selected_packages,
                    package_requirements=updated_packages,
                    requirement_truths=case.requirement_truths,
                )

        # Remove irrelevant unselected package definitions.
        selected_set = set(case.selected_packages)
        removable_packages = [
            package_id
            for package_id in package_ids
            if package_id not in selected_set
        ]
        for package_id in removable_packages:
            updated_packages = {
                key: value
                for key, value in case.package_requirements.items()
                if key != package_id
            }
            yield _PropertyCase(
                selected_packages=case.selected_packages,
                package_requirements=updated_packages,
                requirement_truths=case.requirement_truths,
            )

        # Remove truth entries. Missing evidence deliberately means UNKNOWN,
        # which can make a failing case smaller and more diagnostically useful.
        for identity in sorted(case.requirement_truths):
            updated_truths = dict(case.requirement_truths)
            del updated_truths[identity]
            yield _PropertyCase(
                selected_packages=case.selected_packages,
                package_requirements=case.package_requirements,
                requirement_truths=updated_truths,
            )

    @classmethod
    def _shrink_case(
        cls,
        case: _PropertyCase,
        predicate,
    ) -> _PropertyCase:
        current = case
        changed = True
        while changed:
            changed = False
            for candidate in cls._shrink_candidates(current):
                try:
                    predicate(candidate)
                except AssertionError:
                    current = candidate
                    changed = True
                    break
        return current

    def _assert_property_with_shrink(
        self,
        *,
        property_name: str,
        seed: int,
        case_index: int,
        case: _PropertyCase,
        predicate,
    ) -> None:
        try:
            predicate(case)
        except AssertionError as original:
            minimal = self._shrink_case(case, predicate)
            raise AssertionError(
                f"{property_name} failed; seed=0x{seed:X}; "
                f"iteration={case_index}; original={case.description()}; "
                f"minimal={minimal.description()}; "
                f"original_error={original}"
            ) from original

    def test_property_tri_state_matches_three_valued_conjunction(self):
        seed = 0xA02E7
        rng = random.Random(seed)
        for case_index in range(self.ITERATIONS):
            case = self._generate_case(rng)
            with self.subTest(seed=f"0x{seed:X}", case_index=case_index):
                self._assert_property_with_shrink(
                    property_name="tri-state",
                    seed=seed,
                    case_index=case_index,
                    case=case,
                    predicate=self._property_tri_state,
                )

    def test_property_requirement_union_is_semantically_deduplicated(self):
        seed = 0xD3D0F
        rng = random.Random(seed)
        for case_index in range(self.ITERATIONS):
            case = self._generate_case(rng)
            with self.subTest(seed=f"0x{seed:X}", case_index=case_index):
                self._assert_property_with_shrink(
                    property_name="deduplication",
                    seed=seed,
                    case_index=case_index,
                    case=case,
                    predicate=self._property_dedup,
                )

    def test_property_requirement_order_is_independent_of_input_order(self):
        seed = 0x0FD3
        rng = random.Random(seed)
        for case_index in range(self.ITERATIONS):
            case = self._generate_case(rng)
            with self.subTest(seed=f"0x{seed:X}", case_index=case_index):
                self._assert_property_with_shrink(
                    property_name="deterministic-ordering",
                    seed=seed,
                    case_index=case_index,
                    case=case,
                    predicate=self._property_order,
                )

    def test_property_duplicate_selected_package_is_semantically_irrelevant(self):
        seed = 0xD0B
        rng = random.Random(seed)
        for case_index in range(self.ITERATIONS):
            case = self._generate_case(rng)
            unique_selected = tuple(sorted(set(case.selected_packages)))
            duplicated_selected = list(case.selected_packages)
            duplicated_selected.extend(
                case.selected_packages[: rng.randint(0, len(case.selected_packages))]
            )
            rng.shuffle(duplicated_selected)

            first = aggregate_composition_upgrade_readiness(
                unique_selected,
                case.package_requirements,
                case.requirement_truths,
            )
            second = aggregate_composition_upgrade_readiness(
                tuple(duplicated_selected),
                case.package_requirements,
                case.requirement_truths,
            )

            with self.subTest(seed=f"0x{seed:X}", case_index=case_index):
                self.assertEqual(first, second)

    def test_property_conflicting_duplicate_definitions_always_fail_closed_at_structure_boundary(self):
        seed = 0xC0FF
        rng = random.Random(seed)
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
                raise AssertionError(
                    "generator failed to create a conflicting observation"
                )
            package_requirements = {
                "primary": (first,),
                "supporting": (second,),
            }

            with self.subTest(seed=f"0x{seed:X}", case_index=case_index):
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
        seed = 0xA11
        rng = random.Random(seed)
        for case_index in range(self.ITERATIONS):
            case = self._generate_case(rng)
            expected_requirements = self._expected_requirements(case)
            if not expected_requirements:
                continue
            missing_identity = rng.choice(
                [item.identity for item in expected_requirements]
            )
            truths = dict(case.requirement_truths)
            truths.pop(missing_identity, None)
            missing_case = _PropertyCase(
                selected_packages=case.selected_packages,
                package_requirements=case.package_requirements,
                requirement_truths=truths,
            )

            state = aggregate_composition_upgrade_readiness(
                missing_case.selected_packages,
                missing_case.package_requirements,
                missing_case.requirement_truths,
            )

            with self.subTest(
                seed=f"0x{seed:X}",
                case_index=case_index,
                identity=missing_identity,
            ):
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
        for case_index in range(self.ITERATIONS):
            with self.subTest(case_index=case_index):
                state = aggregate_composition_upgrade_readiness((), {}, {})
                self.assertEqual(
                    state.status,
                    CompositionUpgradeReadiness.READY,
                )
                self.assertEqual(state.selected_packages, ())
                self.assertEqual(state.requirements, ())


if __name__ == "__main__":
    unittest.main()
