import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.backends.errors import NativeBackendError
from Compiler.backends.models import (
    ArtifactIdentity,
    BackendIdentity,
    InvocationResult,
    NativeValidationResult,
    ValidationStatus,
    ValidationSummary,
)
from Compiler.compiler import (
    compile_package_with_report,
    compile_source,
    compile_source_with_report,
    compile_to_file,
)
from Compiler.source_graph import SourceGraphRequest
from Compiler.primitives.native_schema import NativeCommandRegistry, NativeCommandSpec, NativeParameterSpec, load_default_native_schema
from Compiler.primitives.registry import NativeSupportState, Primitive, PrimitiveRegistry, default_de_registry
from Compiler.primitives.engine_semantics import (
    EngineSemanticMapping,
    EngineSemanticMappingRegistry,
    EngineSemanticMappingStatus,
    default_engine_semantic_mapping_registry,
)
from Compiler.diagnostics import DiagnosticSeverity, ReportStatus
from Compiler.ast import SourceLocation, Expression
from Compiler.ir import (
    AttackLifecycleObservation,
    NativeAttackLifecyclePlan,
    NativeAttackRule,
    NativeDucPlan,
    NativeDucRule,
)

EXAMPLES = (Path(__file__).parents[1] / "examples" / "basics.perdsl").read_text(encoding="utf-8")


def persistent_rule_diagnostic():
    return SimpleNamespace(
        rule_order=2,
        code=SimpleNamespace(value="PSTATE-002"),
        severity=DiagnosticSeverity.WARNING,
        eligibility=None,
        message="goal state '7' has a later writer in rule 2 after writer in rule 1",
        location=SimpleNamespace(line=1, column=1, source_unit="<generated>"),
        category=SimpleNamespace(value="PERSISTENT_STATE"),
        source_code="PSTATE-002",
        state_kind="GOAL",
        state_identifier="7",
        related_rule_order=1,
        related_operation="set-goal",
    )

def fake_result(output: Path, status: ValidationStatus) -> NativeValidationResult:
    backend = BackendIdentity("aoe2-ai-parser", "0.1.0", "3dfa2583b7c2ec36b85ccb421ebd0abe9ff276ba", "3.12.7")
    artifact = ArtifactIdentity(output.resolve(), "0" * 64)
    return NativeValidationResult(
        status=status,
        failed=status is ValidationStatus.REJECTED,
        backend=backend,
        invocation=InvocationResult("default", output.resolve(), 0 if status is ValidationStatus.VALIDATED else 1, 1),
        artifact=artifact,
        summary=ValidationSummary(0, 0, 0, 0, 0),
        diagnostics=(),
        stderr="" if status is ValidationStatus.VALIDATED else "backend unavailable",
    )


class FakeBackend:
    def __init__(self, result):
        self.result = result
        self.seen_artifact = None
        self.seen_artifact_text = None
        self.seen_artifact_bytes = None

    def validate(self, artifact: Path):
        self.seen_artifact = artifact
        self.seen_artifact_text = artifact.read_text(encoding="utf-8")
        self.seen_artifact_bytes = artifact.read_bytes()
        return self.result

class CompilerNativeIntegrationTests(unittest.TestCase):
    @staticmethod
    def _attack_plan():
        lifecycle = (
            AttackLifecycleObservation.ADMISSION_REQUIRED,
            AttackLifecycleObservation.ISSUE,
            AttackLifecycleObservation.COMPLETION_UNOBSERVED,
            AttackLifecycleObservation.REASSESS_REQUIRED,
        )
        return NativeAttackLifecyclePlan(
            (
                NativeAttackRule(
                    identity="attack-first",
                    order=10,
                    facts=(
                        Expression("(true)", "true", ()),
                    ),
                    actions=(
                        Expression("(attack-now)", "attack-now", ()),
                    ),
                    lifecycle=lifecycle,
                ),
                NativeAttackRule(
                    identity="attack-second",
                    order=20,
                    facts=(
                        Expression("(true)", "true", ()),
                    ),
                    actions=(
                        Expression("(attack-now)", "attack-now", ()),
                    ),
                    lifecycle=lifecycle,
                ),
            )
        )

    @staticmethod
    def _duc_plan():
        return NativeDucPlan(
            (
                NativeDucRule(
                    identity="search-and-select",
                    order=100,
                    facts=(
                        Expression(
                            "(up-find-local c: villager c: 1)",
                            "up-find-local",
                            ("c:", "villager", "c:", "1"),
                        ),
                    ),
                    actions=(
                        Expression(
                            "(up-set-target-object search-local c: 0)",
                            "up-set-target-object",
                            ("search-local", "c:", "0"),
                        ),
                    ),
                ),
                NativeDucRule(
                    identity="target-action",
                    order=101,
                    facts=(
                        Expression(
                            "(up-set-target-object search-local c: 0)",
                            "up-set-target-object",
                            ("search-local", "c:", "0"),
                        ),
                    ),
                    actions=(
                        Expression(
                            "(up-target-objects 1 action-default -1 -1)",
                            "up-target-objects",
                            ("1", "action-default", "-1", "-1"),
                        ),
                    ),
                ),
            )
        )

    def test_public_compile_source_forwards_attack_plan(self):
        source = """
        demand marker {
            require (can-train spearman)
            action (train spearman)
            witness (unit-type-count spearman >= 1)
            release (unit-type-count spearman >= 1)
        }
        """
        artifact = compile_source(
            source,
            attack_plan=self._attack_plan(),
        )
        self.assertIn("; Native attack lifecycle plan", artifact)
        self.assertIn("; Native attack rule: attack-first", artifact)
        self.assertIn("; Native attack rule: attack-second", artifact)
        self.assertEqual(artifact.count("(attack-now)"), 2)

    def test_internal_attack_plan_survives_binding_and_emission(self):
        source = """
        demand marker {
            require (can-train spearman)
            action (train spearman)
            witness (unit-type-count spearman >= 1)
            release (unit-type-count spearman >= 1)
        }
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            first = tmp / "first.per"
            second = tmp / "second.per"

            first_backend = FakeBackend(
                fake_result(first, ValidationStatus.VALIDATED)
            )
            second_backend = FakeBackend(
                fake_result(second, ValidationStatus.VALIDATED)
            )

            first_report = compile_to_file(
                source,
                first,
                native_backend=first_backend,
                attack_plan=self._attack_plan(),
            )
            second_report = compile_to_file(
                source,
                second,
                native_backend=second_backend,
                attack_plan=self._attack_plan(),
            )

            self.assertEqual(first_report.status, ValidationStatus.VALIDATED)
            self.assertEqual(second_report.status, ValidationStatus.VALIDATED)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            artifact = first.read_text(encoding="utf-8")
            self.assertIn("; Native attack lifecycle plan", artifact)
            self.assertLess(
                artifact.index("; Native attack rule: attack-first"),
                artifact.index("; Native attack rule: attack-second"),
            )
            self.assertEqual(artifact.count("(attack-now)"), 2)
            self.assertNotIn("(up-reset-attack-now)", artifact)
            self.assertNotIn("(timer-triggered", artifact)
            self.assertIn("(attack-now)", first_backend.seen_artifact_text)

    def test_internal_duc_plan_survives_binding_and_emission(self):
        source = """
        demand marker {
            require (can-train spearman)
            action (train spearman)
            witness (unit-type-count spearman >= 1)
            release (unit-type-count spearman >= 1)
        }
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            first = tmp / "first.per"
            second = tmp / "second.per"

            first_backend = FakeBackend(
                fake_result(first, ValidationStatus.VALIDATED)
            )
            second_backend = FakeBackend(
                fake_result(second, ValidationStatus.VALIDATED)
            )

            first_report = compile_to_file(
                source,
                first,
                native_backend=first_backend,
                duc_plan=self._duc_plan(),
            )
            second_report = compile_to_file(
                source,
                second,
                native_backend=second_backend,
                duc_plan=self._duc_plan(),
            )

            self.assertEqual(first_report.status, ValidationStatus.VALIDATED)
            self.assertEqual(second_report.status, ValidationStatus.VALIDATED)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertIn("; Native DUC execution plan", first.read_text(encoding="utf-8"))
            self.assertIn("; Native DUC rule: search-and-select", first.read_text(encoding="utf-8"))
            self.assertIn("(up-find-local c: villager c: 1)", first_backend.seen_artifact_text)
            self.assertIn("(up-target-objects 1 action-default -1 -1)", first_backend.seen_artifact_text)

    def test_compile_to_file_requires_native_validation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "CompilerFixture.per"

            with self.assertRaises(NativeBackendError):
                compile_to_file(EXAMPLES, output)

            self.assertFalse(output.exists())

    def test_compile_source_with_report_requires_native_validation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "Basilisk.per"
            output.write_text("KEEP THIS\n", encoding="utf-8")

            report = compile_source_with_report(EXAMPLES, output)

            self.assertEqual(report.status, ReportStatus.BACKEND_FAILURE)
            self.assertEqual(output.read_text(encoding="utf-8"), "KEEP THIS\n")
            self.assertEqual(
                report.diagnostics[0].code,
                "NATIVE-VALIDATION-REQUIRED",
            )

    def test_validated_backend_with_findings_never_promotes(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            output = tmp / "Basilisk.per"
            output.write_text("KEEP THIS\n", encoding="utf-8")
            result = fake_result(output, ValidationStatus.VALIDATED)
            result = NativeValidationResult(
                status=result.status,
                failed=False,
                backend=result.backend,
                invocation=result.invocation,
                artifact=result.artifact,
                summary=ValidationSummary(1, 0, 1, 0, 0),
                diagnostics=(),
                stderr="",
            )
            fake = FakeBackend(result)

            validation = compile_to_file(EXAMPLES, output, native_backend=fake)

            self.assertEqual(validation.status, ValidationStatus.BACKEND_PROTOCOL_ERROR)
            self.assertEqual(output.read_text(encoding="utf-8"), "KEEP THIS\n")

    def test_validated_backend_promotes_staged_output(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            output = tmp / "Basilisk.per"
            output.write_text("OLD ARTIFACT\n", encoding="utf-8")
            fake = FakeBackend(fake_result(output, ValidationStatus.VALIDATED))

            result = compile_to_file(EXAMPLES, output, native_backend=fake)

            self.assertEqual(result.status, ValidationStatus.VALIDATED)
            self.assertIn("AOE2 .PER GENERATED BY COMPILER", output.read_text(encoding="utf-8"))
            self.assertIsNotNone(fake.seen_artifact)
            self.assertNotEqual(fake.seen_artifact, output)

    def test_persistent_rule_diagnostics_are_embedded_in_promoted_artifact(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            output = tmp / "Basilisk.per"
            fake = FakeBackend(fake_result(output, ValidationStatus.VALIDATED))
            diagnostic = SimpleNamespace(
                rule_order=2,
                code=SimpleNamespace(value="PSTATE-002"),
                severity=DiagnosticSeverity.WARNING,
                eligibility=None,
                message="goal state '7' has a later writer in rule 2 after writer in rule 1",
                location=SourceLocation(1, 1, "<generated>"),
                category=SimpleNamespace(value="PERSISTENT_STATE"),
                source_code="PSTATE-002",
                state_kind="GOAL",
                state_identifier="7",
                related_rule_order=1,
                related_operation="set-goal",
            )
            rule_report = SimpleNamespace(diagnostics=(diagnostic,))

            with patch(
                "Compiler.compiler.analyze_rule_diagnostics",
                return_value=rule_report,
            ):
                result = compile_to_file(
                    EXAMPLES,
                    output,
                    native_backend=fake,
                )

            self.assertEqual(result.status, ValidationStatus.VALIDATED)
            artifact = output.read_text(encoding="utf-8")
            self.assertIn("; COMPILER RULE DIAGNOSTICS", artifact)
            self.assertIn(
                "; PERSISTENT_STATE rule=2 code=PSTATE-002 severity=warning "
                "state=GOAL:7 related-rule=1 related-operation=set-goal",
                artifact,
            )
            self.assertIn(
                "; message=goal state '7' has a later writer in rule 2 after writer in rule 1",
                artifact,
            )
            self.assertIsNotNone(fake.seen_artifact)
            self.assertNotIn(b"\r\n", fake.seen_artifact_bytes)

    def test_package_promotion_embeds_persistent_state_annotation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            root = tmp / "root.perdsl"
            child = tmp / "child.perdsl"
            output = tmp / "Basilisk.per"
            child.write_text(
                """
                demand castle {
                    require (can-build castle)
                    action (build castle)
                    witness (building-type-count castle > 0)
                    release (building-type-count castle > 0)
                }
                """,
                encoding="utf-8",
            )
            root.write_text('(load "child.perdsl")\n', encoding="utf-8")
            fake = FakeBackend(fake_result(output, ValidationStatus.VALIDATED))

            with patch(
                "Compiler.compiler.analyze_rule_diagnostics",
                return_value=SimpleNamespace(
                    diagnostics=(persistent_rule_diagnostic(),)
                ),
            ):
                report = compile_package_with_report(
                    SourceGraphRequest(entrypoint=root),
                    output,
                    native_backend=fake,
                )

            self.assertEqual(report.status, ReportStatus.VALIDATED)
            artifact = output.read_text(encoding="utf-8")
            self.assertIn("; COMPILER RULE DIAGNOSTICS", artifact)
            self.assertIn("PSTATE-002", artifact)
            self.assertIn("(build castle)", artifact)
            self.assertIn("; COMPILER RULE DIAGNOSTICS", fake.seen_artifact_text)
            self.assertNotIn(b"\r\n", fake.seen_artifact_bytes)

    def test_rejected_source_promotion_preserves_old_artifact_and_validates_annotated_stage(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            output = tmp / "Basilisk.per"
            output.write_text("KEEP OLD ARTIFACT\n", encoding="utf-8")
            fake = FakeBackend(fake_result(output, ValidationStatus.REJECTED))

            with patch(
                "Compiler.compiler.analyze_rule_diagnostics",
                return_value=SimpleNamespace(
                    diagnostics=(persistent_rule_diagnostic(),)
                ),
            ):
                report = compile_source_with_report(
                    EXAMPLES,
                    output,
                    native_backend=fake,
                )

            self.assertEqual(report.status, ReportStatus.NATIVE_REJECTED)
            self.assertEqual(output.read_text(encoding="utf-8"), "KEEP OLD ARTIFACT\n")
            self.assertIn("; COMPILER RULE DIAGNOSTICS", fake.seen_artifact_text)
            self.assertIn("PSTATE-002", fake.seen_artifact_text)

    def test_rejected_package_promotion_preserves_old_artifact_and_validates_annotated_stage(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            root = tmp / "root.perdsl"
            child = tmp / "child.perdsl"
            output = tmp / "Basilisk.per"
            child.write_text(EXAMPLES, encoding="utf-8")
            root.write_text('(load "child.perdsl")\n', encoding="utf-8")
            output.write_text("KEEP OLD PACKAGE ARTIFACT\n", encoding="utf-8")
            fake = FakeBackend(fake_result(output, ValidationStatus.REJECTED))

            with patch(
                "Compiler.compiler.analyze_rule_diagnostics",
                return_value=SimpleNamespace(
                    diagnostics=(persistent_rule_diagnostic(),)
                ),
            ):
                report = compile_package_with_report(
                    SourceGraphRequest(entrypoint=root),
                    output,
                    native_backend=fake,
                )

            self.assertEqual(report.status, ReportStatus.NATIVE_REJECTED)
            self.assertEqual(output.read_text(encoding="utf-8"), "KEEP OLD PACKAGE ARTIFACT\n")
            self.assertIn("; COMPILER RULE DIAGNOSTICS", fake.seen_artifact_text)

    def test_repeated_file_promotion_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            first = tmp / "first.per"
            second = tmp / "second.per"

            for output in (first, second):
                fake = FakeBackend(fake_result(output, ValidationStatus.VALIDATED))
                with patch(
                    "Compiler.compiler.analyze_rule_diagnostics",
                    return_value=SimpleNamespace(
                        diagnostics=(persistent_rule_diagnostic(),)
                    ),
                ):
                    report = compile_to_file(
                        EXAMPLES,
                        output,
                        native_backend=fake,
                    )
                self.assertEqual(report.status, ValidationStatus.VALIDATED)

            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_repeated_package_promotion_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            root = tmp / "root.perdsl"
            child = tmp / "child.perdsl"
            first = tmp / "first.per"
            second = tmp / "second.per"
            child.write_text(EXAMPLES, encoding="utf-8")
            root.write_text('(load "child.perdsl")\n', encoding="utf-8")

            for output in (first, second):
                fake = FakeBackend(fake_result(output, ValidationStatus.VALIDATED))
                with patch(
                    "Compiler.compiler.analyze_rule_diagnostics",
                    return_value=SimpleNamespace(
                        diagnostics=(persistent_rule_diagnostic(),)
                    ),
                ):
                    report = compile_package_with_report(
                        SourceGraphRequest(entrypoint=root),
                        output,
                        native_backend=fake,
                    )
                self.assertEqual(report.status, ReportStatus.VALIDATED)

            self.assertEqual(first.read_bytes(), second.read_bytes())
    def test_rejected_backend_does_not_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            output = tmp / "Basilisk.per"
            output.write_text("KEEP THIS\n", encoding="utf-8")
            fake = FakeBackend(fake_result(output, ValidationStatus.REJECTED))

            result = compile_to_file(EXAMPLES, output, native_backend=fake)

            self.assertEqual(result.status, ValidationStatus.REJECTED)
            self.assertEqual(output.read_text(encoding="utf-8"), "KEEP THIS\n")

    def test_backend_failure_does_not_promote_artifact(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            output = tmp / "Basilisk.per"
            output.write_text("KEEP THIS\n", encoding="utf-8")
            fake = FakeBackend(fake_result(output, ValidationStatus.BACKEND_TIMEOUT))

            result = compile_to_file(EXAMPLES, output, native_backend=fake)

            self.assertEqual(result.status, ValidationStatus.BACKEND_TIMEOUT)
            self.assertEqual(output.read_text(encoding="utf-8"), "KEEP THIS\n")


    def test_validated_backend_promotes_binding_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            output = tmp / "Basilisk.per"
            manifest = tmp / "Basilisk.bindings.json"
            fake = FakeBackend(fake_result(output, ValidationStatus.VALIDATED))

            result = compile_to_file(
                EXAMPLES,
                output,
                native_backend=fake,
                binding_manifest=manifest,
            )

            self.assertEqual(result.status, ValidationStatus.VALIDATED)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(payload["format_version"], 4)
            self.assertEqual(len(payload["records"]), 5)
            self.assertTrue(all("goal_id" in record for record in payload["records"]))
            self.assertEqual(payload["integrity"]["algorithm"], "SHA-256")
            self.assertEqual(len(payload["integrity"]["content_sha256"]), 64)

    def test_rejected_backend_does_not_overwrite_existing_binding_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            output = tmp / "Basilisk.per"
            manifest = tmp / "Basilisk.bindings.json"
            output.write_text("KEEP THIS\n", encoding="utf-8")
            manifest.write_text("KEEP MANIFEST\n", encoding="utf-8")
            fake = FakeBackend(fake_result(output, ValidationStatus.REJECTED))

            result = compile_to_file(
                EXAMPLES,
                output,
                native_backend=fake,
                binding_manifest=manifest,
            )

            self.assertEqual(result.status, ValidationStatus.REJECTED)
            self.assertEqual(output.read_text(encoding="utf-8"), "KEEP THIS\n")
            self.assertEqual(manifest.read_text(encoding="utf-8"), "KEEP MANIFEST\n")

    def test_compiler_manifest_carries_package_inventory_fingerprint(self):
        from Compiler.runtime_binding import (
            BindingContext,
            PackageStorageInventory,
            PackageStorageReservation,
            StorageKind,
        )

        inventory = PackageStorageInventory(
            package_id="compiler-test",
            package_revision="r1",
            reservations=(
                PackageStorageReservation(
                    kind=StorageKind.GOAL_SLOT,
                    start=500,
                    end=500,
                    provenance_id="external-goal",
                ),
            ),
        )
        context = BindingContext.from_package_inventory(inventory)
        source = EXAMPLES
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            output = tmp / "Basilisk.per"
            manifest = tmp / "Basilisk.bindings.json"
            fake = FakeBackend(fake_result(output, ValidationStatus.VALIDATED))

            result = compile_to_file(
                source,
                output,
                native_backend=fake,
                binding_context=context,
                binding_manifest=manifest,
            )

            self.assertEqual(result.status, ValidationStatus.VALIDATED)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["package_inventory_sha"],
                inventory.inventory_sha,
            )
            self.assertEqual(
                json.loads(inventory.to_json())["inventory_sha"],
                payload["package_inventory_sha"],
            )

    def test_native_support_state_fixtures_traverse_full_compiler_pipeline(self):
        fixture_root = Path(__file__).parent / "fixtures" / "native_support_states"
        cases = (
            ("native-known", NativeSupportState.UNSUPPORTED, "NATIVE-SUPPORT-006"),
            ("native-typed", NativeSupportState.UNSUPPORTED, "NATIVE-SUPPORT-006"),
            ("semantically-adapted", NativeSupportState.UNSUPPORTED, "NATIVE-SUPPORT-006"),
            ("executable-safe", NativeSupportState.EXECUTABLE_SAFE, None),
            ("unsupported", NativeSupportState.UNSUPPORTED, "NATIVE-SUPPORT-006"),
        )

        for name, expected_state, expected_code in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp_dir:
                source = (fixture_root / f"{name}.perdsl").read_text(encoding="utf-8")
                registry = self._native_support_fixture_registry(name)
                output = Path(tmp_dir) / f"{name}.per"
                backend = FakeBackend(fake_result(output, ValidationStatus.VALIDATED))

                if name != "executable-safe":
                    output.write_text("KEEP UNSUPPORTED ARTIFACT\\n", encoding="utf-8")
                    before = output.read_text(encoding="utf-8")
                else:
                    before = None

                report = compile_source_with_report(
                    source,
                    output,
                    native_backend=backend,
                    registry=registry,
                    source_unit=f"native-support/{name}.perdsl",
                )

                expected_states = {
                    "native-known": [
                        NativeSupportState.NATIVE_KNOWN,
                        NativeSupportState.UNSUPPORTED,
                    ],
                    "native-typed": [
                        NativeSupportState.NATIVE_KNOWN,
                        NativeSupportState.NATIVE_TYPED,
                        NativeSupportState.UNSUPPORTED,
                    ],
                    "semantically-adapted": [
                        NativeSupportState.NATIVE_KNOWN,
                        NativeSupportState.NATIVE_TYPED,
                        NativeSupportState.SEMANTICALLY_ADAPTED,
                        NativeSupportState.UNSUPPORTED,
                    ],
                    "executable-safe": [
                        NativeSupportState.NATIVE_KNOWN,
                        NativeSupportState.NATIVE_TYPED,
                        NativeSupportState.SEMANTICALLY_ADAPTED,
                        NativeSupportState.ENGINE_SEMANTICS_MAPPED,
                        NativeSupportState.EXECUTABLE_SAFE,
                    ],
                    "unsupported": [
                        NativeSupportState.UNSUPPORTED,
                    ],
                }
                expected_codes = {
                    "native-known": ["NATIVE-SUPPORT-001", "NATIVE-SUPPORT-006"],
                    "native-typed": [
                        "NATIVE-SUPPORT-001",
                        "NATIVE-SUPPORT-002",
                        "NATIVE-SUPPORT-006",
                    ],
                    "semantically-adapted": [
                        "NATIVE-SUPPORT-001",
                        "NATIVE-SUPPORT-002",
                        "NATIVE-SUPPORT-003",
                        "NATIVE-SUPPORT-006",
                    ],
                    "executable-safe": [
                        "NATIVE-SUPPORT-001",
                        "NATIVE-SUPPORT-002",
                        "NATIVE-SUPPORT-003",
                        "NATIVE-SUPPORT-004",
                        "NATIVE-SUPPORT-005",
                    ],
                    "unsupported": ["NATIVE-SUPPORT-006"],
                }

                assessment = registry.assess_support("fixture-command")
                repeat_assessment = registry.assess_support("fixture-command")
                self.assertEqual(assessment.state, expected_state)
                self.assertEqual(
                    [diagnostic.state for diagnostic in assessment.diagnostics],
                    expected_states[name],
                )
                self.assertEqual(
                    [diagnostic.code for diagnostic in assessment.diagnostics],
                    expected_codes[name],
                )
                self.assertEqual(
                    [diagnostic.code for diagnostic in repeat_assessment.diagnostics],
                    expected_codes[name],
                )

                if name == "executable-safe":
                    self.assertEqual(report.status, ReportStatus.VALIDATED)
                    self.assertIsNotNone(backend.seen_artifact)
                    self.assertTrue(output.exists())
                else:
                    self.assertEqual(report.status, ReportStatus.SEMANTIC_REJECTED)
                    self.assertEqual(
                        [diagnostic.code for diagnostic in report.diagnostics],
                        ["NATIVE-SUPPORT-006"],
                    )
                    self.assertIsNone(backend.seen_artifact)
                    self.assertTrue(output.exists())
                    self.assertEqual(output.read_text(encoding="utf-8"), before)

                    expected_support_payload = [
                        {
                            "command": diagnostic.command,
                            "state": diagnostic.state.value,
                            "code": diagnostic.code,
                            "severity": diagnostic.severity,
                            "message": diagnostic.message,
                        }
                        for diagnostic in assessment.diagnostics
                    ]
                    baseline_payload = report.to_dict()["diagnostics"]
                    baseline_state_sequence = [
                        diagnostic.state.value for diagnostic in assessment.diagnostics
                    ]
                    baseline_artifact_hash = hashlib.sha256(
                        output.read_bytes()
                    ).hexdigest()

                    self.assertEqual(
                        [item["code"] for item in baseline_payload],
                        ["NATIVE-SUPPORT-006"],
                    )
                    self.assertEqual(
                        baseline_state_sequence,
                        [state.value for state in expected_states[name]],
                    )
                    self.assertEqual(
                        [item["code"] for item in expected_support_payload],
                        expected_codes[name],
                    )

                    cross_process_baseline = {
                        "diagnostics": baseline_payload,
                        "support_states": baseline_state_sequence,
                        "artifact_hash": baseline_artifact_hash,
                    }
                    for process_number in range(1, 3):
                        cross_process_payload = self._cross_process_replay(
                            name,
                            output,
                        )
                        self.assertEqual(
                            cross_process_payload,
                            cross_process_baseline,
                            msg=f"cross-process replay {process_number} diverged",
                        )

                    for run_number in range(2, 4):
                        replay_backend = FakeBackend(
                            fake_result(output, ValidationStatus.VALIDATED)
                        )
                        replay_report = compile_source_with_report(
                            source,
                            output,
                            native_backend=replay_backend,
                            registry=registry,
                            source_unit=f"native-support/{name}.perdsl",
                        )
                        replay_assessment = registry.assess_support("fixture-command")
                        replay_payload = replay_report.to_dict()["diagnostics"]
                        replay_state_sequence = [
                            diagnostic.state.value
                            for diagnostic in replay_assessment.diagnostics
                        ]
                        replay_artifact_hash = hashlib.sha256(
                            output.read_bytes()
                        ).hexdigest()

                        self.assertEqual(
                            replay_report.status,
                            ReportStatus.SEMANTIC_REJECTED,
                            msg=f"run {run_number}",
                        )
                        self.assertEqual(
                            replay_payload,
                            baseline_payload,
                            msg=f"diagnostic payload changed on run {run_number}",
                        )
                        self.assertEqual(
                            replay_state_sequence,
                            baseline_state_sequence,
                            msg=f"support-state sequence changed on run {run_number}",
                        )
                        self.assertEqual(
                            [
                                {
                                    "command": diagnostic.command,
                                    "state": diagnostic.state.value,
                                    "code": diagnostic.code,
                                    "severity": diagnostic.severity,
                                    "message": diagnostic.message,
                                }
                                for diagnostic in replay_assessment.diagnostics
                            ],
                            expected_support_payload,
                            msg=f"support diagnostic payload changed on run {run_number}",
                        )
                        self.assertEqual(
                            replay_artifact_hash,
                            baseline_artifact_hash,
                            msg=f"artifact hash changed on run {run_number}",
                        )
                        self.assertEqual(
                            output.read_text(encoding="utf-8"),
                            before,
                            msg=f"artifact content changed on run {run_number}",
                        )
                        self.assertIsNone(
                            replay_backend.seen_artifact,
                            msg=f"native backend invoked on run {run_number}",
                        )

    @staticmethod
    def _cross_process_replay(
        name,
        output,
    ):
        script = r"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
test_path = root / "Compiler" / "tests" / "test_compiler_native_integration.py"
fixture_name = sys.argv[2]
output = Path(sys.argv[3])

sys.path.insert(0, str(root))
spec = importlib.util.spec_from_file_location("native_support_integration", test_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

fixture_root = test_path.parent / "fixtures" / "native_support_states"
source = (fixture_root / f"{fixture_name}.perdsl").read_text(encoding="utf-8")
registry = module.CompilerNativeIntegrationTests._native_support_fixture_registry(fixture_name)
backend = module.FakeBackend(
    module.fake_result(output, module.ValidationStatus.VALIDATED)
)
report = module.compile_source_with_report(
    source,
    output,
    native_backend=backend,
    registry=registry,
    source_unit=f"native-support/{fixture_name}.perdsl",
)
assessment = registry.assess_support("fixture-command")
payload = {
    "diagnostics": report.to_dict()["diagnostics"],
    "support_states": [diagnostic.state.value for diagnostic in assessment.diagnostics],
    "artifact_hash": hashlib.sha256(output.read_bytes()).hexdigest(),
}
print(json.dumps(payload, sort_keys=True))
"""
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                script,
                str(ROOT),
                name,
                str(output),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(completed.stdout)

    @staticmethod
    def _native_support_fixture_registry(name):
        parameter = NativeParameterSpec(
            "Value",
            "Const",
            "in",
            "fixture",
            "fixture parameter",
        )
        base_registry = default_de_registry()
        base_primitives = tuple(
            base_registry.get(command)
            for command in base_registry.names()
        )
        base_native = load_default_native_schema()
        base_native_commands = tuple(
            base_native.get(command)
            for command in base_native.names()
        )

        if name == "native-known":
            native = NativeCommandSpec(
                "fixture-command",
                "DE",
                "Fact",
                (NativeParameterSpec("", "", "", "", ""),),
            )
            primitive = None
        elif name == "native-typed":
            native = NativeCommandSpec(
                "fixture-command",
                "DE",
                "Fact",
                (parameter,),
            )
            primitive = None
        elif name == "semantically-adapted":
            native = NativeCommandSpec(
                "fixture-command",
                "DE",
                "Fact",
                (parameter,),
            )
            primitive = Primitive("fixture-command", "FACT", "FEASIBILITY", 2, 2)
        elif name == "executable-safe":
            native = NativeCommandSpec(
                "fixture-command",
                "DE",
                "Fact",
                (parameter,),
            )
            primitive = Primitive("fixture-command", "FACT", "FEASIBILITY", 1, 1, engine_semantics_id="fixture.execution.safe")
        else:
            return base_registry

        primitives = base_primitives if primitive is None else base_primitives + (primitive,)
        native_registry = NativeCommandRegistry(
            base_native_commands + (native,),
            source_blob_sha=f"native-support-{name}",
            command_count=len(base_native_commands) + 1,
        )
        semantic_registry = default_engine_semantic_mapping_registry()
        if name == "executable-safe":
            semantic_registry = EngineSemanticMappingRegistry(
                semantic_registry.mappings
                + (
                    EngineSemanticMapping(
                        identity="fixture.execution.safe",
                        native_command="fixture-command",
                        native_kind="Fact",
                        status=EngineSemanticMappingStatus.CONTRACTED,
                        evidence_class="ENGINE FACT",
                        evidence_sources=("test://compiler-native-integration",),
                        state_effects="test fixture has no persistent state mutation",
                        lifetime="test fixture semantic mapping exists for this test only",
                        ordering="test fixture fact is read during rule evaluation",
                        admission="test fixture native fact is admissible",
                        completion="test fixture fact is the executable promotion boundary",
                        recovery="test fixture has no recovery semantics",
                    ),
                )
            )
        return PrimitiveRegistry(primitives, native_registry, semantic_registry)


if __name__ == "__main__":
    unittest.main()
