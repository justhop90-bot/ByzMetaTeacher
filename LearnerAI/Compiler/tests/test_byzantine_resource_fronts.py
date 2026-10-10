from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = ROOT / "Byzantine.per"


def _const_value(source: str, name: str) -> int:
    matches = re.findall(rf"\(defconst {re.escape(name)} (\d+)\)", source)
    if len(matches) != 1:
        raise AssertionError(f"{name}: expected one defconst, got {matches!r}")
    return int(matches[0])


def _section(source: str, start_marker: str, end_marker: str) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


class ByzantineResourceFrontLivenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ARTIFACT.read_text(encoding="utf-8")

    def test_remote_list_count_uses_third_search_state_goal_without_duplicate_storage(self):
        searches = (
            ("byzantine-dark-gold-camp-search-state-1", "byzantine-dark-gold-camp-search-remote-count-1"),
            ("byzantine-dark-gold-camp-search-state-2", "byzantine-dark-gold-camp-search-remote-count-2"),
            ("byzantine-dark-gold-camp-search-state-3", "byzantine-dark-gold-camp-search-remote-count-3"),
            ("byzantine-dark-gold-camp-search-state-4", "byzantine-dark-gold-camp-search-remote-count-4"),
            ("byzantine-dark-gold-camp-search-state-5", "byzantine-dark-gold-camp-search-remote-count-5"),
            ("byzantine-dark-wood-camp-search-state-1", "byzantine-dark-wood-camp-search-remote-count-1"),
            ("byzantine-dark-wood-camp-search-state-2", "byzantine-dark-wood-camp-search-remote-count-2"),
            ("byzantine-dark-stone-camp-search-state-2", "byzantine-dark-stone-camp-search-remote-count-2"),
            ("byzantine-dark-stone-camp-search-state-3", "byzantine-dark-stone-camp-search-remote-count-3"),
            ("byzantine-dark-stone-camp-search-state-4", "byzantine-dark-stone-camp-search-remote-count-4"),
            ("byzantine-dark-stone-camp-search-state-5", "byzantine-dark-stone-camp-search-remote-count-5"),
            ("byzantine-dark-mill-search-state", "byzantine-dark-mill-search-remote-count"),
        )
        spans = []
        for state_name, obsolete_alias in searches:
            start = _const_value(self.source, state_name)
            remote_goal = start + 2
            self.assertGreaterEqual(start, 41, state_name)
            self.assertLessEqual(start + 3, 16000, state_name)
            self.assertNotRegex(
                self.source,
                rf"\(defconst {re.escape(obsolete_alias)}\s",
                f"{obsolete_alias} must not allocate a second Goal inside a GoalSpan",
            )
            self.assertIn(
                f"(up-compare-goal {remote_goal} > ",
                self.source,
                f"{state_name}: compare remote-list total from output slot start+2",
            )
            spans.append((start, start + 3, state_name))

        for index, (start, end, name) in enumerate(spans):
            for other_start, other_end, other_name in spans[index + 1:]:
                self.assertTrue(
                    end < other_start or other_end < start,
                    f"search-state spans overlap: {name} {(start, end)} and {other_name} {(other_start, other_end)}",
                )

    def test_gold_camp_floors_advance_past_the_candidate_used_by_the_prior_floor(self):
        for floor in range(1, 6):
            end_marker = (
                f"; economy-gold-camp-floor-{floor + 1}"
                if floor < 5
                else "; economy-stone-camp-floor-1"
            )
            section = _section(
                self.source,
                f"; economy-gold-camp-floor-{floor}",
                end_marker,
            )
            index = floor - 1
            state_name = f"byzantine-dark-gold-camp-search-state-{floor}"
            remote_goal = _const_value(self.source, state_name) + 2
            expected_search_size = 1 if floor == 1 else 40
            self.assertIn(f"(up-find-resource c: gold c: {expected_search_size})", section)
            self.assertIn(f"(up-compare-goal {remote_goal} > {index})", section)
            self.assertIn(f"(up-set-target-object search-remote c: {index})", section)

    def test_wood_second_camp_searches_enough_candidates_and_advances_index(self):
        section = _section(
            self.source,
            "; Action issuance: economy-lumber-camp-floor-2 | ACTIVE -> ISSUED",
            "; RESOURCE-SPECIFIC BYZANTINE CAMP LIFECYCLES",
        )
        state_name = "byzantine-dark-wood-camp-search-state-2"
        remote_goal = _const_value(self.source, state_name) + 2
        self.assertIn("(up-find-resource c: wood c: 40)", section)
        self.assertIn(f"(up-compare-goal {remote_goal} > 1)", section)
        self.assertIn("(up-set-target-object search-remote c: 1)", section)
        self.assertIn("(up-build place-point 0 c: lumber-camp)", section)

    def test_stone_camp_floors_start_at_remote_index_zero_after_direct_first_camp(self):
        for floor in range(2, 6):
            end_marker = (
                f"; economy-stone-camp-floor-{floor + 1}"
                if floor < 5
                else "; Narrow Dark Age second-mill rule"
            )
            section = _section(
                self.source,
                f"; economy-stone-camp-floor-{floor}",
                end_marker,
            )
            index = floor - 2
            state_name = f"byzantine-dark-stone-camp-search-state-{floor}"
            remote_goal = _const_value(self.source, state_name) + 2
            self.assertIn(f"(up-get-search-state {state_name})", section)
            self.assertIn("(up-find-resource c: stone c: 40)", section)
            self.assertIn(f"(up-compare-goal {remote_goal} > {index})", section)
            self.assertIn(f"(up-set-target-object search-remote c: {index})", section)
            self.assertIn("(up-build place-point 0 c: mining-camp)", section)


if __name__ == "__main__":
    unittest.main()
