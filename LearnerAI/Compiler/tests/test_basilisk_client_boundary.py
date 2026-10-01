import ast
import importlib
import pkgutil
import unittest
from pathlib import Path


GENERIC_PUBLIC_MODULES = (
    "LearnerAI.Compiler",
    "LearnerAI.Compiler.compiler",
    "LearnerAI.Compiler.ir",
    "LearnerAI.Compiler.clients",
)

# These names are Basilisk-specific client API and must never become attributes
# of the generic compiler facades again.
DOWNSTREAM_CLIENT_MODULE_PREFIXES = (
    "LearnerAI.Compiler.clients.basilisk",
    "LearnerAI.Compiler.ir.strategy",
    "LearnerAI.Compiler.ir.strategy_runtime",
)


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
    "PolicyBindingRequirement",
    "PolicyField",
    "PolicyOverride",
    "PolicyOverrideKind",
    "PolicyRecipe",
    "PolicyResolution",
    "PolicyStrength",
    "PolicyTerm",
    "default_byzantine_policy_recipes",
    "resolve_policy_recipe",
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


    def test_every_generic_package_module_rejects_basilisk_reexports(self):
        import LearnerAI.Compiler as compiler_package
        import LearnerAI.Compiler.clients.basilisk as basilisk_client

        canonical_symbols = {
            name: getattr(basilisk_client, name)
            for name in BASILISK_STRATEGY_SYMBOLS
        }
        canonical_ids = {id(value): name for name, value in canonical_symbols.items()}

        module_names = {compiler_package.__name__}
        module_names.update(
            info.name
            for info in pkgutil.walk_packages(
                compiler_package.__path__,
                compiler_package.__name__ + ".",
            )
        )

        for module_name in sorted(module_names):
            if any(
                module_name == prefix or module_name.startswith(prefix + ".")
                for prefix in DOWNSTREAM_CLIENT_MODULE_PREFIXES
            ):
                continue
            module = importlib.import_module(module_name)
            for symbol_name in dir(module):
                if symbol_name.startswith("_"):
                    continue
                value = getattr(module, symbol_name)
                canonical_name = canonical_ids.get(id(value))
                if canonical_name is None:
                    continue
                origin = getattr(value, "__module__", None)
                if origin == module_name:
                    continue
                with self.subTest(
                    module=module_name,
                    symbol=symbol_name,
                    canonical=canonical_name,
                ):
                    self.fail(
                        f"{module_name}.{symbol_name} re-exports Basilisk strategy "
                        f"symbol {canonical_name} from {origin}"
                    )

    def test_generic_source_does_not_import_downstream_strategy_policy(self):
        compiler_root = Path(__file__).parents[1]
        forbidden = DOWNSTREAM_CLIENT_MODULE_PREFIXES
        violations = []

        for source_path in sorted(compiler_root.rglob("*.py")):
            relative = source_path.relative_to(compiler_root).as_posix()
            if relative.startswith("clients/basilisk/"):
                continue
            if relative.startswith("tests/"):
                continue

            tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
            for node in ast.walk(tree):
                imported: str | None = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported = alias.name
                        if any(
                            imported == prefix or imported.startswith(prefix + ".")
                            for prefix in forbidden
                        ):
                            violations.append((relative, node.lineno, imported))
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if node.level:
                        continue
                    imported = module
                    if any(
                        imported == prefix or imported.startswith(prefix + ".")
                        for prefix in forbidden
                    ):
                        violations.append((relative, node.lineno, imported))

        self.assertEqual(
            violations,
            [],
            "generic compiler source must not import downstream strategy policy: "
            f"{violations}",
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
