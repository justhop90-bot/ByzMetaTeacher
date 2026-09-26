import unittest

from LearnerAI.Compiler.ir.native_metadata import (
    NativeEngineProfile,
    default_de_native_profile,
)
from LearnerAI.Compiler.primitives.native_schema import (
    NativeCommandRegistry,
    NativeCommandSpec,
    NativeParameterSpec,
)
from LearnerAI.Compiler.primitives.registry import (
    NativeSupportState,
    Primitive,
    PrimitiveRegistry,
)


class NativeMetadataTests(unittest.TestCase):
    def test_default_profile_contains_separate_goal_sn_and_timer_ranges(self):
        profile = default_de_native_profile()

        self.assertEqual(profile.goal_range, (1, 16000))
        self.assertEqual(profile.strategic_number_range, (0, 511))
        self.assertEqual(profile.timer_range, (1, 50))

    def test_site_specific_logistica_alias_is_not_treated_as_builtin(self):
        profile = default_de_native_profile()
        symbol = profile.identifier("ri-logistica")

        self.assertEqual(symbol.numeric_id, 61)
        self.assertFalse(symbol.built_in)
        self.assertTrue(symbol.local_alias_required)

        with self.assertRaisesRegex(ValueError, "local alias"):
            profile.require_symbol("ri-logistica")

        resolved = profile.require_symbol("ri-logistica", local_aliases={"ri-logistica"})
        self.assertIsNotNone(resolved)

    def test_profile_is_immutable(self):
        profile = default_de_native_profile()
        self.assertIsInstance(profile, NativeEngineProfile)
        with self.assertRaises(Exception):
            profile.goal_range = (1, 10)


class NativeSupportStateTests(unittest.TestCase):
    def test_current_command_reaches_executable_safe(self):
        registry = PrimitiveRegistry(
            (Primitive('current-age', 'FACT', 'OBSERVATION', 2, 2),),
            NativeCommandRegistry(
                (NativeCommandSpec(
                    'current-age',
                    'DE',
                    'Fact',
                    (NativeParameterSpec('Age', 'Age', 'in', 'a valid age', 'check age'),
                     NativeParameterSpec('Compare', 'compareOp', 'in', 'a comparison', 'compare'),),
                ),),
                source_blob_sha='test',
                command_count=1,
            ),
        )
        assessment = registry.assess_support('current-age')
        self.assertEqual(assessment.state, NativeSupportState.EXECUTABLE_SAFE)
        self.assertEqual(
            [diagnostic.state for diagnostic in assessment.diagnostics],
            [
                NativeSupportState.NATIVE_KNOWN,
                NativeSupportState.NATIVE_TYPED,
                NativeSupportState.SEMANTICALLY_ADAPTED,
                NativeSupportState.EXECUTABLE_SAFE,
            ],
        )
        self.assertEqual(
            [diagnostic.code for diagnostic in assessment.diagnostics],
            ['NATIVE-SUPPORT-001', 'NATIVE-SUPPORT-002', 'NATIVE-SUPPORT-003', 'NATIVE-SUPPORT-004'],
        )

    def test_known_typed_command_without_adapter_is_unsupported(self):
        registry = PrimitiveRegistry(
            (),
            NativeCommandRegistry(
                (NativeCommandSpec(
                    'up-find-flare',
                    'UP',
                    'Action',
                    (NativeParameterSpec('Point', 'Goal', 'out', '41 to 15998', 'point pair'),),
                ),),
                source_blob_sha='test',
                command_count=1,
            ),
        )
        assessment = registry.assess_support('up-find-flare')
        self.assertEqual(assessment.state, NativeSupportState.UNSUPPORTED)
        self.assertEqual(
            [diagnostic.state for diagnostic in assessment.diagnostics],
            [NativeSupportState.NATIVE_KNOWN, NativeSupportState.NATIVE_TYPED],
        )
        self.assertEqual(assessment.message, 'native command is known and typed but has no semantic adapter')
        self.assertEqual(assessment.diagnostics[-1].code, 'NATIVE-SUPPORT-005')

    def test_malformed_native_metadata_stops_at_native_known(self):
        registry = PrimitiveRegistry(
            (),
            NativeCommandRegistry(
                (NativeCommandSpec(
                    'broken-command',
                    'DE',
                    'Fact',
                    (NativeParameterSpec('', '', '', '', ''),),
                ),),
                source_blob_sha='test',
                command_count=1,
            ),
        )
        assessment = registry.assess_support('broken-command')
        self.assertEqual(assessment.state, NativeSupportState.UNSUPPORTED)
        self.assertEqual(
            [diagnostic.state for diagnostic in assessment.diagnostics],
            [NativeSupportState.NATIVE_KNOWN],
        )
        self.assertIn('native metadata is not typed', assessment.message)

    def test_adapted_but_contract_invalid_never_becomes_executable_safe(self):
        registry = PrimitiveRegistry(
            (Primitive('synthetic', 'ACTION', 'ACTION', 2, 2),),
            NativeCommandRegistry(
                (NativeCommandSpec(
                    'synthetic',
                    'DE',
                    'Action',
                    (NativeParameterSpec('Only', 'Const', 'in', 'x', 'single parameter'),),
                ),),
                source_blob_sha='test',
                command_count=1,
            ),
        )
        assessment = registry.assess_support('synthetic')
        self.assertEqual(assessment.state, NativeSupportState.UNSUPPORTED)
        self.assertEqual(
            [diagnostic.state for diagnostic in assessment.diagnostics],
            [
                NativeSupportState.NATIVE_KNOWN,
                NativeSupportState.NATIVE_TYPED,
                NativeSupportState.SEMANTICALLY_ADAPTED,
            ],
        )
        self.assertEqual(assessment.diagnostics[-1].code, 'NATIVE-SUPPORT-005')

    def test_unknown_command_is_deterministically_unsupported(self):
        registry = PrimitiveRegistry((), NativeCommandRegistry((), source_blob_sha='test', command_count=0))
        assessment = registry.assess_support('not-a-command')
        self.assertEqual(assessment.state, NativeSupportState.UNSUPPORTED)
        self.assertEqual(assessment.diagnostics[0].state, NativeSupportState.UNSUPPORTED)
        self.assertEqual(assessment.diagnostics[0].code, 'NATIVE-SUPPORT-005')

    def test_support_diagnostics_are_deterministic(self):
        registry = PrimitiveRegistry(
            (
                Primitive('current-age', 'FACT', 'OBSERVATION', 2, 2),
                Primitive('build', 'ACTION', 'ACTION', 1, 1),
            ),
            NativeCommandRegistry(
                (
                    NativeCommandSpec('build', 'DE', 'Action', (NativeParameterSpec('Building', 'BuildingId', 'in', 'id', 'building'),)),
                    NativeCommandSpec('current-age', 'DE', 'Fact', (NativeParameterSpec('Age', 'Age', 'in', 'id', 'age'), NativeParameterSpec('Compare', 'compareOp', 'in', 'op', 'compare'))),
                ),
                source_blob_sha='test',
                command_count=2,
            ),
        )
        first = registry.support_diagnostics(('build', 'current-age'))
        second = registry.support_diagnostics(('build', 'current-age'))
        self.assertEqual(first, second)
        self.assertEqual([item.command for item in first], ['build', 'current-age'])


if __name__ == "__main__":
    unittest.main()
