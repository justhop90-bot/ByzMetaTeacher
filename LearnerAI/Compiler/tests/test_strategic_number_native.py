import unittest
from pathlib import Path


FIXTURE = Path(__file__).parent / "fixtures" / "strategic_number.per"


class StrategicNumberNativeFixtureTests(unittest.TestCase):
    def test_fixture_exists_and_covers_all_operand_domains(self):
        text = FIXTURE.read_text(encoding="utf-8")

        for domain in ("c:","g:","s:"):
            self.assertIn(domain + "+", text)

        for operator in (
            ":=", ":+", ":-", ":*", ":/", ":z/", ":mod",
            ":min", ":max", ":neg", ":%*", ":%/",
        ):
            self.assertIn(operator, text)

    def test_fixture_rules_stay_within_32_element_limit(self):
        text = FIXTURE.read_text(encoding="utf-8")
        cursor = 0
        while True:
            start = text.find("(defrule", cursor)
            if start < 0:
                break
            depth = 0
            end = None
            for index in range(start, len(text)):
                if text[index] == "(":
                    depth += 1
                elif text[index] == ")":
                    depth -= 1
                    if depth == 0:
                        end = index + 1
                        break
            self.assertIsNotNone(end)
            rule = text[start:end]
            self.assertLessEqual(rule.count("(") - 1, 32)
            cursor = end


if __name__ == "__main__":
    unittest.main()
