"""Authoritative engine-state/control effect contracts for native .per commands.

This catalog is the semantic bridge between the native command schema and the
compiler analyzers that reason about persistent engine state and rule control.
It deliberately describes effects, not strategy policy and not runtime
simulation.

A command may be natively known/typed without having an engine-effect contract.
Such a command remains unsupported by the semantic layer.  The contracts here
are limited to the generic Goal, Strategic Number, Timer, and rule-control
state that the compiler already analyzes elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class NativeStateDomain(str, Enum):
    GOAL = "GOAL"
    STRATEGIC_NUMBER = "STRATEGIC_NUMBER"
    TIMER = "TIMER"
    RULE_CONTROL = "RULE_CONTROL"


class NativeEffectKind(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    CONTROL = "CONTROL"


@dataclass(frozen=True)
class NativeEngineEffectContract:
    command: str
    native_kind: str
    domain: NativeStateDomain
    effect: NativeEffectKind
    identifier_arg: int | None
    persistent: bool
    same_pass_visible: bool
    typed_operand_dependency: bool
    evidence_sources: tuple[str, ...]
    semantics: str


@dataclass(frozen=True)
class NativeEngineEffectCatalog:
    contracts: tuple[NativeEngineEffectContract, ...]

    def __post_init__(self) -> None:
        commands = [item.command for item in self.contracts]
        if len(commands) != len(set(commands)):
            raise ValueError("duplicate native engine-effect command")

        for item in self.contracts:
            if not item.command:
                raise ValueError("native engine-effect command must not be empty")
            if item.native_kind not in {"Fact", "Action", "Fact/Action"}:
                raise ValueError(
                    f"unsupported native kind '{item.native_kind}' for '{item.command}'"
                )
            if item.identifier_arg is not None and item.identifier_arg < 0:
                raise ValueError(
                    f"identifier_arg for '{item.command}' must be non-negative"
                )
            if not item.evidence_sources:
                raise ValueError(
                    f"native engine-effect '{item.command}' lacks evidence"
                )
            for source in item.evidence_sources:
                if not isinstance(source, str) or not source.startswith(
                    ("https://", "http://", "repo://", "test://")
                ):
                    raise ValueError(
                        f"native engine-effect '{item.command}' has invalid evidence source"
                    )
            if not item.semantics:
                raise ValueError(
                    f"native engine-effect '{item.command}' lacks semantic description"
                )
            if item.domain is NativeStateDomain.RULE_CONTROL and item.effect is not NativeEffectKind.CONTROL:
                raise ValueError(
                    f"rule-control effect '{item.command}' must use CONTROL"
                )

    def get(self, command: str) -> NativeEngineEffectContract | None:
        for item in self.contracts:
            if item.command == command:
                return item
        return None

    def require(self, command: str) -> NativeEngineEffectContract:
        item = self.get(command)
        if item is None:
            raise KeyError(command)
        return item

    def commands(self) -> tuple[str, ...]:
        return tuple(sorted(item.command for item in self.contracts))

    def stateful_commands(self) -> frozenset[str]:
        return frozenset(item.command for item in self.contracts)

    def validate_native_registry(self, native_registry) -> None:
        for contract in self.contracts:
            native = native_registry.get(contract.command)
            if native is None:
                raise ValueError(
                    f"native engine-effect '{contract.command}' is absent from the "
                    "checked-in native schema"
                )
            if native.command_type != contract.native_kind:
                raise ValueError(
                    f"native engine-effect '{contract.command}' declares "
                    f"{contract.native_kind}, schema has {native.command_type}"
                )
            if (
                contract.identifier_arg is not None
                and contract.identifier_arg >= native.parameter_count
            ):
                raise ValueError(
                    f"native engine-effect '{contract.command}' identifier argument "
                    f"{contract.identifier_arg} is outside parameter count "
                    f"{native.parameter_count}"
                )

    def validate_effect(self, command: str, native_registry):
        contract = self.require(command)
        native = native_registry.get(command)
        if native is None:
            return False, f"native command '{command}' is absent from the checked-in schema"
        if native.command_type != contract.native_kind:
            return False, (
                f"native engine-effect '{command}' declares {contract.native_kind}, "
                f"schema has {native.command_type}"
            )
        if (
            contract.identifier_arg is not None
            and contract.identifier_arg >= native.parameter_count
        ):
            return False, (
                f"native engine-effect '{command}' identifier argument "
                f"{contract.identifier_arg} is outside native parameter count "
                f"{native.parameter_count}"
            )
        return True, "native engine-effect contract is mapped and schema-compatible"


_AOERF = "https://airef.github.io/"
_AOERF_LIMITS = "https://airef.github.io/resources/articles/data-limits.html"
_AOERF_COMMANDS = "https://airef.github.io/resources/articles/intro-to-commands.html"
_AOERF_SN = "https://airef.github.io/strategic-numbers/sn-index.html"
_AOERF_SWGB = "https://airef.github.io/resources/articles/swgb-scripting.html"
_SCHEMA = "repo://docs/reference/inventories/airef-command-schema.json"


def default_native_engine_effect_catalog() -> NativeEngineEffectCatalog:
    """Return the generic engine-state/control contracts currently modeled."""
    contracts = (
        NativeEngineEffectContract(
            command="up-find-player",
            native_kind="Action",
            domain=NativeStateDomain.GOAL,
            effect=NativeEffectKind.WRITE,
            identifier_arg=2,
            persistent=True,
            same_pass_visible=False,
            typed_operand_dependency=False,
            evidence_sources=(_AOERF_COMMANDS, _SCHEMA),
            semantics=(
                "selects a native player according to PlayerStance and FindPlayerMethod "
                "and writes the resulting player number into the supplied Goal"
            ),
        ),
        NativeEngineEffectContract(
            command="set-goal",
            native_kind="Action",
            domain=NativeStateDomain.GOAL,
            effect=NativeEffectKind.WRITE,
            identifier_arg=0,
            persistent=True,
            same_pass_visible=True,
            typed_operand_dependency=False,
            evidence_sources=(_AOERF_COMMANDS, _AOERF_LIMITS, _SCHEMA),
            semantics=(
                "writes a persistent Goal value; later rule evaluation can read the "
                "stored value until another native writer changes it"
            ),
        ),
        NativeEngineEffectContract(
            command="goal",
            native_kind="Fact",
            domain=NativeStateDomain.GOAL,
            effect=NativeEffectKind.READ,
            identifier_arg=0,
            persistent=True,
            same_pass_visible=True,
            typed_operand_dependency=False,
            evidence_sources=(_AOERF_COMMANDS, _AOERF_LIMITS, _SCHEMA),
            semantics="reads persistent Goal state during fact evaluation",
        ),
        NativeEngineEffectContract(
            command="up-compare-goal",
            native_kind="Fact",
            domain=NativeStateDomain.GOAL,
            effect=NativeEffectKind.READ,
            identifier_arg=0,
            persistent=True,
            same_pass_visible=True,
            typed_operand_dependency=True,
            evidence_sources=(_AOERF_COMMANDS, _SCHEMA),
            semantics=(
                "reads persistent Goal state and may resolve its comparison operand "
                "from another Goal or Strategic Number"
            ),
        ),
        NativeEngineEffectContract(
            command="up-modify-goal",
            native_kind="Fact/Action",
            domain=NativeStateDomain.GOAL,
            effect=NativeEffectKind.WRITE,
            identifier_arg=0,
            persistent=True,
            same_pass_visible=True,
            typed_operand_dependency=True,
            evidence_sources=(_AOERF_COMMANDS, _SCHEMA),
            semantics=(
                "mutates a persistent Goal using a native math operator; prefixed "
                "Goal/Strategic Number operands are additional persistent-state reads"
            ),
        ),
        NativeEngineEffectContract(
            command="set-strategic-number",
            native_kind="Action",
            domain=NativeStateDomain.STRATEGIC_NUMBER,
            effect=NativeEffectKind.WRITE,
            identifier_arg=0,
            persistent=True,
            same_pass_visible=True,
            typed_operand_dependency=False,
            evidence_sources=(_AOERF_COMMANDS, _AOERF_SN, _SCHEMA),
            semantics=(
                "directly assigns a persistent Strategic Number value; native engine "
                "behavior may depend on the selected SN"
            ),
        ),
        NativeEngineEffectContract(
            command="strategic-number",
            native_kind="Fact",
            domain=NativeStateDomain.STRATEGIC_NUMBER,
            effect=NativeEffectKind.READ,
            identifier_arg=0,
            persistent=True,
            same_pass_visible=True,
            typed_operand_dependency=True,
            evidence_sources=(_AOERF_COMMANDS, _AOERF_SN, _SCHEMA),
            semantics="reads persistent Strategic Number state during fact evaluation",
        ),
        NativeEngineEffectContract(
            command="up-compare-sn",
            native_kind="Fact",
            domain=NativeStateDomain.STRATEGIC_NUMBER,
            effect=NativeEffectKind.READ,
            identifier_arg=0,
            persistent=True,
            same_pass_visible=True,
            typed_operand_dependency=True,
            evidence_sources=(_AOERF_COMMANDS, _AOERF_SN, _SCHEMA),
            semantics=(
                "reads persistent Strategic Number state and may resolve its "
                "comparison operand from a Goal or another Strategic Number"
            ),
        ),
        NativeEngineEffectContract(
            command="up-modify-sn",
            native_kind="Fact/Action",
            domain=NativeStateDomain.STRATEGIC_NUMBER,
            effect=NativeEffectKind.WRITE,
            identifier_arg=0,
            persistent=True,
            same_pass_visible=True,
            typed_operand_dependency=True,
            evidence_sources=(_AOERF_COMMANDS, _AOERF_SN, _SCHEMA),
            semantics=(
                "mutates a persistent Strategic Number using a native math operator; "
                "prefixed Goal/Strategic Number operands are additional persistent-state reads"
            ),
        ),
        NativeEngineEffectContract(
            command="enable-timer",
            native_kind="Action",
            domain=NativeStateDomain.TIMER,
            effect=NativeEffectKind.WRITE,
            identifier_arg=0,
            persistent=True,
            same_pass_visible=True,
            typed_operand_dependency=False,
            evidence_sources=(_AOERF_SWGB, _AOERF_LIMITS, _SCHEMA),
            semantics="enables or rearms persistent timer state for the requested interval",
        ),
        NativeEngineEffectContract(
            command="disable-timer",
            native_kind="Action",
            domain=NativeStateDomain.TIMER,
            effect=NativeEffectKind.WRITE,
            identifier_arg=0,
            persistent=True,
            same_pass_visible=True,
            typed_operand_dependency=False,
            evidence_sources=(_AOERF_SWGB, _AOERF_LIMITS, _SCHEMA),
            semantics="disables persistent timer state",
        ),
        NativeEngineEffectContract(
            command="timer-triggered",
            native_kind="Fact",
            domain=NativeStateDomain.TIMER,
            effect=NativeEffectKind.READ,
            identifier_arg=0,
            persistent=True,
            same_pass_visible=True,
            typed_operand_dependency=False,
            evidence_sources=(_AOERF_SWGB, _AOERF_LIMITS, _SCHEMA),
            semantics="reads whether persistent timer state has reached the triggered state",
        ),
        NativeEngineEffectContract(
            command="up-set-timer",
            native_kind="Action",
            domain=NativeStateDomain.TIMER,
            effect=NativeEffectKind.WRITE,
            identifier_arg=1,
            persistent=True,
            same_pass_visible=True,
            typed_operand_dependency=False,
            evidence_sources=(_AOERF_SWGB, _AOERF_LIMITS, _SCHEMA),
            semantics=(
                "sets persistent timer state through the UP timer control surface; "
                "negative/zero-style native intervals have command-specific semantics"
            ),
        ),
        NativeEngineEffectContract(
            command="up-timer-status",
            native_kind="Fact",
            domain=NativeStateDomain.TIMER,
            effect=NativeEffectKind.READ,
            identifier_arg=0,
            persistent=True,
            same_pass_visible=True,
            typed_operand_dependency=False,
            evidence_sources=(_AOERF_COMMANDS, _AOERF_SWGB, _SCHEMA),
            semantics="reads persistent timer status state",
        ),
        NativeEngineEffectContract(
            command="disable-self",
            native_kind="Action",
            domain=NativeStateDomain.RULE_CONTROL,
            effect=NativeEffectKind.CONTROL,
            identifier_arg=None,
            persistent=True,
            same_pass_visible=False,
            typed_operand_dependency=False,
            evidence_sources=(_AOERF_COMMANDS, _SCHEMA),
            semantics=(
                "changes future eligibility of the currently firing rule without "
                "aborting the rest of that rule's current action sequence"
            ),
        ),
        NativeEngineEffectContract(
            command="up-jump-rule",
            native_kind="Action",
            domain=NativeStateDomain.RULE_CONTROL,
            effect=NativeEffectKind.CONTROL,
            identifier_arg=None,
            persistent=False,
            same_pass_visible=True,
            typed_operand_dependency=False,
            evidence_sources=(_AOERF_COMMANDS, _SCHEMA),
            semantics=(
                "changes the current pass control-flow target using the native "
                "relative RuleDelta convention"
            ),
        ),
    )
    return NativeEngineEffectCatalog(contracts)
