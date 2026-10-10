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

    def test_first_lumber_camp_has_native_direct_build_fallback(self):
        rules = self._active_rules(1)
        fallback = next(
            rule for rule in rules
            if "(build lumber-camp)" in rule
            and "(up-build place-point 0 c: lumber-camp)" not in rule
        )
        self.assertIn("(unit-type-count-total villager >= 15)", fallback)
        self.assertIn("(resource-found wood)", fallback)
        self.assertIn("(can-build lumber-camp)", fallback)
        self.assertIn("(building-type-count-total lumber-camp < 1)", fallback)
        self.assertIn("(goal action-claim-build-pass-singleton 0)", fallback)

    def test_point_search_constants_are_bound_to_nonoverlapping_goal_slots(self):
        names = (
            "byzantine-dark-wood-camp-point-1",
            "byzantine-dark-wood-camp-search-state-1",
            "byzantine-dark-wood-camp-search-remote-count-1",
            "byzantine-dark-wood-camp-point-2",
            "byzantine-dark-wood-camp-search-state-2",
            "byzantine-dark-wood-camp-search-remote-count-2",
        )
        values = {}
        for name in names:
            matches = re.findall(
                rf"\(defconst {re.escape(name)} (\d+)\)",
                self.source,
            )
            self.assertEqual(len(matches), 1, name)
            values[name] = int(matches[0])

        for state_name, remote_name in (
            ("byzantine-dark-wood-camp-search-state-1", "byzantine-dark-wood-camp-search-remote-count-1"),
            ("byzantine-dark-wood-camp-search-state-2", "byzantine-dark-wood-camp-search-remote-count-2"),
        ):
            self.assertEqual(
                values[remote_name],
                values[state_name] + 2,
                "remote-list count must alias the third up-get-search-state output",
            )

        intervals = (
            (
                values["byzantine-dark-wood-camp-point-1"],
                values["byzantine-dark-wood-camp-point-1"] + 1,
            ),
            (
                values["byzantine-dark-wood-camp-search-state-1"],
                values["byzantine-dark-wood-camp-search-state-1"] + 3,
            ),
            (
                values["byzantine-dark-wood-camp-point-2"],
                values["byzantine-dark-wood-camp-point-2"] + 1,
            ),
            (
                values["byzantine-dark-wood-camp-search-state-2"],
                values["byzantine-dark-wood-camp-search-state-2"] + 3,
            ),
        )
        for index, (start, end) in enumerate(intervals):
            if index in (0, 2):
                self.assertTrue(41 <= start <= 15998)
            else:
                self.assertTrue(41 <= start <= 15996)
            self.assertTrue(start <= end <= 16000)
            for other_start, other_end in intervals[index + 1 :]:
                self.assertTrue(
                    end < other_start or other_end < start,
                    f"wood-camp storage overlaps: {(start, end)} with {(other_start, other_end)}",
                )

    def test_first_two_lumber_camps_use_witnessed_resource_point_placement(self):
        for floor, point, state, remote, search_limit, target_index, old_distance in (
            (
                1,
                "byzantine-dark-wood-camp-point-1",
                "byzantine-dark-wood-camp-search-state-1",
                "byzantine-dark-wood-camp-search-remote-count-1",
                1,
                0,
                "5",
            ),
            (
                2,
                "byzantine-dark-wood-camp-point-2",
                "byzantine-dark-wood-camp-search-state-2",
                "byzantine-dark-wood-camp-search-remote-count-2",
                40,
                1,
                "12",
            ),
        ):
            rules = self._active_rules(floor)
            search_rule = next(
                rule for rule in rules
                if f"(up-find-resource c: wood c: {search_limit})" in rule
            )
            execution_rule = next(
                rule for rule in rules
                if "(up-build place-point 0 c: lumber-camp)" in rule
            )

            self.assertIn(f"(up-find-resource c: wood c: {search_limit})", search_rule)
            self.assertIn(f"(up-get-search-state {state})", search_rule)
            self.assertIn("(up-filter-status c: status-resource c: list-active)", search_rule)

            self.assertIn(f"(up-compare-goal {remote} > {target_index})", execution_rule)
            self.assertIn(f"(up-set-target-object search-remote c: {target_index})", execution_rule)
            self.assertIn(f"(up-get-point position-object {point})", execution_rule)
            self.assertIn(f"(up-set-target-point {point})", execution_rule)
            self.assertIn("(up-build place-point 0 c: lumber-camp)", execution_rule)
            self.assertNotIn(
                f"(dropsite-min-distance wood > {old_distance})",
                execution_rule,
            )


if __name__ == "__main__":
    unittest.main()
