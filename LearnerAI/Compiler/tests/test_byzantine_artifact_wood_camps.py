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




def _defconsts(source: str) -> dict[str, int]:
    return {
        match.group(1): int(match.group(2))
        for match in re.finditer(
            r"\(defconst\s+([^\s()]+)\s+(-?\d+)\)",
            source,
        )
    }


def _storage_intervals(source: str) -> list[tuple[int, int, str]]:
    definitions = _defconsts(source)
    intervals: list[tuple[int, int, str]] = []

    def resolve(token: str) -> int | None:
        if re.fullmatch(r"-?\d+", token):
            return int(token)
        return definitions.get(token)

    for match in re.finditer(
        r"\(up-get-search-state\s+([^\s()]+)\)",
        source,
    ):
        value = resolve(match.group(1))
        if value is not None:
            intervals.append((value, value + 3, "SEARCH_STATE"))

    for match in re.finditer(
        r"\(up-get-point\s+position-object\s+([^\s()]+)\)",
        source,
    ):
        value = resolve(match.group(1))
        if value is not None:
            intervals.append((value, value + 1, "POINT_PAIR"))

    for match in re.finditer(
        r"\((?:goal|set-goal|up-compare-goal|up-modify-goal)\s+([^\s()]+)",
        source,
    ):
        value = resolve(match.group(1))
        if value is not None:
            intervals.append((value, value, "GOAL_SLOT"))

    return list(dict.fromkeys(intervals))


def _duc_output_intervals(source: str) -> list[tuple[int, int, str]]:
    definitions = _defconsts(source)
    intervals: list[tuple[int, int, str]] = []

    def resolve(token: str) -> int | None:
        if re.fullmatch(r"-?\d+", token):
            return int(token)
        return definitions.get(token)

    for match in re.finditer(
        r"\(up-get-search-state\s+([^\s()]+)\)",
        source,
    ):
        value = resolve(match.group(1))
        if value is not None:
            intervals.append((value, value + 3, "SEARCH_STATE"))

    for match in re.finditer(
        r"\(up-get-point\s+position-object\s+([^\s()]+)\)",
        source,
    ):
        value = resolve(match.group(1))
        if value is not None:
            intervals.append((value, value + 1, "POINT_PAIR"))

    return list(dict.fromkeys(intervals))


class ByzantineOpeningWoodCampArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ARTIFACT.read_text(encoding="utf-8")
        cls.rules = _defrules(cls.source)

    def _active_rules(self, floor: int) -> list[str]:
        marker = f"(goal demand-economy-lumber-camp-floor-{floor} 1)"
        return [rule for rule in self.rules if marker in rule]

    def test_compiler_owned_camp_duc_storage_does_not_overlap_hybrid_runtime_state(self):
        header = "; COMPILER-OWNED AIREF RESOURCE-CAMP LIFECYCLES"
        end_marker = "; Narrow Dark Age second-mill rule:"
        start = self.source.index(header)
        end = self.source.index(end_marker, start)
        camp = self.source[start:end]
        outside = self.source[:start] + self.source[end:]

        camp_intervals = _duc_output_intervals(camp)
        runtime_intervals = _storage_intervals(outside)
        collisions = [
            (camp_interval, runtime_interval)
            for camp_interval in camp_intervals
            for runtime_interval in runtime_intervals
            if camp_interval[0] <= runtime_interval[1]
            and runtime_interval[0] <= camp_interval[1]
        ]
        self.assertFalse(
            collisions,
            "compiler-owned camp DUC storage overlaps hybrid runtime Goal storage: "
            f"{collisions[:5]}",
        )

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
        self.assertIn("(building-type-count-total 562 < 1)", fallback)
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

    def test_first_two_lumber_camps_use_witnessed_resource_point_placement(self):
        for floor in (1, 2):
            rules = self._active_rules(floor)
            search_rule = next(
                rule for rule in rules
                if "(up-find-resource c: wood c: 1)" in rule
            )
            placement_rule = next(
                rule for rule in rules
                if "(up-get-point position-object " in rule
                and "(up-set-target-point " in rule
            )

            search_match = re.search(
                r"\(up-get-search-state (\d+)\)",
                search_rule,
            )
            self.assertIsNotNone(search_match)
            search_state = int(search_match.group(1))

            remote_match = re.search(
                r"\(up-compare-goal (\d+) > 0\)",
                placement_rule,
            )
            point_match = re.search(
                r"\(up-get-point position-object (\d+)\)",
                placement_rule,
            )
            target_point_match = re.search(
                r"\(up-set-target-point (\d+)\)",
                placement_rule,
            )
            self.assertIsNotNone(remote_match)
            self.assertIsNotNone(point_match)
            self.assertIsNotNone(target_point_match)

            remote_goal = int(remote_match.group(1))
            point = int(point_match.group(1))
            target_point = int(target_point_match.group(1))

            self.assertEqual(remote_goal, search_state + 2)
            self.assertEqual(point, target_point)
            self.assertGreater(search_state, 1000)
            self.assertGreater(point, 1000)

            self.assertIn("(up-filter-status c: status-resource c: list-active)", search_rule)
            self.assertIn("(up-set-target-object search-remote c: 0)", placement_rule)

            execution_marker = (
                f"; Native placement execution: economy-lumber-camp-floor-{floor}"
            )
            execution_start = self.source.index(execution_marker)
            execution_end = self.source.find("\n; ", execution_start + 10)
            build_section = (
                self.source[execution_start:]
                if execution_end < 0
                else self.source[execution_start:execution_end]
            )
            self.assertIn("(up-build place-point 0 c:", build_section)
            self.assertNotEqual(search_state, 468)
            self.assertNotEqual(point, 416 if floor == 1 else 418)




if __name__ == "__main__":
    unittest.main()
