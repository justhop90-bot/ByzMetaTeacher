"""Typed policy recipes and deterministic resolution for strategy-layer control."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

from .community_engine import EvidenceClass, PracticeStatus
from .policy_cause_graph import (
    PolicyCauseGraph,
    PolicyCauseRelation,
    PolicyDiagnostic,
    PolicyDiagnosticPhase,
    PolicyDiagnosticRef,
    PolicySuppressionRef,
    build_diagnostic,
    select_root_cause,
    validate_policy_cause_graph,
)
from ..diagnostics import DiagnosticSeverity


class PolicyField(str, Enum):
    STANCE = "stance"
    RELATIONSHIP = "relationship"
    ATTACK_RETARGET = "attack-retarget"
    OBJECTIVE_DISCIPLINE = "objective-discipline"


class PolicyStrength(str, Enum):
    DEFAULT = "default"
    CONSTRAINT = "constraint"


class PolicyOverrideKind(str, Enum):
    AUTHOR = "author"


@dataclass(frozen=True)
class PolicyBindingRequirement:
    identity: str
    expected_value: str | None = None


@dataclass(frozen=True)
class PolicyTerm:
    field: PolicyField
    value: str
    strength: PolicyStrength
    evidence: EvidenceClass
    practice_status: PracticeStatus = PracticeStatus.CONTRACTED
    source_refs: tuple[str, ...] = ()
    label: str = ""

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("policy term value must not be empty")
        if not self.source_refs:
            raise ValueError(
                f"policy term '{self.field.value}={self.value}' requires source references"
            )
        if not self.label:
            object.__setattr__(
                self,
                "label",
                f"{self.field.value}={self.value}",
            )


@dataclass(frozen=True)
class PolicyOverride:
    field: PolicyField
    value: str
    kind: PolicyOverrideKind = PolicyOverrideKind.AUTHOR

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("policy override value must not be empty")


@dataclass(frozen=True)
class PolicyRecipe:
    identity: str
    terms: tuple[PolicyTerm, ...]
    bindings: tuple[PolicyBindingRequirement, ...] = ()
    evidence: tuple[EvidenceClass, ...] = ()

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("policy recipe identity must not be empty")
        if not self.terms:
            raise ValueError(f"policy recipe '{self.identity}' requires terms")
        binding_ids = [item.identity for item in self.bindings]
        if len(binding_ids) != len(set(binding_ids)):
            raise ValueError(
                f"policy recipe '{self.identity}' has duplicate binding requirements"
            )


@dataclass(frozen=True)
class PolicyResolution:
    recipe_identity: str
    resolved_terms: tuple[PolicyTerm, ...]
    bindings: tuple[tuple[str, str], ...]
    diagnostics: tuple[PolicyDiagnostic, ...]
    suppressions: tuple[PolicySuppressionRef, ...]
    causal_graph: PolicyCauseGraph
    executable: bool
    overrides: tuple[PolicyOverride, ...] = ()

    def value_for(self, field: PolicyField) -> str | None:
        for term in self.resolved_terms:
            if term.field is field:
                return term.value
        return None


def _subject(recipe: PolicyRecipe, field: PolicyField | None) -> tuple[str, str, str | None]:
    return (
        recipe.identity,
        recipe.identity,
        field.value if field is not None else None,
    )


def _diag(
    *,
    code: str,
    recipe: PolicyRecipe,
    field: PolicyField | None,
    related_field: PolicyField | None = None,
    binding_identity: str | None = None,
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR,
    phase: PolicyDiagnosticPhase = PolicyDiagnosticPhase.RESOLUTION,
    priority: int | None = None,
    message: str,
) -> PolicyDiagnostic:
    return build_diagnostic(
        code=code,
        policy_identity=recipe.identity,
        recipe_identity=recipe.identity,
        field=field.value if field else None,
        related_field=related_field.value if related_field else None,
        binding_identity=binding_identity,
        severity=severity,
        phase=phase,
        priority=priority,
        message=message,
    )


def _validate_recipe_identity_terms(recipe: PolicyRecipe) -> tuple[PolicyDiagnostic, ...]:
    diagnostics: list[PolicyDiagnostic] = []
    by_field: dict[PolicyField, list[PolicyTerm]] = {}
    for term in recipe.terms:
        by_field.setdefault(term.field, []).append(term)
    for field, terms in sorted(by_field.items(), key=lambda item: item[0].value):
        values = {term.value for term in terms}
        if len(values) > 1:
            diagnostics.append(
                _diag(
                    code="POL-010",
                    recipe=recipe,
                    field=field,
                    severity=DiagnosticSeverity.ERROR,
                    message=(
                        f"policy field '{field.value}' is specified with incompatible "
                        f"values: {', '.join(sorted(values))}"
                    ),
                )
            )
    return tuple(diagnostics)


def _validate_bindings(
    recipe: PolicyRecipe,
    bindings: Mapping[str, str],
) -> tuple[PolicyDiagnostic, ...]:
    diagnostics: list[PolicyDiagnostic] = []
    for requirement in recipe.bindings:
        value = bindings.get(requirement.identity)
        if value is None or not str(value).strip():
            diagnostics.append(
                _diag(
                    code="POL-004",
                    recipe=recipe,
                    field=None,
                    binding_identity=requirement.identity,
                    phase=PolicyDiagnosticPhase.BINDING,
                    message=(
                        f"recipe '{recipe.identity}' requires binding "
                        f"'{requirement.identity}'"
                    ),
                )
            )
            continue
        if (
            requirement.expected_value is not None
            and str(value) != requirement.expected_value
        ):
            diagnostics.append(
                _diag(
                    code="POL-005",
                    recipe=recipe,
                    field=None,
                    phase=PolicyDiagnosticPhase.BINDING,
                    message=(
                        f"binding '{requirement.identity}' has value '{value}', "
                        f"expected '{requirement.expected_value}'"
                    ),
                )
            )
    return tuple(diagnostics)


def _build_resolved_terms(
    recipe: PolicyRecipe,
    overrides: Sequence[PolicyOverride],
) -> tuple[tuple[PolicyTerm, ...], tuple[PolicyDiagnostic, ...]]:
    diagnostics: list[PolicyDiagnostic] = []
    by_field: dict[PolicyField, PolicyTerm] = {}
    for term in recipe.terms:
        by_field.setdefault(term.field, term)

    for field, terms in (
        (field, tuple(term for term in recipe.terms if term.field is field))
        for field in PolicyField
    ):
        if not terms:
            continue
        values = {term.value for term in terms}
        if len(values) != 1:
            continue
        by_field[field] = terms[0]

    for override in overrides:
        base = by_field.get(override.field)
        if base is None:
            by_field[override.field] = PolicyTerm(
                field=override.field,
                value=override.value,
                strength=PolicyStrength.DEFAULT,
                evidence=EvidenceClass.COMPILER_POLICY,
                source_refs=("author-override",),
                label=f"author override {override.field.value}",
            )
            continue

        if override.value == base.value:
            diagnostics.append(
                _diag(
                    code="POL-011",
                    recipe=recipe,
                    field=override.field,
                    severity=DiagnosticSeverity.WARNING,
                    message=(
                        f"override '{override.field.value}={override.value}' "
                        "is identical to the recipe default"
                    ),
                )
            )
            continue

        if base.strength is PolicyStrength.CONSTRAINT:
            diagnostics.append(
                _diag(
                    code="POL-002",
                    recipe=recipe,
                    field=override.field,
                    phase=PolicyDiagnosticPhase.RESOLUTION,
                    message=(
                        f"override '{override.field.value}={override.value}' "
                        f"conflicts with constraint "
                        f"'{override.field.value}={base.value}'"
                    ),
                )
            )
            diagnostics.append(
                _diag(
                    code="POL-012",
                    recipe=recipe,
                    field=override.field,
                    severity=DiagnosticSeverity.WARNING,
                    message=(
                        f"recipe constraint '{override.field.value}={base.value}' "
                        "would otherwise be overridden by the author"
                    ),
                )
            )
            continue

        diagnostics.append(
            _diag(
                code="POL-012",
                recipe=recipe,
                field=override.field,
                severity=DiagnosticSeverity.WARNING,
                message=(
                    f"recipe '{recipe.identity}' default "
                    f"{override.field.value}={base.value} overridden by "
                    f"{override.field.value}={override.value}"
                ),
            )
        )
        by_field[override.field] = PolicyTerm(
            field=override.field,
            value=override.value,
            strength=PolicyStrength.DEFAULT,
            evidence=EvidenceClass.COMPILER_POLICY,
            source_refs=("author-override",),
            label=f"author override {override.field.value}",
        )

    return (
        tuple(by_field[field] for field in sorted(by_field, key=lambda item: item.value)),
        tuple(diagnostics),
    )


def _add_graph_edges(
    graph: PolicyCauseGraph,
    diagnostics: Sequence[PolicyDiagnostic],
) -> tuple[PolicyCauseGraph, tuple[PolicySuppressionRef, ...]]:
    current = graph
    suppressions: list[PolicySuppressionRef] = []

    by_code = {item.key.code: item for item in diagnostics}
    conflicts = by_code.get("POL-001")
    constraint_override = by_code.get("POL-002")
    default_override = by_code.get("POL-012")
    no_consumer = by_code.get("POL-006")

    if constraint_override is not None and default_override is not None:
        current = current.with_supersession(
            constraint_override.key,
            default_override.key,
        )
        root = select_root_cause(current, default_override.key)
        if root == constraint_override.key:
            edge = next(
                edge.key
                for edge in current.edges
                if edge.key.source == PolicyDiagnosticRef(constraint_override.key)
                and edge.key.target == PolicyDiagnosticRef(default_override.key)
            )
            suppressions.append(
                PolicySuppressionRef(
                    suppressed=PolicyDiagnosticRef(default_override.key),
                    root_cause=PolicyDiagnosticRef(constraint_override.key),
                    via_edge=edge,
                )
            )

    if no_consumer is not None and conflicts is not None:
        current = current.with_invalidation(
            conflicts.key,
            no_consumer.key,
        )
        root = select_root_cause(current, no_consumer.key)
        if root == conflicts.key:
            edge = next(
                edge.key
                for edge in current.edges
                if edge.key.source == PolicyDiagnosticRef(conflicts.key)
                and edge.key.target == PolicyDiagnosticRef(no_consumer.key)
            )
            suppressions.append(
                PolicySuppressionRef(
                    suppressed=PolicyDiagnosticRef(no_consumer.key),
                    root_cause=PolicyDiagnosticRef(conflicts.key),
                    via_edge=edge,
                )
            )

    for suppression in suppressions:
        current.validate_suppression(suppression)

    return current, tuple(suppressions)


def resolve_policy_recipe(
    recipe: PolicyRecipe,
    *,
    bindings: Mapping[str, str] | None = None,
    overrides: Sequence[PolicyOverride] = (),
) -> PolicyResolution:
    bindings = bindings or {}
    diagnostics: list[PolicyDiagnostic] = []
    diagnostics.extend(_validate_recipe_identity_terms(recipe))
    diagnostics.extend(_validate_bindings(recipe, bindings))

    resolved_terms, override_diagnostics = _build_resolved_terms(recipe, overrides)
    diagnostics.extend(override_diagnostics)

    objective = next(
        (term.value for term in resolved_terms if term.field is PolicyField.OBJECTIVE_DISCIPLINE),
        None,
    )
    retarget = next(
        (term.value for term in resolved_terms if term.field is PolicyField.ATTACK_RETARGET),
        None,
    )
    if objective == "strict" and retarget == "patrol-style":
        diagnostics.append(
            _diag(
                code="POL-001",
                recipe=recipe,
                field=PolicyField.OBJECTIVE_DISCIPLINE,
                related_field=PolicyField.ATTACK_RETARGET,
                message=(
                    "strict objective discipline forbids patrol-style retargeting"
                ),
            )
        )

    for term in resolved_terms:
        if term.evidence is EvidenceClass.OPEN_UNKNOWN or term.practice_status in {
            PracticeStatus.OPEN,
            PracticeStatus.EVIDENCE_ONLY,
        }:
            diagnostics.append(
                _diag(
                    code="POL-008",
                    recipe=recipe,
                    field=term.field,
                    phase=PolicyDiagnosticPhase.EVIDENCE,
                    message=(
                        f"policy term '{term.label}' is not executable because its "
                        f"evidence status is {term.practice_status.value}"
                    ),
                )
            )

    if (
        retarget == "patrol-style"
        and "attack_consumer" not in bindings
        and not any(item.key.code == "POL-001" for item in diagnostics)
    ):
        diagnostics.append(
            _diag(
                code="POL-006",
                recipe=recipe,
                field=PolicyField.ATTACK_RETARGET,
                severity=DiagnosticSeverity.WARNING,
                phase=PolicyDiagnosticPhase.APPLICABILITY,
                message=(
                    "attack retarget policy PATROL_STYLE has no attack-transit consumer"
                ),
            )
        )

    graph = PolicyCauseGraph.from_nodes(tuple(diagnostics))
    graph, suppressions = _add_graph_edges(graph, tuple(diagnostics))
    validate_policy_cause_graph(graph)

    suppressed_keys = {
        suppression.suppressed.key
        for suppression in suppressions
    }
    executable = not any(
        diagnostic.severity is DiagnosticSeverity.ERROR
        and diagnostic.key not in suppressed_keys
        for diagnostic in diagnostics
    )

    return PolicyResolution(
        recipe_identity=recipe.identity,
        resolved_terms=resolved_terms,
        bindings=tuple(sorted((str(key), str(value)) for key, value in bindings.items())),
        diagnostics=tuple(diagnostics),
        suppressions=suppressions,
        causal_graph=graph,
        executable=executable,
        overrides=tuple(overrides),
    )


def resolve_policy_recipes(
    recipes: Sequence[PolicyRecipe],
) -> tuple[PolicyResolution, ...]:
    identities = [recipe.identity for recipe in recipes]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate policy recipe identity")
    results = tuple(resolve_policy_recipe(recipe) for recipe in recipes)
    return tuple(sorted(results, key=lambda item: item.recipe_identity))


def _community_term(
    field: PolicyField,
    value: str,
    *,
    source_refs: tuple[str, ...],
) -> PolicyTerm:
    return PolicyTerm(
        field=field,
        value=value,
        strength=PolicyStrength.DEFAULT,
        evidence=EvidenceClass.COMMUNITY_PRACTICE,
        practice_status=PracticeStatus.CONTRACTED,
        source_refs=source_refs,
    )


def default_byzantine_policy_recipes() -> tuple[PolicyRecipe, ...]:
    airef = "https://airef.github.io/"
    patrol_sn = "https://airef.github.io/strategic-numbers/sn-details.html#sn-enable-patrol-attack"
    community_forum = "https://forums.ageofempires.com/t/three-ways-to-get-the-ai-to-attack/205476"

    return (
        PolicyRecipe(
            identity="RANGED_HOLD",
            terms=(
                _community_term(
                    PolicyField.STANCE,
                    "stand-ground",
                    source_refs=(airef,),
                ),
            ),
        ),
        PolicyRecipe(
            identity="MOBILE_LOCAL_DEFENSE",
            terms=(
                _community_term(
                    PolicyField.STANCE,
                    "defensive",
                    source_refs=(airef, community_forum),
                ),
                _community_term(
                    PolicyField.RELATIONSHIP,
                    "patrol",
                    source_refs=(airef, community_forum),
                ),
                _community_term(
                    PolicyField.ATTACK_RETARGET,
                    "patrol-style",
                    source_refs=(patrol_sn, airef),
                ),
            ),
            bindings=(
                PolicyBindingRequirement("route"),
            ),
        ),
        PolicyRecipe(
            identity="STRICT_RAID",
            terms=(
                _community_term(
                    PolicyField.STANCE,
                    "aggressive",
                    source_refs=(airef,),
                ),
                PolicyTerm(
                    field=PolicyField.OBJECTIVE_DISCIPLINE,
                    value="strict",
                    strength=PolicyStrength.CONSTRAINT,
                    evidence=EvidenceClass.COMPILER_POLICY,
                    source_refs=("byzantine-doctrine",),
                ),
                PolicyTerm(
                    field=PolicyField.ATTACK_RETARGET,
                    value="disabled",
                    strength=PolicyStrength.CONSTRAINT,
                    evidence=EvidenceClass.COMPILER_POLICY,
                    source_refs=(patrol_sn,),
                ),
            ),
        ),
        PolicyRecipe(
            identity="PROTECT_SIEGE",
            terms=(
                _community_term(
                    PolicyField.STANCE,
                    "defensive",
                    source_refs=(airef,),
                ),
                _community_term(
                    PolicyField.RELATIONSHIP,
                    "guard",
                    source_refs=(airef,),
                ),
            ),
            bindings=(
                PolicyBindingRequirement("target"),
                PolicyBindingRequirement("target_kind", "siege"),
            ),
        ),
        PolicyRecipe(
            identity="DEER_PUSH",
            terms=(
                _community_term(
                    PolicyField.RELATIONSHIP,
                    "follow",
                    source_refs=(airef,),
                ),
            ),
            bindings=(
                PolicyBindingRequirement("target"),
                PolicyBindingRequirement("target_kind", "deer"),
            ),
        ),
    )


__all__ = [
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
    "resolve_policy_recipes",
]
