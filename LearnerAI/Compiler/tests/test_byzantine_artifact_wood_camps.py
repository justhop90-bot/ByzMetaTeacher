from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = ROOT / "Byzantine.per"


def _defrules(source: str) -> list[str]:
    rules = []
    cursor = 0
    marker = "(defrule"
    while True:
        start = source.find(marker, cursor)
        if start < 0:
            break
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(source)):
            char = source[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
                continue
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    rules.append(source[start:index + 1])
                    cursor = index + 1
                    break
        else:
            raise AssertionError("unterminated defrule in Byzantine.per")
    return rules


class ByzantineOpeningWoodCampArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ARTIFACT.read_text(encoding="utf-8")
        cls.rules = _defrules(cls.source)

    def _active_rules(self, floor: int) -> list[str]:
        marker = f"(goal demand-economy-lumber-camp-floor-{floor} 1)"
        return [rule for rule in self.rules if marker in rule]

    def test_point_search_constants_are_unique_and_bound_to_unused_goal_slots(self):
        expected = {
            "byzantine-dark-wood-camp-point-1": 15000,
            "byzantine-dark-wood-camp-search-state-1": 15001,
            "byzantine-dark-wood-camp-search-remote-count-1": 15002,
            "byzantine-dark-wood-camp-point-2": 15003,
            "byzantine-dark-wood-camp-search-state-2": 15004,
            "byzantine-dark-wood-camp-search-remote-count-2": 15005,
        }
        for name, value in expected.items():
            self.assertEqual(
                len(re.findall(rf"\(defconst {re.escape(name)} \d+\)", self.source)),
                1,
                name,
            )
            self.assertEqual(
                len(re.findall(rf"\(defconst [^\s()]+ {value}\)", self.source)),
                1,
                f"goal id {value} must be unique",
            )

    def test_first_two_lumber_camps_use_witnessed_resource_point_placement(self):
        for floor, point, state, remote, old_distance in (
            (
                1,
                "byzantine-dark-wood-camp-point-1",
                "byzantine-dark-wood-camp-search-state-1",
                "byzantine-dark-wood-camp-search-remote-count-1",
                "5",
            ),
            (
                2,
                "byzantine-dark-wood-camp-point-2",
                "byzantine-dark-wood-camp-search-state-2",
                "byzantine-dark-wood-camp-search-remote-count-2",
                "12",
            ),
        ):
            rules = self._active_rules(floor)
            self.assertEqual(len(rules), 2, f"floor {floor} must split search and execution")
            search_rule, execution_rule = rules

            self.assertIn("(up-find-resource c: wood c: 1)", search_rule)
            self.assertIn(f"(up-get-search-state {state})", search_rule)
            self.assertIn("(up-filter-status c: status-resource c: list-active)", search_rule)

            self.assertIn(f"(up-compare-goal {remote} > 0)", execution_rule)
            self.assertIn("(up-set-target-object search-remote c: 0)", execution_rule)
            self.assertIn(f"(up-get-point position-object {point})", execution_rule)
            self.assertIn(f"(up-set-target-point {point})", execution_rule)
            self.assertIn("(up-build place-point 0 c: lumber-camp)", execution_rule)
            self.assertNotIn("(build lumber-camp)", execution_rule)
            self.assertNotIn(
                f"(dropsite-min-distance wood > {old_distance})",
                execution_rule,
            )


if __name__ == "__main__":
    unittest.main()
