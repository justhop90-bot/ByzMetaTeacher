from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any

from Compiler.oracles.duc_native import validate_oracle_consistency


FIXTURE_DIR = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "reference"
    / "oracles"
    / "fixtures"
)
CANDIDATE_DIR = FIXTURE_DIR.parent / "candidates"

EXPECTED_FIXTURES = {
    "duc-remove-after-target.pass.json": "PASS",
    "duc-remove-before-target.fail.json": "FAIL",
}


def _read_fixture(name: str) -> dict[str, Any]:
    with (FIXTURE_DIR / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def _read_pointer(document: dict[str, Any], pointer: str) -> Any:
    current: Any = document
    for token in pointer.removeprefix("/").split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            current = current[token]
        elif isinstance(current, list):
            current = current[int(token)]
        else:
            raise AssertionError(f"Cannot descend through {type(current).__name__}")
    return current


class DucNativeOracleFixtureTests(unittest.TestCase):
    def test_representative_fixture_set_is_exactly_two_cases(self):
        self.assertEqual(
            set(EXPECTED_FIXTURES),
            {
                path.name
                for path in FIXTURE_DIR.glob("*.json")
                if path.name in EXPECTED_FIXTURES
            },
        )

    def test_each_fixture_uses_the_restructured_format(self):
        for filename in EXPECTED_FIXTURES:
            document = _read_fixture(filename)
            fixture = document["fixture"]
            observation = fixture["observation"]

            self.assertIn("kind", fixture)
            self.assertEqual(fixture["kind"], "SEMANTIC_EXAMPLE")
            self.assertEqual(fixture["engine_scope"]["build"], "fixture-test-double")
            self.assertEqual(observation["engine"]["build"], "fixture-test-double")

            validate_oracle_consistency(document)

    def test_passing_fixture_has_only_passing_semantic_assertions(self):
        document = _read_fixture("duc-remove-after-target.pass.json")
        fixture = document["fixture"]
        observation = fixture["observation"]

        self.assertEqual(observation["result"], "PASS")
        self.assertTrue(observation["assertions"])
        self.assertTrue(
            all(assertion["result"] == "PASS" for assertion in observation["assertions"])
        )

        observed_by_id = {
            assertion["id"]: assertion for assertion in observation["assertions"]
        }
        for assertion in fixture["assertions"]:
            observed = observed_by_id[assertion["id"]]
            actual = _read_pointer(document, assertion["observation_path"])
            self.assertEqual(assertion["expected"], actual)
            self.assertEqual(observed["expected"], actual)
            self.assertEqual(observed["actual"], actual)

    def test_failing_fixture_is_structurally_valid_but_semantically_fails(self):
        document = _read_fixture("duc-remove-before-target.fail.json")
        fixture = document["fixture"]
        observation = fixture["observation"]

        self.assertEqual(observation["result"], "FAIL")
        self.assertIn(
            "FAIL",
            {assertion["result"] for assertion in observation["assertions"]},
        )

        observed_by_id = {
            assertion["id"]: assertion for assertion in observation["assertions"]
        }
        failing = [
            assertion
            for assertion in fixture["assertions"]
            if observed_by_id[assertion["id"]]["result"] == "FAIL"
        ]
        self.assertEqual([item["id"] for item in failing], ["old-index-preserved"])

        for assertion in failing:
            actual = _read_pointer(document, assertion["observation_path"])
            observed = observed_by_id[assertion["id"]]
            self.assertEqual(observed["actual"], actual)
            self.assertNotEqual(assertion["expected"], actual)

    def test_failed_target_action_candidate_is_explicitly_unpromoted(self):
        with (CANDIDATE_DIR / "duc-failed-target-action.native.json").open(
            encoding="utf-8"
        ) as handle:
            document = json.load(handle)

        fixture = document["fixture"]
        observation = fixture["observation"]
        probe_sources = [item["source"] for item in fixture["probe"]]

        self.assertEqual(fixture["kind"], "NATIVE_OBSERVATION")
        self.assertEqual(observation["result"], "UNVERIFIED")
        self.assertEqual(
            fixture["engine_scope"]["build"],
            "RECORD-ACTUAL-ENGINE-BUILD",
        )
        self.assertEqual(
            observation["engine"]["build"],
            "RECORD-ACTUAL-ENGINE-BUILD",
        )
        self.assertEqual(
            [assertion["result"] for assertion in observation["assertions"]],
            ["UNVERIFIED", "UNVERIFIED", "UNVERIFIED"],
        )
        self.assertIn(
            "(up-set-target-object search-local c: 240)",
            probe_sources,
        )
        self.assertIn(
            "search-local capacity is 240; index 240 is invalid",
            fixture["scenario"]["object_set"][0]["metadata"]["capacity_boundary"],
        )
        self.assertIn(
            "(up-get-object-target-data object-data-id 101)",
            probe_sources,
        )

    def test_clean_search_target_identity_candidate_is_explicitly_unpromoted(self):
        with (CANDIDATE_DIR / "duc-clean-search-target-identity.native.json").open(
            encoding="utf-8"
        ) as handle:
            document = json.load(handle)

        fixture = document["fixture"]
        observation = fixture["observation"]
        probe_sources = [item["source"] for item in fixture["probe"]]

        self.assertEqual(fixture["kind"], "NATIVE_OBSERVATION")
        self.assertEqual(observation["result"], "UNVERIFIED")
        self.assertEqual(
            fixture["engine_scope"]["build"],
            "RECORD-ACTUAL-ENGINE-BUILD",
        )
        self.assertEqual(
            observation["engine"]["build"],
            "RECORD-ACTUAL-ENGINE-BUILD",
        )
        self.assertEqual(
            [assertion["result"] for assertion in observation["assertions"]],
            ["UNVERIFIED", "UNVERIFIED", "UNVERIFIED", "UNVERIFIED"],
        )
        self.assertEqual(
            observation["target"]["before"]["index"],
            0,
        )
        self.assertEqual(
            observation["target"]["after"]["index"],
            2,
        )
        self.assertIn(
            "(up-clean-search search-local object-data-id search-order-desc)",
            probe_sources,
        )
        self.assertIn(
            "(up-get-object-target-data object-data-id 101)",
            probe_sources,
        )


if __name__ == "__main__":
    unittest.main()
