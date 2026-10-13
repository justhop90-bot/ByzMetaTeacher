import json
import tempfile
import unittest
from pathlib import Path

from tools.byzds_parser import BYZDSParser, parse_events, BYZDSInvalid


ROOT = Path(__file__).parents[1]
SPEC = ROOT / "docs/runtime/byzds-cross-event-constraints-v1.json"


def line(event, *fields):
    return "\t".join(("BYZDS", "1", "case", event, *map(str, fields)))


def case(events, case_id="c1", controller="lumber-1", scenario="R6_COMPLETION"):
    start = line("CASE_START", case_id, controller, scenario, "IDLE", "0")
    return "\n".join([start, *events])


class BYZDSParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = BYZDSParser.from_file(SPEC)

    def test_valid_completion_trace(self):
        text = case([
            line("DEMAND_ON", "RESOURCE_NEEDS"),
            line("ADMITTED", 1),
            line("TARGET_SELECTED", "gold-A", 1),
            line("ACTION", "BUILD_MINING_CAMP", "gold-A", 1),
            line("FOUNDATION", "gold-A", 1),
            line("COMPLETION", 1, 2),
            line("RELEASE", "COMPLETED"),
            line("CASE_END", "PASS", 9),
        ])
        result = self.parser.parse(text)
        self.assertEqual(result["matrix"]["result"], "PASS")
        self.assertEqual(result["cases"][0]["result"], "PASS")

    def test_retry_requires_invalidation(self):
        text = case([
            line("DEMAND_ON", "RESOURCE_NEEDS"),
            line("ADMITTED", 1),
            line("TARGET_SELECTED", "gold-A", 1),
            line("ACTION", "BUILD_MINING_CAMP", "gold-A", 1),
            line("FAILURE", 1, "PLACEMENT_INVALID"),
            line("RETRY", 1, 2),
            line("CASE_END", "FAIL", 7),
        ], scenario="R1_FIRST_FAILURE")
        result = self.parser.parse(text)
        ids = {r["constraint_id"]: r for r in result["cases"][0]["constraint_results"]}
        self.assertFalse(ids["X005"]["satisfied"])

    def test_active_target_mismatch(self):
        text = case([
            line("ADMITTED", 1),
            line("TARGET_SELECTED", "gold-A", 1),
            line("ACTION", "BUILD_MINING_CAMP", "gold-B", 1),
            line("CASE_END", "FAIL", 5),
        ])
        result = self.parser.parse(text)
        ids = {r["constraint_id"]: r for r in result["cases"][0]["constraint_results"]}
        self.assertEqual(ids["X001"]["code"], "ACTIVE_TARGET_MISMATCH")

    def test_completion_without_foundation_fails(self):
        text = case([
            line("ADMITTED", 1),
            line("TARGET_SELECTED", "gold-A", 1),
            line("ACTION", "BUILD_MINING_CAMP", "gold-A", 1),
            line("COMPLETION", 1, 2),
            line("CASE_END", "FAIL", 5),
        ])
        result = self.parser.parse(text)
        self.assertEqual(
            next(r for r in result["cases"][0]["constraint_results"] if r["constraint_id"] == "X015")["code"],
            "COMPLETION_WITHOUT_FOUNDATION",
        )

    def test_stale_target_reuse_fails(self):
        text = case([
            line("ADMITTED", 1),
            line("TARGET_SELECTED", "gold-A", 1),
            line("ACTION", "BUILD_MINING_CAMP", "gold-A", 1),
            line("FAILURE", 1, "PLACEMENT_INVALID"),
            line("TARGET_INVALIDATED", "gold-A", 1),
            line("RETRY", 1, 2),
            line("ADMITTED", 2),
            line("ACTION", "BUILD_MINING_CAMP", "gold-A", 2),
            line("CASE_END", "FAIL", 9),
        ], scenario="R2_SECOND_FAILURE")
        result = self.parser.parse(text)
        codes = [r["code"] for r in result["cases"][0]["constraint_results"] if not r["satisfied"]]
        self.assertIn("MISSING_FRESH_TARGET_SELECTION", codes)

    def test_malformed_input_is_infra_error(self):
        result = self.parser.parse("BYZDS\t1\tcase\tACTION\tBUILD_MILL")
        self.assertEqual(result["matrix"]["result"], "INFRA_ERROR")
        self.assertEqual(result["errors"][0]["code"], "PARSE_ERROR")

    def test_multi_case_matrix_is_deterministic(self):
        a = case([line("CASE_END", "PASS", 2)], "a", scenario="R6_COMPLETION")
        b = case([line("CASE_END", "PASS", 2)], "b", scenario="R3_THIRD_FAILURE")
        r1 = self.parser.parse(a + "\n" + b)
        r2 = self.parser.parse(a + "\n" + b)
        self.assertEqual(json.dumps(r1, sort_keys=True), json.dumps(r2, sort_keys=True))
        self.assertEqual(r1["matrix"]["case_count"], 2)

    def test_percent_decoding_is_strict(self):
        with self.assertRaises(BYZDSInvalid):
            parse_events(line("ERROR", "LOGGING_FAILURE", "bad%ZZ"))


if __name__ == "__main__":
    unittest.main()
