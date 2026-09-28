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


if __name__ == "__main__":
    unittest.main()
