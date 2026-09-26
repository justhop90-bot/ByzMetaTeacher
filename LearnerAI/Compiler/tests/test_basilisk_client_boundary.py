import unittest


class BasiliskClientBoundaryTests(unittest.TestCase):
    def test_generic_compiler_does_not_export_basilisk_strategy_entrypoints(self):
        import LearnerAI.Compiler.compiler as generic

        self.assertFalse(hasattr(generic, "compile_strategy_profile"))
        self.assertFalse(hasattr(generic, "compile_strategy_runtime_profile"))

    def test_generic_ir_does_not_export_downstream_strategy_symbols(self):
        import LearnerAI.Compiler.ir as generic_ir

        self.assertFalse(hasattr(generic_ir, "StrategyProfile"))
        self.assertFalse(hasattr(generic_ir, "StrategyPosture"))
        self.assertFalse(hasattr(generic_ir, "build_byzantine_castle_strategy"))

    def test_basilisk_client_namespace_owns_strategy_exports(self):
        from LearnerAI.Compiler.clients.basilisk import (
            ByzantineProfile,
            StrategyPosture,
            StrategyProfile,
            build_byzantine_castle_strategy,
            compile_strategy_profile,
            compile_strategy_runtime_profile,
        )

        self.assertTrue(callable(compile_strategy_profile))
        self.assertTrue(callable(compile_strategy_runtime_profile))
        self.assertTrue(callable(build_byzantine_castle_strategy))
        self.assertIsNotNone(ByzantineProfile)
        self.assertIsNotNone(StrategyPosture)
        self.assertIsNotNone(StrategyProfile)


if __name__ == "__main__":
    unittest.main()
