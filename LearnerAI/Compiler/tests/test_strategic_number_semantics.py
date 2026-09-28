import tempfile
import unittest
from pathlib import Path

from Compiler.ast import Expression, SourceLocation
from Compiler.semantic.rule_execution import analyze_effective_rules
from Compiler.source_graph import SourceGraphRequest, SourceGraphResolver
from Compiler.semantic.strategic_number_semantics import (
    StrategicNumberSemanticError,
    evaluate_strategic_number_comparison,
    evaluate_strategic_number_mutation,
    analyze_strategic_number_expressions,
    parse_strategic_number_comparison,
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
