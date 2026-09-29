import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Compiler.backends.models import (
    ArtifactIdentity,
    BackendIdentity,
    InvocationResult,
    NativeValidationResult,
    ValidationStatus,
    ValidationSummary,
)
from Compiler.compiler import (
    compile_package,
    compile_package_with_report,
    compile_semantic_demands,
    compile_source,
    compile_source_with_report,
    compile_to_file,
)
from Compiler.diagnostics import ReportStatus
from Compiler.source_graph import SourceGraphRequest


SOURCE = """
demand marker {
    require (can-train spearman)
    action (train spearman)
    witness (unit-type-count spearman >= 1)
    release (unit-type-count spearman >= 1)
}
"""

MINIMAL_ARTIFACT = """(defrule
    (true)
=>
    (disable-self)
)
"""


def _validated_result(output: Path) -> NativeValidationResult:
    backend = BackendIdentity(
        "aoe2-ai-parser",
        "0.1.0",
        "3dfa2583b7c2ec36b85ccb421ebd0abe9ff276ba",
        "3.12.7",
    )
    artifact = ArtifactIdentity(output.resolve(), "0" * 64)
    return NativeValidationResult(
        status=ValidationStatus.VALIDATED,
        failed=False,
        backend=backend,
        invocation=InvocationResult("default", output.resolve(), 0, 1),
        artifact=artifact,
        summary=ValidationSummary(0, 0, 0, 0, 0),
        diagnostics=(),
        stderr="",
    )


class _ValidatedBackend:
    def __init__(self) -> None:
        self.seen_artifact: Path | None = None

    def validate(self, artifact: Path) -> NativeValidationResult:
        self.seen_artifact = artifact
        return _validated_result(artifact)


class NativeEscrowPlanCompilerThreadingTests(unittest.TestCase):
    """Ensure every public compiler surface forwards escrow_plan exactly once."""

    @staticmethod
    def _cases(tmp: Path):
        package_root = tmp / "root.perdsl"
        package_child = tmp / "child.perdsl"
        package_root.write_text('(load "child.perdsl")\n', encoding="utf-8")
        package_child.write_text(SOURCE, encoding="utf-8")

        source_output = tmp / "source.per"
        package_output = tmp / "package.per"
        file_output = tmp / "file.per"

        return (
            (
                "compile_source",
                lambda plan: compile_source(
                    SOURCE,
                    escrow_plan=plan,
                ),
                None,
            ),
            (
                "compile_package",
                lambda plan: compile_package(
                    SourceGraphRequest(entrypoint=package_root),
                    escrow_plan=plan,
                ),
                None,
            ),
            (
                "compile_semantic_demands",
                lambda plan: compile_semantic_demands(
                    (),
                    escrow_plan=plan,
                ),
                None,
            ),
            (
                "compile_source_with_report",
                lambda plan: compile_source_with_report(
                    SOURCE,
                    source_output,
                    native_backend=_ValidatedBackend(),
                    escrow_plan=plan,
                ),
                ReportStatus.VALIDATED,
            ),
            (
                "compile_package_with_report",
                lambda plan: compile_package_with_report(
                    SourceGraphRequest(entrypoint=package_root),
                    package_output,
                    native_backend=_ValidatedBackend(),
                    escrow_plan=plan,
                ),
                ReportStatus.VALIDATED,
            ),
            (
                "compile_to_file",
                lambda plan: compile_to_file(
                    SOURCE,
                    file_output,
                    native_backend=_ValidatedBackend(),
                    escrow_plan=plan,
                ),
                ValidationStatus.VALIDATED,
            ),
        )

    def test_every_public_compiler_path_accepts_policy_plan(self):
        owner = object()
        policy_plan = __import__(
            "Compiler.ir",
            fromlist=["EscrowOperation", "EscrowOperationKind", "NativeEscrowPolicyPlan", "SemanticId"],
        ).NativeEscrowPolicyPlan(
            (
                __import__(
                    "Compiler.ir",
                    fromlist=["EscrowOperation", "EscrowOperationKind", "SemanticId"],
                ).EscrowOperation(
                    contract_identity="policy-food",
                    owner=__import__(
                        "Compiler.ir",
                        fromlist=["SemanticId"],
                    ).SemanticId("test", "policy"),
                    kind=__import__(
                        "Compiler.ir",
                        fromlist=["EscrowOperationKind"],
                    ).EscrowOperationKind.POLICY_RESET,
                    resource="food",
                    command="set-escrow-percentage",
                    percentage=50,
                    rule_order=10,
                ),
            )
        )

        with (
            patch(
                "Compiler.compiler.emit",
                return_value=MINIMAL_ARTIFACT,
            ) as emitted,
            tempfile.TemporaryDirectory() as tmp_dir,
        ):
            tmp = Path(tmp_dir)
            for name, invoke, expected_status in self._cases(tmp):
                with self.subTest(path=name):
                    if name == "compile_semantic_demands":
                        # Empty semantic demands still exercise the public escrow forwarding path.
                        pass
                    result = invoke(policy_plan)
                    self.assertEqual(
                        emitted.call_args.kwargs["escrow_plan"],
                        policy_plan,
                    )
                    if expected_status is not None:
                        status = result.status if hasattr(result, "status") else result
                        self.assertEqual(status, expected_status)
                    emitted.reset_mock()

    def test_every_public_compiler_path_forwards_same_escrow_plan_once(self):
        def capture_emit(*_args, **kwargs):
            self.assertIn("escrow_plan", kwargs)
            return MINIMAL_ARTIFACT

        with (
            patch(
                "Compiler.compiler.NativeEscrowReleasePlan",
                object,
                create=True,
            ),
            patch(
                "Compiler.compiler.emit",
                side_effect=capture_emit,
            ) as emitted,
            tempfile.TemporaryDirectory() as tmp_dir,
        ):
            tmp = Path(tmp_dir)
            for name, invoke, expected_status in self._cases(tmp):
                with self.subTest(path=name):
                    plan = object()
                    try:
                        result = invoke(plan)
                    except TypeError as exc:
                        self.fail(
                            f"{name} rejected escrow_plan before reaching emit(): {exc}"
                        )

                    self.assertEqual(
                        emitted.call_count,
                        1,
                        msg=f"{name} must call emit() exactly once",
                    )
                    self.assertIs(
                        emitted.call_args.kwargs["escrow_plan"],
                        plan,
                        msg=f"{name} changed or duplicated escrow_plan",
                    )

                    if expected_status is not None:
                        status = (
                            result.status
                            if hasattr(result, "status")
                            else result
                        )
                        self.assertEqual(
                            status,
                            expected_status,
                            msg=f"{name} did not complete through its public path",
                        )

                    emitted.reset_mock()


if __name__ == "__main__":
    unittest.main()
