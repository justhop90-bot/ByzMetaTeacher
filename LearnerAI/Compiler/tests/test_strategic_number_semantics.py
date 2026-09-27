import unittest

from Compiler.ast import Expression, SourceLocation
from Compiler.semantic.strategic_number_semantics import (
    StrategicNumberSemanticError,
    evaluate_strategic_number_mutation,
    parse_strategic_number_mutation,
)


class StrategicNumberSemanticsTests(unittest.TestCase):
    def _expr(self, *args):
        return Expression(
            source="(up-modify-sn ...)",
            head="up-modify-sn",
            args=tuple(args),
            location=SourceLocation(1, 1, "sn-test"),
        )

    def test_operand_domains_are_typed(self):
        constant = parse_strategic_number_mutation(self._expr("510", "c:+", "5"))
        goal = parse_strategic_number_mutation(self._expr("510", "g:+", "goal-x"))
        strategic = parse_strategic_number_mutation(self._expr("510", "s:+", "511"))

        self.assertEqual(constant.operand.kind.value, "CONSTANT")
        self.assertEqual(goal.operand.kind.value, "GOAL")
        self.assertEqual(strategic.operand.kind.value, "STRATEGIC_NUMBER")
        self.assertEqual(goal.operand.value, "goal-x")
        self.assertEqual(strategic.operand.value, "511")

    def test_all_constant_math_operators(self):
        cases = {
            "c:=": 3,
            "c:+": 11,
            "c:-": 5,
            "c:*": 24,
            "c:/": 3,
            "c:z/": 2,
            "c:mod": 2,
            "c:min": 3,
            "c:max": 8,
            "c:neg": -3,
            "c:%*": 2,
            "c:%/": 266,
        }
        for operator, expected in cases.items():
            with self.subTest(operator=operator):
                mutation = parse_strategic_number_mutation(
                    self._expr("510", operator, "3")
                )
                self.assertEqual(
                    evaluate_strategic_number_mutation(
                        mutation,
                        current_value=8,
                        goals={},
                        strategic_numbers={},
                    ),
                    expected,
                )

    def test_dynamic_goal_and_sn_operands_are_evaluated(self):
        goal_mutation = parse_strategic_number_mutation(
            self._expr("510", "g:+", "goal-x")
        )
        sn_mutation = parse_strategic_number_mutation(
            self._expr("510", "s:%*", "511")
        )

        self.assertEqual(
            evaluate_strategic_number_mutation(
                goal_mutation,
                current_value=40,
                goals={"goal-x": 80},
                strategic_numbers={"511": 25},
            ),
            120,
        )
        self.assertEqual(
            evaluate_strategic_number_mutation(
                sn_mutation,
                current_value=40,
                goals={},
                strategic_numbers={"511": 25},
            ),
            10,
        )

    def test_negative_division_uses_engine_style_nearest_integer(self):
        mutation = parse_strategic_number_mutation(self._expr("510", "c:/", "3"))
        self.assertEqual(
            evaluate_strategic_number_mutation(
                mutation,
                current_value=-8,
                goals={},
                strategic_numbers={},
            ),
            -3,
        )

    def test_zero_constant_divisors_are_rejected(self):
        for operator in ("c:/", "c:z/", "c:mod", "c:%/"):
            with self.subTest(operator=operator):
                with self.assertRaises(StrategicNumberSemanticError):
                    parse_strategic_number_mutation(
                        self._expr("510", operator, "0")
                    )

    def test_dynamic_zero_divisor_fails_at_runtime(self):
        mutation = parse_strategic_number_mutation(
            self._expr("510", "s:/", "511")
        )
        with self.assertRaises(StrategicNumberSemanticError):
            evaluate_strategic_number_mutation(
                mutation,
                current_value=8,
                goals={},
                strategic_numbers={"511": 0},
            )

    def test_invalid_prefix_is_rejected(self):
        with self.assertRaises(StrategicNumberSemanticError):
            parse_strategic_number_mutation(
                self._expr("510", "x:+", "1")
            )

    def test_wrong_arity_is_rejected(self):
        with self.assertRaises(StrategicNumberSemanticError):
            parse_strategic_number_mutation(
                Expression("(up-modify-sn)", "up-modify-sn", ("510", "c:+"))
            )

    def test_constant_operand_must_be_integer_and_in_range(self):
        with self.assertRaises(StrategicNumberSemanticError):
            parse_strategic_number_mutation(
                self._expr("510", "c:+", "not-an-int")
            )
        with self.assertRaises(StrategicNumberSemanticError):
            parse_strategic_number_mutation(
                self._expr("510", "c:+", "2147483648")
            )


if __name__ == "__main__":
    unittest.main()
