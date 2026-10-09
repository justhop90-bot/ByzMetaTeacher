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

    def test_point_search_constants_are_unique_and_bound_to_unused_goal_slots(self):
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

        self.assertEqual(len(values), len(set(values.values())))

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
                values["byzantine-dark-wood-camp-search-remote-count-1"],
                values["byzantine-dark-wood-camp-search-remote-count-1"],
            ),
            (
                values["byzantine-dark-wood-camp-point-2"],
                values["byzantine-dark-wood-camp-point-2"] + 1,
            ),
            (
                values["byzantine-dark-wood-camp-search-state-2"],
                values["byzantine-dark-wood-camp-search-state-2"] + 3,
            ),
            (
                values["byzantine-dark-wood-camp-search-remote-count-2"],
                values["byzantine-dark-wood-camp-search-remote-count-2"],
            ),
        )

        for index, (start, end) in enumerate(intervals):
            if index in (0, 3):
                self.assertTrue(41 <= start <= 15998)
            elif index in (1, 4):
                self.assertTrue(41 <= start <= 15996)
            else:
                self.assertTrue(1 <= start <= 16000)
            self.assertTrue(start <= end <= 16000)

        for index, (start, end) in enumerate(intervals):
            for other_start, other_end in intervals[index + 1 :]:
                self.assertTrue(
                    end < other_start or other_end < start,
                    f"wood-camp storage overlaps: {(start, end)} with "
                    f"{(other_start, other_end)}",
                )

    def test_first_two_lumber_camps_have_native_fallback_when_point_witness_is_absent(self):
        floor1 = self._active_rules(1)
        first_camp = next(
            rule for rule in floor1
            if "(build lumber-camp)" in rule
            and "(up-build place-point 0 c: lumber-camp)" not in rule
        )
        self.assertIn("(unit-type-count-total villager >= 15)", first_camp)
        self.assertIn("(resource-found wood)", first_camp)
        self.assertIn("(can-build lumber-camp)", first_camp)
        self.assertIn("(building-type-count-total lumber-camp < 1)", first_camp)
        self.assertIn("(goal action-claim-build-pass-singleton 0)", first_camp)
        # This artifact deliberately removed the dead first-camp DUC path;
        # the live rule is the native direct build guarded by the resource fact.

        floor2 = self._active_rules(2)
        search_rule = next(
            rule for rule in floor2
            if "(up-find-resource c: wood c: 1)" in rule
        )
        point_rule = next(
            rule for rule in floor2
            if "(up-build place-point 0 c: lumber-camp)" in rule
        )
        direct_fallback = next(
            rule for rule in floor2
            if "(build lumber-camp)" in rule
            and "(up-build place-point 0 c: lumber-camp)" not in rule
        )

        self.assertIn(
            "(up-get-search-state byzantine-dark-wood-camp-search-state-2)",
            search_rule,
        )
        self.assertIn(
            "(up-compare-goal byzantine-dark-wood-camp-search-remote-count-2 > 0)",
            point_rule,
        )
        self.assertIn("(up-set-target-object search-remote c: 0)", point_rule)
        self.assertIn("(up-get-point position-object byzantine-dark-wood-camp-point-2)", point_rule)
        self.assertIn("(up-set-target-point byzantine-dark-wood-camp-point-2)", point_rule)
        self.assertNotIn("(dropsite-min-distance wood", point_rule)
        self.assertIn("(dropsite-min-distance wood > 12)", direct_fallback)
        self.assertIn("(not (building-type-count lumber-camp >= 2))", direct_fallback)
        self.assertIn("(resource-found wood)", direct_fallback)
        self.assertIn("(can-build lumber-camp)", direct_fallback)
        self.assertIn("(goal action-claim-build-pass-singleton 0)", direct_fallback)


if __name__ == "__main__":
    unittest.main()
