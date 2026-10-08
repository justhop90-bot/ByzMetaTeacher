"""Semantic verification for the Byzantine compiler -> runtime -> promotion lineage."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

COMPILER_ARTIFACT = Path("dist/byzantine/Byzantine.compiler.per")
COMPILER_MANIFEST = Path("dist/byzantine/Byzantine.compiler.manifest.json")
OVERLAY_ARTIFACT = Path("runtime/byzantine/Byzantine.runtime-overlay.per")
OVERLAY_MANIFEST = Path("runtime/byzantine/Byzantine.runtime-overlay.json")
RUNTIME_ARTIFACT = Path("dist/byzantine/Byzantine.runtime.per")
RUNTIME_MANIFEST = Path("dist/byzantine/Byzantine.runtime.manifest.json")
PROMOTED_ARTIFACT = Path("Byzantine.per")
PROMOTION_MANIFEST = Path("Byzantine.manifest.json")


class ArtifactLineageError(RuntimeError):
    """Raised at the first broken artifact-lineage edge."""

    def __init__(
        self,
        *,
        code: str,
        edge: str,
        expected: str,
        observed: str,
        source_path: Path | None = None,
        target_path: Path | None = None,
    ) -> None:
        self.code = code
        self.edge = edge
        self.expected = expected
        self.observed = observed
        self.source_path = source_path
        self.target_path = target_path
        location = ""
        if source_path is not None or target_path is not None:
            location = (
                f" source={source_path!s}" if source_path is not None else ""
            )
            location += (
                f" target={target_path!s}" if target_path is not None else ""
            )
        super().__init__(
            f"{code}: {edge}; expected={expected!r}; observed={observed!r}{location}"
        )


@dataclass(frozen=True)
class ArtifactLineageResult:
    """Verified compiler -> runtime -> promotion lineage."""

    compiler_verified: bool
    runtime_verified: bool
    promotion_verified: bool
    root_matches_runtime: bool
    compiler_sha256: str
    runtime_sha256: str
    promoted_sha256: str
    compiler_source_revision: str


def defrule_blocks(payload: bytes) -> tuple[str, ...]:
    """Extract complete defrule bodies in source order."""
    text = payload.decode("utf-8", errors="replace")
    blocks: list[str] = []
    cursor = 0
    while True:
        start = text.find("(defrule", cursor)
        if start < 0:
            return tuple(blocks)
        depth = 0
        end = None
        for index in range(start, len(text)):
            char = text[index]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is None:
            raise ArtifactLineageError(
                code="BYZ-LINEAGE-030",
                edge="runtime-artifact -> defrule-analysis",
                expected="balanced defrule body",
                observed="unterminated defrule",
            )
        blocks.append(text[start:end])
        cursor = end


@dataclass(frozen=True)
class WovenRuntimeLineageResult:
    """Compiler-owned rules conserved inside the woven runtime artifact."""

    compiler_sha256: str
    runtime_sha256: str
    compiler_source_revision: str
    compiler_rule_count: int
    runtime_rule_count: int
    compiler_rules_conserved: bool


def verify_woven_runtime_lineage(
    *,
    repository_root: Path,
    compiler_manifest_path: Path = COMPILER_MANIFEST,
    runtime_artifact_path: Path = PROMOTED_ARTIFACT,
) -> WovenRuntimeLineageResult:
    """Verify compiler rule conservation without asserting compiler ordering."""
    root = repository_root.resolve()
    compiler_sha, source_revision = verify_compiler_manifest_semantics(
        repository_root=root,
        manifest_path=compiler_manifest_path,
    )
    runtime_path = _expect_file(
        root=root,
        relative_path=runtime_artifact_path,
        code="BYZ-LINEAGE-031",
        edge="compiler -> woven-runtime",
    )
    runtime_bytes = runtime_path.read_bytes()
    compiler_bytes = (root / COMPILER_ARTIFACT).read_bytes()
    compiler_rules = defrule_blocks(compiler_bytes)
    runtime_rules = defrule_blocks(runtime_bytes)

    compiler_counts: dict[str, int] = {}
    runtime_counts: dict[str, int] = {}
    for rule in compiler_rules:
        compiler_counts[rule] = compiler_counts.get(rule, 0) + 1
    for rule in runtime_rules:
        runtime_counts[rule] = runtime_counts.get(rule, 0) + 1

    missing = [
        (rule, count, runtime_counts.get(rule, 0))
        for rule, count in compiler_counts.items()
        if runtime_counts.get(rule, 0) < count
    ]
    if missing:
        rule, expected_count, observed_count = missing[0]
        raise ArtifactLineageError(
            code="BYZ-LINEAGE-032",
            edge="compiler-owned-rules -> woven-runtime",
            expected=f"{expected_count} occurrence(s) of exact compiler rule",
            observed=f"{observed_count} occurrence(s); rule_head={rule[:160]!r}",
            source_path=root / COMPILER_ARTIFACT,
            target_path=runtime_path,
        )

    return WovenRuntimeLineageResult(
        compiler_sha256=compiler_sha,
        runtime_sha256=sha256_bytes(runtime_bytes),
        compiler_source_revision=source_revision,
        compiler_rule_count=len(compiler_rules),
        runtime_rule_count=len(runtime_rules),
        compiler_rules_conserved=True,
    )


def sha256_bytes(payload: bytes) -> str:
    """Return the SHA-256 digest for exact bytes."""
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for the exact bytes in a file."""
    return sha256_bytes(path.read_bytes())


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactLineageError(
            code="BYZ-LINEAGE-000",
            edge="manifest -> manifest-json",
            expected="valid UTF-8 JSON object",
            observed=f"{type(exc).__name__}: {exc}",
            source_path=path,
        ) from exc
    if not isinstance(value, dict):
        raise ArtifactLineageError(
            code="BYZ-LINEAGE-000",
            edge="manifest -> manifest-json",
            expected="JSON object",
            observed=type(value).__name__,
            source_path=path,
        )
    return value


def _missing(mapping: Mapping[str, Any], path: str) -> ArtifactLineageError:
    return ArtifactLineageError(
        code="BYZ-LINEAGE-000",
        edge="manifest -> required-field",
        expected=f"field {path!r}",
        observed="missing",
    )


def _get(mapping: Mapping[str, Any], key: str, *, context: str) -> Any:
    try:
        return mapping[key]
    except KeyError as exc:
        raise _missing(mapping, f"{context}.{key}") from exc


def _expect_equal(
    *,
    code: str,
    edge: str,
    expected: Any,
    observed: Any,
    source_path: Path | None = None,
    target_path: Path | None = None,
) -> None:
    if expected != observed:
        raise ArtifactLineageError(
            code=code,
            edge=edge,
            expected=str(expected),
            observed=str(observed),
            source_path=source_path,
            target_path=target_path,
        )


def _expect_file(
    *,
    root: Path,
    relative_path: Path,
    code: str,
    edge: str,
) -> Path:
    if relative_path.is_absolute():
        raise ArtifactLineageError(
            code=code,
            edge=edge,
            expected=f"relative canonical path {relative_path.as_posix()!r}",
            observed="absolute path",
            target_path=relative_path,
        )
    path = root / relative_path
    if not path.is_file():
        raise ArtifactLineageError(
            code=code,
            edge=edge,
            expected=f"existing file {relative_path.as_posix()!r}",
            observed="missing file",
            target_path=path,
        )
    return path


def _expect_hex(value: str, length: int, *, code: str, edge: str) -> None:
    if len(value) != length or any(char not in "0123456789abcdef" for char in value):
        raise ArtifactLineageError(
            code=code,
            edge=edge,
            expected=f"{length}-character lowercase hexadecimal digest",
            observed=value,
        )


def _artifact_hash(
    *,
    root: Path,
    relative_path: Path,
    declared_sha256: str,
    code: str,
    edge: str,
) -> str:
    _expect_hex(declared_sha256, 64, code=code, edge=edge)
    path = _expect_file(root=root, relative_path=relative_path, code=code, edge=edge)
    observed = sha256_file(path)
    _expect_equal(
        code=code,
        edge=edge,
        expected=declared_sha256,
        observed=observed,
        target_path=path,
    )
    return observed


def _check_canonical_artifact_reference(
    *,
    manifest: Mapping[str, Any],
    expected_artifact_path: Path,
    expected_manifest_path: Path,
    context: str,
    artifact_path_code: str,
    manifest_path_code: str,
) -> None:
    artifact = _get(manifest, "artifact", context=context)
    if not isinstance(artifact, dict):
        raise ArtifactLineageError(
            code="BYZ-LINEAGE-000",
            edge=f"{context} -> artifact",
            expected="object",
            observed=type(artifact).__name__,
        )
    _expect_equal(
        code=artifact_path_code,
        edge=f"{context}.artifact -> canonical-artifact-path",
        expected=expected_artifact_path.as_posix(),
        observed=_get(artifact, "path", context=f"{context}.artifact"),
    )
    _expect_equal(
        code=manifest_path_code,
        edge=f"{context}.artifact -> canonical-manifest-path",
        expected=expected_manifest_path.as_posix(),
        observed=_get(artifact, "manifest_path", context=f"{context}.artifact"),
    )


def verify_compiler_manifest_semantics(
    *,
    repository_root: Path,
    manifest_path: Path = COMPILER_MANIFEST,
) -> tuple[str, str]:
    """Verify the compiler manifest, returning (artifact_sha256, source_revision)."""
    root = repository_root.resolve()
    manifest_file = _expect_file(
        root=root,
        relative_path=manifest_path,
        code="BYZ-LINEAGE-002",
        edge="compiler -> compiler-manifest",
    )
    manifest = _read_json(manifest_file)

    _expect_equal(
        code="BYZ-LINEAGE-000",
        edge="compiler-manifest -> schema",
        expected="byzantine-compiler-artifact-1",
        observed=_get(manifest, "schema", context="compiler"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-000",
        edge="compiler-manifest -> artifact-kind",
        expected="compiler",
        observed=_get(manifest, "artifact_kind", context="compiler"),
    )
    _check_canonical_artifact_reference(
        manifest=manifest,
        expected_artifact_path=COMPILER_ARTIFACT,
        expected_manifest_path=COMPILER_MANIFEST,
        context="compiler",
        artifact_path_code="BYZ-LINEAGE-001",
        manifest_path_code="BYZ-LINEAGE-002",
    )

    artifact = _get(manifest, "artifact", context="compiler")
    sha = str(_get(artifact, "sha256", context="compiler.artifact"))
    actual_sha = _artifact_hash(
        root=root,
        relative_path=COMPILER_ARTIFACT,
        declared_sha256=sha,
        code="BYZ-LINEAGE-003",
        edge="compiler-manifest -> compiler-artifact",
    )

    compiler = _get(manifest, "compiler", context="compiler")
    source_revision = str(_get(compiler, "source_revision", context="compiler.compiler"))
    _expect_hex(
        source_revision,
        40,
        code="BYZ-LINEAGE-004",
        edge="compiler -> source-revision",
    )
    _expect_equal(
        code="BYZ-LINEAGE-000",
        edge="compiler -> entrypoint",
        expected="compile_strategy_profile",
        observed=_get(compiler, "entrypoint", context="compiler.compiler"),
    )

    strategy = _get(manifest, "strategy", context="compiler")
    _expect_equal(
        code="BYZ-LINEAGE-000",
        edge="compiler -> profile-entrypoint",
        expected="ByzantineProfile.for_update_185872",
        observed=_get(strategy, "profile_entrypoint", context="compiler.strategy"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-000",
        edge="compiler -> strategy-entrypoint",
        expected="build_byzantine_strategy",
        observed=_get(strategy, "strategy_entrypoint", context="compiler.strategy"),
    )

    return actual_sha, source_revision


def verify_overlay_manifest_semantics(
    *,
    repository_root: Path,
    manifest_path: Path = OVERLAY_MANIFEST,
) -> str:
    """Verify the declared runtime overlay and return its artifact SHA."""
    root = repository_root.resolve()
    manifest_file = _expect_file(
        root=root,
        relative_path=manifest_path,
        code="BYZ-LINEAGE-011",
        edge="overlay -> overlay-manifest",
    )
    manifest = _read_json(manifest_file)
    _expect_equal(
        code="BYZ-LINEAGE-000",
        edge="overlay-manifest -> schema",
        expected="byzantine-runtime-overlay-1",
        observed=_get(manifest, "schema", context="overlay"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-000",
        edge="overlay-manifest -> artifact-kind",
        expected="runtime-overlay",
        observed=_get(manifest, "artifact_kind", context="overlay"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-011",
        edge="overlay -> id",
        expected="byzantine-runtime-overlay",
        observed=_get(manifest, "id", context="overlay"),
    )
    _check_canonical_artifact_reference(
        manifest=manifest,
        expected_artifact_path=OVERLAY_ARTIFACT,
        expected_manifest_path=OVERLAY_MANIFEST,
        context="overlay",
        artifact_path_code="BYZ-LINEAGE-011",
        manifest_path_code="BYZ-LINEAGE-011",
    )
    artifact = _get(manifest, "artifact", context="overlay")
    return _artifact_hash(
        root=root,
        relative_path=OVERLAY_ARTIFACT,
        declared_sha256=str(_get(artifact, "sha256", context="overlay.artifact")),
        code="BYZ-LINEAGE-011",
        edge="overlay-manifest -> overlay-artifact",
    )


def verify_runtime_manifest_semantics(
    *,
    repository_root: Path,
    compiler_manifest: Mapping[str, Any],
    overlay_manifest: Mapping[str, Any],
    manifest_path: Path = RUNTIME_MANIFEST,
) -> str:
    """Verify runtime inputs/output and return the runtime artifact SHA."""
    root = repository_root.resolve()
    runtime_manifest_file = _expect_file(
        root=root,
        relative_path=manifest_path,
        code="BYZ-LINEAGE-012",
        edge="runtime -> runtime-manifest",
    )
    manifest = _read_json(runtime_manifest_file)

    _expect_equal(
        code="BYZ-LINEAGE-000",
        edge="runtime-manifest -> schema",
        expected="byzantine-runtime-artifact-1",
        observed=_get(manifest, "schema", context="runtime"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-000",
        edge="runtime-manifest -> artifact-kind",
        expected="runtime",
        observed=_get(manifest, "artifact_kind", context="runtime"),
    )
    _check_canonical_artifact_reference(
        manifest=manifest,
        expected_artifact_path=RUNTIME_ARTIFACT,
        expected_manifest_path=RUNTIME_MANIFEST,
        context="runtime",
        artifact_path_code="BYZ-LINEAGE-012",
        manifest_path_code="BYZ-LINEAGE-012",
    )

    inputs = _get(manifest, "inputs", context="runtime")
    compiler_ref = _get(inputs, "compiler", context="runtime.inputs")
    _expect_equal(
        code="BYZ-LINEAGE-010",
        edge="compiler-manifest -> runtime.inputs.compiler",
        expected="compiler",
        observed=_get(compiler_ref, "artifact_kind", context="runtime.inputs.compiler"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-010",
        edge="compiler-manifest -> runtime.inputs.compiler.path",
        expected=COMPILER_ARTIFACT.as_posix(),
        observed=_get(compiler_ref, "path", context="runtime.inputs.compiler"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-010",
        edge="compiler-manifest -> runtime.inputs.compiler.manifest_path",
        expected=COMPILER_MANIFEST.as_posix(),
        observed=_get(compiler_ref, "manifest_path", context="runtime.inputs.compiler"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-010",
        edge="compiler-manifest -> runtime.inputs.compiler.sha256",
        expected=compiler_manifest["artifact"]["sha256"],
        observed=_get(compiler_ref, "sha256", context="runtime.inputs.compiler"),
    )

    compiler_manifest_path = root / COMPILER_MANIFEST
    compiler_manifest_sha = sha256_file(compiler_manifest_path)
    _expect_equal(
        code="BYZ-LINEAGE-010",
        edge="compiler-manifest -> runtime.inputs.compiler.manifest_sha256",
        expected=compiler_manifest_sha,
        observed=_get(compiler_ref, "manifest_sha256", context="runtime.inputs.compiler"),
    )

    overlay_ref = _get(inputs, "overlay", context="runtime.inputs")
    _expect_equal(
        code="BYZ-LINEAGE-011",
        edge="overlay-manifest -> runtime.inputs.overlay.artifact_kind",
        expected="runtime-overlay",
        observed=_get(overlay_ref, "artifact_kind", context="runtime.inputs.overlay"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-011",
        edge="overlay-manifest -> runtime.inputs.overlay.id",
        expected="byzantine-runtime-overlay",
        observed=_get(overlay_ref, "id", context="runtime.inputs.overlay"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-011",
        edge="overlay-manifest -> runtime.inputs.overlay.path",
        expected=OVERLAY_ARTIFACT.as_posix(),
        observed=_get(overlay_ref, "path", context="runtime.inputs.overlay"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-011",
        edge="overlay-manifest -> runtime.inputs.overlay.manifest_path",
        expected=OVERLAY_MANIFEST.as_posix(),
        observed=_get(overlay_ref, "manifest_path", context="runtime.inputs.overlay"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-011",
        edge="overlay-manifest -> runtime.inputs.overlay.sha256",
        expected=overlay_manifest["artifact"]["sha256"],
        observed=_get(overlay_ref, "sha256", context="runtime.inputs.overlay"),
    )

    overlay_manifest_path = root / OVERLAY_MANIFEST
    overlay_manifest_sha = sha256_file(overlay_manifest_path)
    _expect_equal(
        code="BYZ-LINEAGE-011",
        edge="overlay-manifest -> runtime.inputs.overlay.manifest_sha256",
        expected=overlay_manifest_sha,
        observed=_get(overlay_ref, "manifest_sha256", context="runtime.inputs.overlay"),
    )

    assembly = _get(manifest, "assembly", context="runtime")
    _expect_equal(
        code="BYZ-LINEAGE-000",
        edge="runtime -> assembly.order",
        expected=["compiler", "runtime-overlay"],
        observed=_get(assembly, "order", context="runtime.assembly"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-000",
        edge="runtime -> assembly.conflict_mode",
        expected="reject",
        observed=_get(assembly, "conflict_mode", context="runtime.assembly"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-000",
        edge="runtime -> assembly.deterministic",
        expected=True,
        observed=_get(assembly, "deterministic", context="runtime.assembly"),
    )

    runtime_artifact = _get(manifest, "artifact", context="runtime")
    runtime_sha = str(_get(runtime_artifact, "sha256", context="runtime.artifact"))
    actual_runtime_sha = _artifact_hash(
        root=root,
        relative_path=RUNTIME_ARTIFACT,
        declared_sha256=runtime_sha,
        code="BYZ-LINEAGE-013",
        edge="runtime-manifest -> runtime-artifact",
    )
    _expect_equal(
        code="BYZ-LINEAGE-016",
        edge="compiler-source-revision -> runtime-source-revision",
        expected=compiler_manifest["compiler"]["source_revision"],
        observed=_get(manifest, "compiler_source_revision", context="runtime"),
    )

    return actual_runtime_sha


def verify_promotion_manifest_semantics(
    *,
    repository_root: Path,
    runtime_manifest: Mapping[str, Any],
    manifest_path: Path = PROMOTION_MANIFEST,
) -> tuple[str, str]:
    """Verify promotion and return (promoted SHA, compiler source revision)."""
    root = repository_root.resolve()
    promotion_manifest_file = _expect_file(
        root=root,
        relative_path=manifest_path,
        code="BYZ-LINEAGE-021",
        edge="promotion -> promotion-manifest",
    )
    manifest = _read_json(promotion_manifest_file)

    _expect_equal(
        code="BYZ-LINEAGE-000",
        edge="promotion-manifest -> schema",
        expected="byzantine-promoted-runtime-1",
        observed=_get(manifest, "schema", context="promotion"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-000",
        edge="promotion-manifest -> artifact-kind",
        expected="promoted-runtime",
        observed=_get(manifest, "artifact_kind", context="promotion"),
    )

    source = _get(manifest, "source_runtime", context="promotion")
    _expect_equal(
        code="BYZ-LINEAGE-020",
        edge="runtime-manifest -> promotion.source_runtime.artifact_kind",
        expected="runtime",
        observed=_get(source, "artifact_kind", context="promotion.source_runtime"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-020",
        edge="runtime-manifest -> promotion.source_runtime.path",
        expected=RUNTIME_ARTIFACT.as_posix(),
        observed=_get(source, "path", context="promotion.source_runtime"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-020",
        edge="runtime-manifest -> promotion.source_runtime.manifest_path",
        expected=RUNTIME_MANIFEST.as_posix(),
        observed=_get(source, "manifest_path", context="promotion.source_runtime"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-020",
        edge="runtime-manifest -> promotion.source_runtime.sha256",
        expected=runtime_manifest["artifact"]["sha256"],
        observed=_get(source, "sha256", context="promotion.source_runtime"),
    )

    runtime_manifest_path = root / RUNTIME_MANIFEST
    runtime_manifest_sha = sha256_file(runtime_manifest_path)
    _expect_equal(
        code="BYZ-LINEAGE-020",
        edge="runtime-manifest -> promotion.source_runtime.manifest_sha256",
        expected=runtime_manifest_sha,
        observed=_get(source, "manifest_sha256", context="promotion.source_runtime"),
    )

    promoted = _get(manifest, "promoted_artifact", context="promotion")
    _expect_equal(
        code="BYZ-LINEAGE-021",
        edge="promotion -> canonical-root-artifact",
        expected="promoted-runtime",
        observed=_get(promoted, "artifact_kind", context="promotion.promoted_artifact"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-021",
        edge="promotion -> Byzantine.per",
        expected=PROMOTED_ARTIFACT.as_posix(),
        observed=_get(promoted, "path", context="promotion.promoted_artifact"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-021",
        edge="promotion -> Byzantine.manifest.json",
        expected=PROMOTION_MANIFEST.as_posix(),
        observed=_get(promoted, "manifest_path", context="promotion.promoted_artifact"),
    )

    promoted_path = root / PROMOTED_ARTIFACT
    runtime_path = root / RUNTIME_ARTIFACT
    source_bytes = runtime_path.read_bytes()
    promoted_bytes = promoted_path.read_bytes()
    source_sha = sha256_bytes(source_bytes)
    promoted_actual_sha = sha256_bytes(promoted_bytes)
    if source_bytes != promoted_bytes:
        raise ArtifactLineageError(
            code="BYZ-PROMOTE-001",
            edge="runtime-artifact -> promoted-artifact",
            expected=source_sha,
            observed=promoted_actual_sha,
            source_path=runtime_path,
            target_path=promoted_path,
        )

    promoted_sha_declared = str(
        _get(promoted, "sha256", context="promotion.promoted_artifact")
    )
    promoted_sha = _artifact_hash(
        root=root,
        relative_path=PROMOTED_ARTIFACT,
        declared_sha256=promoted_sha_declared,
        code="BYZ-LINEAGE-022",
        edge="promotion-manifest -> promoted-artifact",
    )
    _expect_equal(
        code="BYZ-LINEAGE-023",
        edge="runtime-manifest -> promotion.source_runtime.sha256",
        expected=runtime_manifest["artifact"]["sha256"],
        observed=promoted_sha_declared,
    )

    promotion = _get(manifest, "promotion", context="promotion")
    _expect_equal(
        code="BYZ-LINEAGE-000",
        edge="promotion -> promotion.mode",
        expected="byte-copy",
        observed=_get(promotion, "mode", context="promotion.promotion"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-000",
        edge="promotion -> promotion.atomic",
        expected=True,
        observed=_get(promotion, "atomic", context="promotion.promotion"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-000",
        edge="promotion -> promotion.source_matches_destination",
        expected=True,
        observed=_get(
            promotion,
            "source_matches_destination",
            context="promotion.promotion",
        ),
    )

    compiler_source_revision = str(
        _get(manifest, "compiler_source_revision", context="promotion")
    )
    _expect_equal(
        code="BYZ-LINEAGE-024",
        edge="runtime-source-revision -> promotion-source-revision",
        expected=runtime_manifest["compiler_source_revision"],
        observed=compiler_source_revision,
    )

    return promoted_sha, compiler_source_revision


def verify_byzantine_artifact_lineage(
    *,
    repository_root: Path,
) -> ArtifactLineageResult:
    """Verify compiler -> runtime -> promotion lineage in first-broken-edge order."""
    root = repository_root.resolve()

    compiler_sha, compiler_source_revision = verify_compiler_manifest_semantics(
        repository_root=root,
    )

    overlay_manifest_file = _expect_file(
        root=root,
        relative_path=OVERLAY_MANIFEST,
        code="BYZ-LINEAGE-011",
        edge="runtime -> overlay-manifest",
    )
    overlay_manifest = _read_json(overlay_manifest_file)
    _expect_equal(
        code="BYZ-LINEAGE-000",
        edge="overlay-manifest -> schema",
        expected="byzantine-runtime-overlay-1",
        observed=_get(overlay_manifest, "schema", context="overlay"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-000",
        edge="overlay-manifest -> artifact-kind",
        expected="runtime-overlay",
        observed=_get(overlay_manifest, "artifact_kind", context="overlay"),
    )
    _expect_equal(
        code="BYZ-LINEAGE-011",
        edge="overlay -> id",
        expected="byzantine-runtime-overlay",
        observed=_get(overlay_manifest, "id", context="overlay"),
    )
    _check_canonical_artifact_reference(
        manifest=overlay_manifest,
        expected_artifact_path=OVERLAY_ARTIFACT,
        expected_manifest_path=OVERLAY_MANIFEST,
        context="overlay",
        artifact_path_code="BYZ-LINEAGE-011",
        manifest_path_code="BYZ-LINEAGE-011",
    )
    overlay_artifact = _get(overlay_manifest, "artifact", context="overlay")
    _artifact_hash(
        root=root,
        relative_path=OVERLAY_ARTIFACT,
        declared_sha256=str(_get(overlay_artifact, "sha256", context="overlay.artifact")),
        code="BYZ-LINEAGE-011",
        edge="overlay-manifest -> overlay-artifact",
    )

    compiler_manifest = _read_json(root / COMPILER_MANIFEST)
    runtime_sha = verify_runtime_manifest_semantics(
        repository_root=root,
        compiler_manifest=compiler_manifest,
        overlay_manifest=overlay_manifest,
    )

    runtime_manifest = _read_json(root / RUNTIME_MANIFEST)
    promoted_sha, promotion_source_revision = verify_promotion_manifest_semantics(
        repository_root=root,
        runtime_manifest=runtime_manifest,
    )

    _expect_equal(
        code="BYZ-LINEAGE-024",
        edge="compiler-source-revision -> promotion-source-revision",
        expected=compiler_source_revision,
        observed=promotion_source_revision,
    )

    return ArtifactLineageResult(
        compiler_verified=True,
        runtime_verified=True,
        promotion_verified=True,
        root_matches_runtime=True,
        compiler_sha256=compiler_sha,
        runtime_sha256=runtime_sha,
        promoted_sha256=promoted_sha,
        compiler_source_revision=compiler_source_revision,
    )
