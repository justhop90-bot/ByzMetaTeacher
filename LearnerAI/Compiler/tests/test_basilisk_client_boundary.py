import importlib
import unittest


GENERIC_PUBLIC_MODULES = (
    "LearnerAI.Compiler",
    "LearnerAI.Compiler.compiler",
    "LearnerAI.Compiler.ir",
    "LearnerAI.Compiler.clients",
)

# These names are Basilisk-specific client API and must never become attributes
# of the generic compiler facades again.
BASILISK_STRATEGY_SYMBOLS = (
    "ByzantineProfile",
    "CapabilityIntent",
    "CapabilityIntentKind",
    "ExecutionDemandTemplate",
    "OpportunityCostPolicy",
    "PostureTransition",
    "ProtectedResourceFloor",
    "ResolvedStrategyProfile",
    "StrategicBinding",
    "StrategicCapabilityObservation",
    "StrategicCapabilityObservationKind",
    "StrategicDemandSpec",
    "StrategicObservationSpec",
    "StrategicEvidence",
    "StrategicEvidenceKind",
    "StrategicEvidenceSource",
    "StrategicPriority",
    "StrategicTarget",
    "StrategicTargetKind",
    "StrategyCompilation",
    "StrategyEnvelope",
    "StrategyPosture",
    "StrategyProfile",
    "EvidenceTruth",
    "ObservationReferenceBinding",
    "OpportunityCostRuntimeState",
    "ReassessmentReason",
    "RuntimeObservationSnapshot",
    "StrategicDemandRuntimeState",
    "StrategicEvidenceBinding",
    "StrategicObservation",
    "StrategicObservationType",
    "StrategicPredicate",
    "StrategyRuntimeState",
    "bind_observation_reference",
    "bind_strategic_capability_observation",
    "bind_strategic_evidence",
    "evaluate_binding",
    "evaluate_strategy_runtime",
    "build_byzantine_castle_strategy",
    "build_land_castle_strategy",
    "lower_strategy_profile",
    "resolve_strategy_profile",
    "compile_strategy_profile",
    "compile_strategy_runtime_profile",
)


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

    def test_generic_public_modules_cannot_reexport_basilisk_strategy_symbols(self):
        for module_name in GENERIC_PUBLIC_MODULES:
            module = importlib.import_module(module_name)
            for symbol in BASILISK_STRATEGY_SYMBOLS:
                with self.subTest(module=module_name, symbol=symbol):
                    self.assertFalse(
                        hasattr(module, symbol),
                        f"{module_name} must not re-export Basilisk symbol {symbol}",
                    )

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
