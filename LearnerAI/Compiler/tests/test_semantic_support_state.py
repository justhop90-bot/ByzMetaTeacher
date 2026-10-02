                is NativeSupportState.EXECUTABLE_SAFE
                for name in registry.names()
            )
        )


    def test_default_semantic_mapping_catalog_is_exact_and_contracted(self):
        from Compiler.semantic.community_engine import default_community_engine_registry

        mapping_registry = default_engine_semantic_mapping_registry()
        from Compiler.primitives.engine_semantics import (
            default_duc_executable_commands,
            default_escrow_executable_commands,
            default_native_controller_executable_commands,
            default_native_control_plane_executable_commands,
        )
        from Compiler.primitives.native_hygiene import (
            default_native_output_goal_contracts,
        )

        expected_commands = tuple(
            sorted(
                tuple(default_de_registry().names())
                + tuple(item.command for item in default_native_output_goal_contracts())
                + tuple(default_duc_executable_commands())
                + tuple(default_escrow_executable_commands())
                + tuple(default_native_controller_executable_commands())
                + tuple(default_native_control_plane_executable_commands())
            )
        )
        self.assertEqual(
            tuple(
                sorted(
                    item.native_command
                    for item in mapping_registry.mappings
                    if item.status is EngineSemanticMappingStatus.CONTRACTED
                )
            ),
            expected_commands,
        )
        self.assertTrue(
            all(
                item.status is EngineSemanticMappingStatus.CONTRACTED
                for item in mapping_registry.mappings
                if item.native_command is not None
            )
        )
        practice_ids = {
            item.identity
            for item in default_community_engine_registry().practices
        }
        for item in mapping_registry.mappings:
            self.assertTrue(set(item.practice_references).issubset(practice_ids))