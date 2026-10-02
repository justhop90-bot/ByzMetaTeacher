"""Validated native engine-semantic mappings for executable compiler primitives.

The mapping catalog is deliberately separate from EnginePractice evidence records.
A mapping is executable only when the compiler has a complete, contracted semantic
description for the native primitive. Evidence-only identities may exist in the
catalog but can never promote a primitive to executable-safe.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EngineSemanticMappingStatus(str, Enum):
    CONTRACTED = "contracted"
    EVIDENCE_ONLY = "evidence-only"
    OPEN = "open"


_ENGINE_EVIDENCE_CLASSES = frozenset(
    {"ENGINE FACT", "COMMUNITY PRACTICE", "COMPILER POLICY", "OPEN / UNKNOWN"}
)
@dataclass(frozen=True)
class EngineSemanticMapping:
    identity: str
    native_command: str | None
    native_kind: str | None
    status: EngineSemanticMappingStatus
    evidence_class: str
    evidence_sources: tuple[str, ...]
    state_effects: str
    lifetime: str
    ordering: str
    admission: str
    completion: str
    recovery: str
    practice_references: tuple[str, ...] = ()


@dataclass(frozen=True)
class EngineSemanticMappingRegistry:
    mappings: tuple[EngineSemanticMapping, ...]

    def __post_init__(self) -> None:
        identities = [item.identity for item in self.mappings]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate engine semantic mapping identity")
        for item in self.mappings:
            if not item.identity:
                raise ValueError("engine semantic mapping identity must not be empty")
            if item.evidence_class not in _ENGINE_EVIDENCE_CLASSES:
                raise ValueError(
                    f"engine semantic mapping '{item.identity}' has unsupported "
                    f"evidence class '{item.evidence_class}'"
                )
            if item.status is EngineSemanticMappingStatus.CONTRACTED and item.evidence_class == "OPEN / UNKNOWN":
                raise ValueError(
                    f"contracted engine semantic mapping '{item.identity}' "
                    "cannot use OPEN / UNKNOWN evidence"
                )
            if not item.evidence_sources:
                raise ValueError(f"engine semantic mapping '{item.identity}' lacks evidence")
            for source in item.evidence_sources:
                if not isinstance(source, str) or not source.startswith(
                    ("https://", "http://", "repo://", "test://")
                ):
                    raise ValueError(
                        f"engine semantic mapping '{item.identity}' has invalid evidence source"
                    )
            for field_name in (
                "state_effects",
                "lifetime",
                "ordering",
                "admission",
                "completion",
                "recovery",
            ):
                if not getattr(item, field_name):
                    raise ValueError(
                        f"engine semantic mapping '{item.identity}' lacks {field_name}"
                    )
            for reference in item.practice_references:
                if not reference:
                    raise ValueError(
                        f"engine semantic mapping '{item.identity}' has an empty practice reference"
                    )
            if item.status is EngineSemanticMappingStatus.CONTRACTED:
                if not item.native_command or not item.native_kind:
                    raise ValueError(
                        f"contracted engine semantic mapping '{item.identity}' "
                        "must identify a native command and kind"
                    )
            elif item.native_command is not None or item.native_kind is not None:
                raise ValueError(
                    f"non-executable engine semantic mapping '{item.identity}' "
                    "must not masquerade as a native primitive contract"
                )

    def get(self, identity: str) -> EngineSemanticMapping | None:
        for item in self.mappings:
            if item.identity == identity:
                return item
        return None

    def require(self, identity: str) -> EngineSemanticMapping:
        item = self.get(identity)
        if item is None:
            raise KeyError(identity)
        return item

    def for_command(self, command: str) -> EngineSemanticMapping | None:
        matches = [item for item in self.mappings if item.native_command == command]
        if len(matches) > 1:
            raise ValueError(
                f"multiple engine semantic mappings registered for native command '{command}'"
            )
        return matches[0] if matches else None

    def validate_practice_references(self, practice_identities: set[str]) -> None:
        referenced = {
            reference
            for item in self.mappings
            for reference in item.practice_references
        }
        missing = sorted(referenced - practice_identities)
        if missing:
            raise ValueError(
                "engine semantic mapping references unknown engine practices: "
                f"{missing}"
            )

    def validate_exact_executable_commands(self, commands: tuple[str, ...]) -> None:
        expected = tuple(sorted(commands))
        actual = tuple(
            sorted(
                item.native_command
                for item in self.mappings
                if item.status is EngineSemanticMappingStatus.CONTRACTED
            )
        )
        if expected != actual:
            missing = sorted(set(expected) - set(actual))
            extra = sorted(set(actual) - set(expected))
            raise ValueError(
                "executable engine semantic mapping inventory mismatch: "
                f"missing={missing}, extra={extra}"
            )

    def validate_primitive(
        self,
        *,
        command: str,
        native_kind: str,
        identity: str,
    ) -> tuple[bool, str]:
        mapping = self.get(identity)
        if mapping is None:
            return False, f"engine semantic mapping '{identity}' is not registered"
        if mapping.status is EngineSemanticMappingStatus.EVIDENCE_ONLY:
            return False, (
                f"engine semantic mapping '{identity}' is evidence-only and cannot "
                "promote a native primitive"
            )
        if mapping.status is EngineSemanticMappingStatus.OPEN:
            return False, (
                f"engine semantic mapping '{identity}' is open/unknown and cannot "
                "promote a native primitive"
            )
        if mapping.native_command != command:
            return False, (
                f"engine semantic mapping '{identity}' targets "
                f"'{mapping.native_command}', not '{command}'"
            )
        # A contracted mapping may cover a subset of the schema-declared
        # native kinds (e.g. an Action-only mapping under a Fact/Action
        # schema): promotion is valid wherever the mapping covers the kind.
        # Claiming a kind outside the schema remains rejected below.
        mapping_kinds = set(mapping.native_kind.split("/"))
        native_kinds = set(native_kind.split("/"))
        if not mapping_kinds <= native_kinds:
            return False, (
                f"engine semantic mapping '{identity}' covers native kind(s) "
                f"'{mapping.native_kind}' outside contracted schema kind(s) "
                f"'{native_kind}'"
            )
        return True, "engine semantic mapping is contracted and executable"


_AOERF = "https://airef.github.io/"
_AOERF_LIMITS = "https://airef.github.io/resources/articles/data-limits.html"
_AOERF_PER = "https://airef.github.io/resources/articles/intro-to-commands.html"
_AOE2AI = "https://github.com/lewisc64/aoe2ai"
_DUKE = "https://github.com/niektb/AI"
_DUC_COMMAND_SPECS = (
    ("up-can-search", "duc.search.availability"),
    ("up-get-search-state", "duc.search.state"),
    ("up-get-group-size", "duc.group.get-size"),
    ("up-get-cost-delta", "duc.output.cost-delta"),
    ("up-get-point", "duc.output.point"),
    ("up-get-object-data", "duc.output.object-data"),
    ("up-create-group", "duc.group.create"),
    ("up-reset-group", "duc.group.reset"),
    ("up-set-group", "duc.group.set"),
    ("up-group-size", "duc.group.size"),
    ("up-modify-group-flag", "duc.group.flag"),
    ("up-get-object-target-data", "duc.output.object-target-data"),
    ("up-find-local", "duc.search.local"),
    ("up-find-status-local", "duc.search.local-status"),
    ("up-find-remote", "duc.search.remote"),
    ("up-find-status-remote", "duc.search.remote-status"),
    ("up-find-resource", "duc.search.resource"),
    ("up-filter-distance", "duc.filter.distance"),
    ("up-filter-exclude", "duc.filter.exclude"),
    ("up-filter-garrison", "duc.filter.garrison"),
    ("up-filter-include", "duc.filter.include"),
    ("up-filter-range", "duc.filter.range"),
    ("up-filter-status", "duc.filter.status"),
    ("up-reset-filters", "duc.reset.filters"),
    ("up-reset-search", "duc.reset.search"),
    ("up-full-reset-search", "duc.reset.full-search"),
    ("up-clean-search", "duc.mutation.clean-search"),
    ("up-remove-objects", "duc.mutation.remove-objects"),
    ("up-add-object-by-id", "duc.mutation.add-object-by-id"),
    ("up-set-target-by-id", "duc.target.by-id"),
    ("up-set-target-object", "duc.target.object"),
    ("up-set-target-point", "duc.target.point"),
    ("up-target-objects", "duc.target.consume-objects"),
)


_NATIVE_OUTPUT_READER_SPECS = (
    ("up-get-fact", "output.reader.fact"),
)


_PERSISTENT_STATE_SPECS = (
    ("up-compare-sn", "state.compare.strategic-number"),
)


_OBSERVATION_SPECS = (
    ("current-age", "observation.age.current"),
    ("food-amount", "observation.resource.food"),
    ("wood-amount", "observation.resource.wood"),
    ("gold-amount", "observation.resource.gold"),
    ("stone-amount", "observation.resource.stone"),
    ("players-unit-type-count", "observation.threat.unit-count"),
    ("players-building-type-count", "observation.world.building-count"),
    ("game-time", "observation.timing.game-time"),
    ("dropsite-min-distance", "observation.placement.dropsite-distance"),
    ("unit-type-count", "observation.unit.count"),
    ("up-research-status", "observation.research.status"),
)

_ADMISSIBILITY_SPECS = (
    ("building-available", "admissibility.building.available"),
    ("research-available", "admissibility.research.available"),
    ("up-train-site-ready", "admissibility.train.site-ready"),
)

_ARBITRATION_SPECS = (
    ("can-afford-building", "arbitration.building.affordability"),
    ("can-afford-research", "arbitration.research.affordability"),
)

_FEASIBILITY_SPECS = (
    ("can-build", "execution.build.feasibility"),
    ("can-build-with-escrow", "execution.build.feasibility.escrow"),
    ("can-train", "execution.train.feasibility"),
    ("can-train-with-escrow", "execution.train.feasibility.escrow"),
    ("can-research", "execution.research.feasibility"),
    ("can-research-with-escrow", "execution.research.feasibility.escrow"),
)

_WITNESS_SPECS = (
    ("building-type-count", "witness.building.present"),
    ("building-type-count-total", "witness.building.present.total"),
    ("unit-type-count-total", "witness.unit.present.total"),
    ("research-completed", "witness.research.completed"),
)

_ACTION_SPECS = (
    ("build", "execution.build.request"),
    ("train", "execution.train.request"),
    ("research", "execution.research.request"),
)

_ESCROW_COMMAND_SPECS = (
    ("release-escrow", "escrow.execution.release"),
    ("set-escrow-percentage", "escrow.execution.set-percentage"),
)



def _practice_references(command: str) -> tuple[str, ...]:
    references = {
        "can-build": ("build.can-pending-witness",),
        "can-build-with-escrow": ("build.can-pending-witness", "resource-control.escrow"),
        "can-train": ("train.can-queue-witness",),
        "can-train-with-escrow": ("train.can-queue-witness", "resource-control.escrow"),
        "up-train-site-ready": ("train.provider-readiness",),
        "can-research": ("research.can-complete-witness",),
        "can-research-with-escrow": ("research.can-complete-witness", "resource-control.escrow"),
        "building-type-count-total": ("build.can-pending-witness",),
        "unit-type-count-total": ("train.can-queue-witness",),
        "research-completed": ("research.can-complete-witness",),
    }
    return references.get(command, ())


def _fact_mapping(command: str, identity: str, category: str) -> EngineSemanticMapping:
    if category == "OBSERVATION":
        state_effects = "reads native world state without persistent mutation"
        lifetime = "single fact evaluation; truth is re-evaluated on subsequent rule passes"
        ordering = "observation reflects native state at evaluation time; source order does not make it persistent"
        admission = "native fact evaluation"
        completion = "observation result is not an action-completion witness"
        recovery = "re-evaluate the fact; no retained compiler failure state"
        sources = (_AOERF, _AOERF_PER)
    elif category == "ADMISSIBILITY":
        state_effects = "reads native provider/research admissibility state without persistent mutation"
        lifetime = "single admissibility evaluation; availability may change between passes"
        ordering = "truth is determined from native state at evaluation time"
        admission = "native admissibility fact"
        completion = "admissibility is not completion evidence"
        recovery = "re-evaluate admissibility when the demand is reconsidered"
        sources = (_AOERF, _AOERF_LIMITS)
    elif category == "ARBITRATION":
        state_effects = "reads current resource-affordability state without owning strategic intent"
        lifetime = "transient feasibility observation"
        ordering = "truth is evaluated against current native resource state"
        admission = "native affordability/arbitration fact"
        completion = "affordability is not completion evidence"
        recovery = "re-evaluate when resources or competing claims change"
        sources = (_AOERF, _DUKE)
    elif category == "FEASIBILITY":
        state_effects = "reads native execution feasibility; does not issue the native action"
        lifetime = "transient admission predicate"
        ordering = "must be evaluated immediately before the associated action when used as an execution guard"
        admission = "native can-* execution admission"
        completion = "feasibility does not prove issuance or completion"
        recovery = "re-enter through the same native feasibility predicate after temporary blockage"
        sources = (_AOERF, _DUKE)
    elif category == "WITNESS":
        state_effects = "reads world-state evidence produced by native engine state"
        lifetime = "persistent world observation until the world state changes"
        ordering = "witness must be evaluated after the relevant world-state transition can exist"
        admission = "native observation/witness evaluation"
        completion = "proves the corresponding world-state condition, not merely a request"
        recovery = "reassess current world state; never infer completion from a timer or request"
        sources = (_AOERF, _DUKE)
    else:
        raise ValueError(category)
    return EngineSemanticMapping(
        identity=identity,
        native_command=command,
        native_kind="Fact",
        status=EngineSemanticMappingStatus.CONTRACTED,
        evidence_class="ENGINE FACT",
        evidence_sources=sources,
        state_effects=state_effects,
        lifetime=lifetime,
        ordering=ordering,
        admission=admission,
        completion=completion,
        recovery=recovery,
        practice_references=_practice_references(command),
    )


def _action_mapping(command: str, identity: str) -> EngineSemanticMapping:
    witness = {
        "build": "building-type-count",
        "train": "unit-type-count",
        "research": "research-completed",
    }[command]
    return EngineSemanticMapping(
        identity=identity,
        native_command=command,
        native_kind="Action",
        status=EngineSemanticMappingStatus.CONTRACTED,
        evidence_class="ENGINE FACT",
        evidence_sources=(_AOERF, _AOE2AI, _DUKE),
        state_effects="issues native engine work and may create asynchronous pending work",
        lifetime="request persists only as native engine state; completion occurs through later world observation",
        ordering="action executes in emitted order within its rule; later rules observe engine-persisted effects only after they exist",
        admission="native action command; caller must separately guard with can-* or equivalent admission semantics where required",
        completion=f"completion requires world-state witness '{witness}'",
        recovery="preserve strategic demand and reassess through native feasibility after temporary blockage or failure",
        practice_references=("actions.request-not-completion",),
    )


def _native_output_reader_mapping(command: str, identity: str) -> EngineSemanticMapping:
    return EngineSemanticMapping(
        identity=identity,
        native_command=command,
        native_kind="Fact/Action",
        status=EngineSemanticMappingStatus.CONTRACTED,
        evidence_class="ENGINE FACT",
        evidence_sources=(_AOERF, _AOERF_PER, _AOE2AI, _DUKE),
        state_effects=(
            "evaluates the documented native Fact/Action reader and writes the "
            "requested result into the caller-supplied GoalId"
        ),
        lifetime=(
            "one native output evaluation; the resulting Goal value persists until "
            "another Goal write changes it"
        ),
        ordering=(
            "the native read occurs at its emitted rule position; the compiler does "
            "not claim the returned numeric value is known at compile time"
        ),
        admission=(
            "native schema provides the documented Fact/Action command, exact arity, "
            "FactId/parameter inputs, and one output Goal"
        ),
        completion=(
            "the native output write is the contracted event; it is not a completion "
            "witness for any separate strategic demand"
        ),
        recovery=(
            "re-evaluate or reissue the native reader as needed; no synthetic cache "
            "or retry state is introduced"
        ),
        practice_references=(),
    )


def _persistent_state_mapping(command: str, identity: str) -> EngineSemanticMapping:
    return EngineSemanticMapping(
        identity=identity,
        native_command=command,
        native_kind="Fact",
        status=EngineSemanticMappingStatus.CONTRACTED,
        evidence_class="ENGINE FACT",
        evidence_sources=(_AOERF, _AOERF_PER),
        state_effects="reads persistent Strategic Number control state without mutating it",
        lifetime="persists as engine state until another native write changes the Strategic Number",
        ordering="guard evaluation observes the current stored Strategic Number before the rule action list executes",
        admission="native persistent-state comparison fact",
        completion="does not prove world-state completion and is not a completion witness",
        recovery="re-evaluate the comparison after the underlying Goal or Strategic Number state changes",
        practice_references=(),
    )

def _escrow_percentage_mapping() -> EngineSemanticMapping:
    return EngineSemanticMapping(
        identity="escrow.execution.set-percentage",
        native_command="set-escrow-percentage",
        native_kind="Action",
        status=EngineSemanticMappingStatus.CONTRACTED,
        evidence_class="ENGINE FACT",
        evidence_sources=(
            "https://airef.github.io/commands/commands-details.html#set-escrow-percentage",
            "https://airef.github.io/commands/commands-details.html#escrow-amount",
            _DUKE,
        ),
        state_effects=(
            "mutates the native escrow-routing percentage for one resource; "
            "the resulting percentage persists until another native policy mutation"
        ),
        lifetime=(
            "persistent native resource-control policy state; this slice does not "
            "claim automatic restoration, ownership transfer, or scheduler behavior"
        ),
        ordering=(
            "the policy mutation executes in emitted action order; this compiler "
            "contract does not claim same-pass visibility to a later ordinary action"
        ),
        admission=(
            "native set-escrow-percentage Action with exactly two constant inputs: "
            "Resource and Value, where Value is restricted to 0..100"
        ),
        completion=(
            "the native policy mutation itself is the contracted operation; no "
            "compiler-generated completion witness is synthesized"
        ),
        recovery=(
            "re-evaluate the owning explicit escrow policy; no starvation or "
            "emergency-release scheduler is emitted by this slice"
        ),
        practice_references=(),
    )


def _escrow_release_mapping() -> EngineSemanticMapping:
    return EngineSemanticMapping(
        identity="escrow.execution.release",
        native_command="release-escrow",
        native_kind="Action",
        status=EngineSemanticMappingStatus.CONTRACTED,
        evidence_class="ENGINE FACT",
        evidence_sources=(
            "https://airef.github.io/commands/commands-details.html#release-escrow",
            "https://github.com/JackkelDragon/AoE2DE_AIBuilder/blob/master/AI%20Libraries/builder%20upgrades.per",
            "https://gist.github.com/Andygmb/1e3a6d9d444b2dfa8c40",
            "repo://docs/reference/engine/commands/release-escrow.md",
        ),
        state_effects=(
            "transfers all escrowed stockpile units of the named resource into "
            "the corresponding normal stockpile and sets that escrow balance to zero"
        ),
        lifetime=(
            "one-shot native resource-state mutation; the resulting normal stockpile "
            "persists as engine player state"
        ),
        ordering=(
            "release executes at its position in the emitted action sequence; this "
            "mapping does not claim same-pass visibility to a following ordinary action"
        ),
        admission=(
            "native release-escrow Action with exactly one Resource constant parameter; "
            "the compiler restricts that parameter to food, wood, stone, or gold"
        ),
        completion=(
            "the native mutation itself is the contracted operation; no separate "
            "world-state completion witness is synthesized"
        ),
        recovery=(
            "reassess the owning semantic demand; no automatic percentage reset, "
            "reacquisition, or starvation scheduler is emitted by this slice"
        ),
        practice_references=(),
    )

def _attack_issue_mapping() -> EngineSemanticMapping:
    return EngineSemanticMapping(
        identity="attack.execution.issue",
        native_command="attack-now",
        native_kind="Action",
        status=EngineSemanticMappingStatus.CONTRACTED,
        evidence_class="ENGINE FACT",
        evidence_sources=(
            "https://airef.github.io/commands/commands-details.html#attack-now",
            "https://github.com/justhop90-bot/ByzMetaTeacher/blob/main/docs/reference/engine/commands/attack-now.md",
        ),
        state_effects=(
            "issues the documented native attack-now command against currently "
            "available attack units; the compiler does not infer a completion state"
        ),
        lifetime=(
            "one-shot native action request; no compiler-owned completion lifetime "
            "is claimed by this contract"
        ),
        ordering="native action executes in emitted action order within the containing rule",
        admission="native attack-now command contract with exact zero-argument arity",
        completion="unobserved; no contracted native attack completion witness exists in this slice",
        recovery="reassess through future native evidence; no synthetic timer, release, or reset is emitted",
        practice_references=(),
    )

def _duc_group_mapping(command: str, identity: str) -> EngineSemanticMapping:
    native_kind = "Fact" if command == "up-group-size" else "Action"
    state_effects = {
        "up-create-group": (
            "creates or refreshes one engine-managed DUC group from the current local "
            "search result window; group membership remains native state"
        ),
        "up-reset-group": (
            "clears one engine-managed DUC group and invalidates its current membership"
        ),
        "up-set-group": (
            "replaces the selected local or remote search list with the current engine "
            "group membership and consequently affects downstream DUC target/list reads"
        ),
        "up-group-size": (
            "reads the current engine-managed DUC group cardinality as a Fact without "
            "mutating group state"
        ),
        "up-modify-group-flag": (
            "sets or clears the native control flag associated with one engine-managed "
            "DUC group"
        ),
    }[command]
    lifetime = {
        "up-create-group": (
            "group membership persists in engine state until reset, replacement, or "
            "another native invalidation"
        ),
        "up-reset-group": (
            "the group remains empty until a later native group creation/set operation"
        ),
        "up-set-group": (
            "the selected search list persists as engine state until another DUC "
            "search/list mutation replaces or resets it"
        ),
        "up-group-size": (
            "one Fact evaluation; the returned cardinality is not retained by the compiler"
        ),
        "up-modify-group-flag": (
            "the control flag persists as native group state until another flag update "
            "or group reset"
        ),
    }[command]
    ordering = (
        "native group state is evaluated or mutated at the command's emitted position; "
        "the compiler does not claim same-pass numeric visibility beyond ordinary native "
        "source ordering"
    )
    completion = (
        "the native group operation itself is the contracted command event; no generic "
        "world-state completion witness is synthesized"
    )
    recovery = (
        "reassess current group/search state and reissue the corresponding native "
        "group operation; no synthetic scheduler or hidden retry state is introduced"
    )
    return EngineSemanticMapping(
        identity=identity,
        native_command=command,
        native_kind=native_kind,
        status=EngineSemanticMappingStatus.CONTRACTED,
        evidence_class="ENGINE FACT",
        evidence_sources=(_AOERF, _AOERF_PER, _AOE2AI, _DUKE),
        state_effects=state_effects,
        lifetime=lifetime,
        ordering=ordering,
        admission=(
            "native DUC group command is present in the pinned AIRef schema with the "
            "documented arity and parameter roles"
        ),
        completion=completion,
        recovery=recovery,
        practice_references=(),
    )


def _duc_target_data_output_mapping(command: str, identity: str) -> EngineSemanticMapping:
    selected = command == "up-get-object-data"
    subject = "the selected target object" if selected else "the selected target object's target"
    return EngineSemanticMapping(
        identity=identity,
        native_command=command,
        native_kind="Fact/Action",
        status=EngineSemanticMappingStatus.CONTRACTED,
        evidence_class="ENGINE FACT",
        evidence_sources=(_AOERF, _AOERF_PER),
        state_effects=(
            f"reads documented object-data state for {subject} and writes one "
            "result value into the caller-supplied GoalId"
        ),
        lifetime=(
            "one-shot native read/output operation; the result remains in the "
            "supplied GoalId until another command changes it"
        ),
        ordering=(
            "the native read observes the current selected-target state at evaluation "
            "time; this mapping makes no claim about cross-pass target liveness"
        ),
        admission=(
            "native Fact/Action command with its documented ObjectData selector and "
            "OutputGoalId parameters"
        ),
        completion=(
            "the output write is the contracted event; the compiler does not infer "
            "the returned numeric/object-data value"
        ),
        recovery=(
            "reassess selected-target state and reissue the native reader when needed; "
            "runtime target liveness remains separate evidence"
        ),
        practice_references=(),
    )


def _duc_point_mapping(command: str, identity: str) -> EngineSemanticMapping:
    return EngineSemanticMapping(
        identity=identity,
        native_command=command,
        native_kind="Action",
        status=EngineSemanticMappingStatus.CONTRACTED,
        evidence_class="ENGINE FACT",
        evidence_sources=(_AOERF, _AOERF_PER),
        state_effects=(
            "reads the documented native Point source and writes its x/y result "
            "into two consecutive GoalIds supplied by the caller"
        ),
        lifetime=(
            "one-shot native output operation; the resulting coordinate values "
            "remain in the supplied Goals until another command changes them"
        ),
        ordering=(
            "the Action executes at its emitted position; later rules may consume "
            "the bound Goal pair, while this mapping makes no same-pass numeric-value claim"
        ),
        admission=(
            "native command is present in the pinned AIRef schema with exactly "
            "two parameters: Point input and OutputGoalId start"
        ),
        completion=(
            "the operation's native output write is the contracted event; the "
            "compiler does not infer the coordinate values themselves"
        ),
        recovery=(
            "reissue or replace the point-output command through normal rule "
            "reassessment; no synthetic geometry or stale-value clearing is emitted"
        ),
        practice_references=(),
    )


def _duc_mapping(command: str, identity: str) -> EngineSemanticMapping:
    native_kind = {
        "up-can-search": "Fact",
        "up-get-search-state": "Action",
        "up-get-group-size": "Action",
        "up-get-cost-delta": "Action",
        "up-find-local": "Fact/Action",
        "up-find-status-local": "Fact/Action",
        "up-find-remote": "Fact/Action",
        "up-find-status-remote": "Fact/Action",
        "up-find-resource": "Fact/Action",
        "up-add-object-by-id": "Action",
        "up-filter-distance": "Action",
        "up-filter-exclude": "Action",
        "up-filter-garrison": "Action",
        "up-filter-include": "Action",
        "up-filter-range": "Action",
        "up-filter-status": "Action",
        "up-reset-filters": "Action",
        "up-reset-search": "Action",
        "up-full-reset-search": "Action",
        "up-clean-search": "Action",
        "up-remove-objects": "Action",
        "up-set-target-by-id": "Action",
        "up-set-target-object": "Fact/Action",
        "up-set-target-point": "Action",
        "up-target-objects": "Action",
    }[command]
    return EngineSemanticMapping(
        identity=identity,
        native_command=command,
        native_kind=native_kind,
        status=EngineSemanticMappingStatus.CONTRACTED,
        evidence_class="ENGINE FACT",
        evidence_sources=(_AOERF, _AOERF_PER, _AOE2AI, _DUKE),
        state_effects=(
            "mutates or consumes documented DUC search, filter, target, or "
            "object-list engine state according to its native command contract"
        ),
        lifetime=(
            "DUC state remains engine-managed until the command's documented "
            "replacement/reset/invalidation semantics apply"
        ),
        ordering=(
            "later DUC operations in emitted source order observe the preceding "
            "native DUC state mutation in the same rule/pass sequence"
        ),
        admission=(
            "native command is present in the pinned AIRef schema with the "
            "documented parameter family and arity"
        ),
        completion=(
            "one-shot DUC control command has no generic compiler completion "
            "witness; runtime state remains the authority"
        ),
        recovery=(
            "re-establish or reset the affected DUC state using the corresponding "
            "native DUC command; no synthetic scheduler is introduced"
        ),
        practice_references=(
            ()
            if command == "up-get-cost-delta"
            else ("duc.search-state-retained",)
        ),
    )


def default_duc_executable_commands() -> tuple[str, ...]:
    return tuple(command for command, _identity in _DUC_COMMAND_SPECS)

def default_escrow_executable_commands() -> tuple[str, ...]:
    """Return commands promoted through the dedicated escrow binder."""
    return tuple(command for command, _identity in _ESCROW_COMMAND_SPECS)

def default_native_controller_executable_commands() -> tuple[str, ...]:
    """Return commands promoted through dedicated controller binders."""
    return ("attack-now",)



def _pending_mapping() -> EngineSemanticMapping:
    return EngineSemanticMapping(
        identity="execution.pending-objects",
        native_command="up-pending-objects",
        native_kind="Fact",
        status=EngineSemanticMappingStatus.CONTRACTED,
        evidence_class="ENGINE FACT",
        evidence_sources=(_AOERF, _AOERF_LIMITS, _AOE2AI),
        state_effects="reads outstanding native build/train work without proving target birth",
        lifetime="pending engine work persists until admitted work progresses, completes, or disappears",
        ordering="pending state is observed after native admission/issuance and before world-state completion",
        admission="native pending-work fact",
        completion="pending state is never a completion witness",
        recovery="use pending evidence to suppress duplicate issuance, then re-evaluate feasibility and world-state witnesses",
        practice_references=("pending.work-queue-guard",),
    )


def _pending_placement_mapping() -> EngineSemanticMapping:
    return EngineSemanticMapping(
        identity="execution.pending-placement",
        native_command="up-pending-placement",
        native_kind="Fact",
        status=EngineSemanticMappingStatus.CONTRACTED,
        evidence_class="ENGINE FACT",
        evidence_sources=(_AOERF, _AOERF_LIMITS),
        state_effects="reads native placement-work state for one building type without mutating construction policy",
        lifetime="placement request remains observable while the native placement system is attempting placement",
        ordering="observed after construction issuance and before a foundation exists",
        admission="native placement-pending observation",
        completion="placement pending never proves a foundation or completed building",
        recovery="re-evaluate placement state; explicit up-reset-placement remains a separate recovery action",
        practice_references=("build.can-pending-witness",),
    )


def default_engine_semantic_mapping_registry() -> EngineSemanticMappingRegistry:
    mappings: list[EngineSemanticMapping] = []
    for command, identity in _PERSISTENT_STATE_SPECS:
        mappings.append(_persistent_state_mapping(command, identity))
    for command, identity in _OBSERVATION_SPECS:
        mappings.append(_fact_mapping(command, identity, "OBSERVATION"))
    for command, identity in _ADMISSIBILITY_SPECS:
        mappings.append(_fact_mapping(command, identity, "ADMISSIBILITY"))
    for command, identity in _ARBITRATION_SPECS:
        mappings.append(_fact_mapping(command, identity, "ARBITRATION"))
    for command, identity in _FEASIBILITY_SPECS:
        mappings.append(_fact_mapping(command, identity, "FEASIBILITY"))
    for command, identity in _WITNESS_SPECS:
        mappings.append(_fact_mapping(command, identity, "WITNESS"))
    mappings.append(_pending_mapping())
    mappings.append(_pending_placement_mapping())
    mappings.extend(_action_mapping(command, identity) for command, identity in _ACTION_SPECS)
    mappings.extend(
        (
            _duc_group_mapping(command, identity)
            if command in {
                "up-create-group",
                "up-reset-group",
                "up-set-group",
                "up-group-size",
                "up-modify-group-flag",
            }
            else (
                _duc_target_data_output_mapping(command, identity)
                if command in {"up-get-object-data", "up-get-object-target-data"}
                else (
                    _duc_point_mapping(command, identity)
                    if command == "up-get-point"
                    else _duc_mapping(command, identity)
                )
            )
        )
        for command, identity in _DUC_COMMAND_SPECS
    )
    mappings.extend(
        _native_output_reader_mapping(command, identity)
        for command, identity in _NATIVE_OUTPUT_READER_SPECS
    )
    mappings.append(_escrow_release_mapping())
    mappings.append(_escrow_percentage_mapping())
    mappings.append(_attack_issue_mapping())
    mappings.extend(
        (
            EngineSemanticMapping(
                identity="duc.search-state-retained",
                native_command=None,
                native_kind=None,
                status=EngineSemanticMappingStatus.EVIDENCE_ONLY,
                evidence_class="ENGINE FACT",
                evidence_sources=(_AOERF, _AOERF_LIMITS),
                state_effects="retained DUC search state mutates engine search context",
                lifetime="retained across commands until reset or replacement",
                ordering="later DUC operations can observe retained search state",
                admission="not executable until DUC IR/lifetime mapping exists",
                completion="not a completion witness",
                recovery="unknown; evidence-only",
                practice_references=("duc.search-state-retained",),
            ),
            EngineSemanticMapping(
                identity="attack.group-state-control",
                native_command=None,
                native_kind=None,
                status=EngineSemanticMappingStatus.EVIDENCE_ONLY,
                evidence_class="COMMUNITY PRACTICE",
                evidence_sources=("https://forums.ageofempires.com/t/three-ways-to-get-the-ai-to-attack/205476",),
                state_effects="persistent attack-group control changes native attack behavior",
                lifetime="persists until native attack controls are changed",
                ordering="later control writes can override earlier attack state",
                admission="not executable until attack lifecycle semantics are mapped",
                completion="not a generic completion witness",
                recovery="unknown; evidence-only",
                practice_references=("attack.group-state-control",),
            ),
        )
    )
    registry = EngineSemanticMappingRegistry(tuple(mappings))
    from ..semantic.community_engine import default_community_engine_registry

    practice_ids = {
        item.identity for item in default_community_engine_registry().practices
    }
    registry.validate_practice_references(practice_ids)
    registry.validate_exact_executable_commands(
        tuple(command for command, _identity in _NATIVE_OUTPUT_READER_SPECS)
        + default_duc_executable_commands()
        + tuple(command for command, _identity in _PERSISTENT_STATE_SPECS)
        + tuple(command for command, _identity in _OBSERVATION_SPECS)
        + tuple(command for command, _identity in _ADMISSIBILITY_SPECS)
        + tuple(command for command, _identity in _ARBITRATION_SPECS)
        + tuple(command for command, _identity in _FEASIBILITY_SPECS)
        + tuple(command for command, _identity in _WITNESS_SPECS)
        + ("up-pending-objects", "up-pending-placement")
        + tuple(command for command, _identity in _ACTION_SPECS)
        + default_escrow_executable_commands()
        + default_native_controller_executable_commands()
    )
    return registry
