import unittest
from enum import Enum

from Compiler.semantic.fact_values import (
    CanonicalEnum,
    CanonicalIdentifier,
    CanonicalInteger,
    CanonicalKind,
    CanonicalSymbol,
    CanonicalizationContext,
    IdentifierForm,
    canonicalize_value,
)


class ExampleAge(str, Enum):
    DARK = "DARK"
    CASTLE = "CASTLE"


class CanonicalFactValueTests(unittest.TestCase):
    def test_integer_normalization_rejects_bool_and_normalizes_decimal_text(self):
        context = CanonicalizationContext.integer(parameter_name="Value")

        self.assertEqual(
            canonicalize_value(42, context),
            CanonicalInteger(42),
        )
        self.assertEqual(
            canonicalize_value("0042", context),
            CanonicalInteger(42),
        )

        with self.assertRaisesRegex(ValueError, "boolean"):
            canonicalize_value(True, context)

    def test_enum_normalization_is_domain_scoped_and_accepts_enum_instances(self):
        context = CanonicalizationContext.enum(
            parameter_name="Age",
            domain="AGE",
            members=("DARK", "CASTLE"),
        )

        self.assertEqual(
            canonicalize_value("castle", context),
            CanonicalEnum("AGE", "CASTLE"),
        )
        self.assertEqual(
            canonicalize_value(ExampleAge.CASTLE, context),
            CanonicalEnum("AGE", "CASTLE"),
        )

        with self.assertRaisesRegex(ValueError, "not a member"):
            canonicalize_value("IMPERIAL", context)

    def test_identifier_normalization_preserves_namespace_and_reference_form(self):
        context = CanonicalizationContext.identifier(
            parameter_name="BuildingId",
            namespace="BUILDING",
            accepted_forms=(
                IdentifierForm.NAME,
                IdentifierForm.NUMERIC_ID,
                IdentifierForm.CLASS,
            ),
            names=("castle",),
            classes=("building-class",),
        )

        self.assertEqual(
            canonicalize_value(109, context),
            CanonicalIdentifier(
                namespace="BUILDING",
                form=IdentifierForm.NUMERIC_ID,
                value=109,
            ),
        )
        self.assertEqual(
            canonicalize_value("castle", context),
            CanonicalIdentifier(
                namespace="BUILDING",
                form=IdentifierForm.NAME,
                value="castle",
            ),
        )
        self.assertEqual(
            canonicalize_value("building-class", context),
            CanonicalIdentifier(
                namespace="BUILDING",
                form=IdentifierForm.CLASS,
                value="BUILDING-CLASS",
            ),
        )

        self.assertNotEqual(
            CanonicalIdentifier("BUILDING", IdentifierForm.NUMERIC_ID, 7),
            CanonicalIdentifier("UNIT", IdentifierForm.NUMERIC_ID, 7),
        )

    def test_symbol_normalization_preserves_symbol_namespace(self):
        context = CanonicalizationContext.symbol(
            parameter_name="Goal",
            namespace="GOAL",
        )

        self.assertEqual(
            canonicalize_value("strategy-goal", context),
            CanonicalSymbol(
                namespace="GOAL",
                name="strategy-goal",
            ),
        )

        self.assertNotEqual(
            CanonicalSymbol("GOAL", "strategy-goal"),
            CanonicalSymbol("STRATEGIC_NUMBER", "strategy-goal"),
        )

    def test_canonical_kind_is_explicit_for_union_members(self):
        self.assertEqual(
            CanonicalInteger(1).kind,
            CanonicalKind.INTEGER,
        )
        self.assertEqual(
            CanonicalEnum("AGE", "CASTLE").kind,
            CanonicalKind.ENUM,
        )
        self.assertEqual(
            CanonicalIdentifier("UNIT", IdentifierForm.NUMERIC_ID, 7).kind,
            CanonicalKind.IDENTIFIER,
        )
        self.assertEqual(
            CanonicalSymbol("GOAL", "x").kind,
            CanonicalKind.SYMBOL,
        )


if __name__ == "__main__":
    unittest.main()
