"""Typed arbitration IR for shared native Strategic Number controllers.

This layer models ownership and lifetime above NativeControlPlan. It does not
simulate runtime scheduling and it does not create a second .per language.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from ..ast import Expression


_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
_NATIVE_SN_MIN = 0
_NATIVE_SN_MAX = 511
_NATIVE_VALUE_MIN = -32768
_NATIVE_VALUE_MAX = 32767


class StrategicNumberControllerLayer(str, Enum):
    DEFAULT_BASE = "DEFAULT_BASE"
    AGE_BASE = "AGE_BASE"
    STRATEGY = "STRATEGY"
    TEMPORARY = "TEMPORARY"
    ACTION = "ACTION"
    RECOVERY = "RECOVERY"

    @property
    def precedence(self) -> int:
        return {
            StrategicNumberControllerLayer.DEFAULT_BASE: 0,
            StrategicNumberControllerLayer.AGE_BASE: 100,
            StrategicNumberControllerLayer.STRATEGY: 200,
            StrategicNumberControllerLayer.TEMPORARY: 300,
            StrategicNumberControllerLayer.ACTION: 400,
            StrategicNumberControllerLayer.RECOVERY: 500,
        }[self]


class StrategicNumberControllerScope(str, Enum):
    PERSISTENT = "PERSISTENT"
    UNTIL_RELEASE = "UNTIL_RELEASE"
    ACTION_SCOPED = "ACTION_SCOPED"


class StrategicNumberRestorationPolicy(str, Enum):
    REASSERT_UNDERLAY = "REASSERT_UNDERLAY"


class StrategicNumberReleaseEvidence(str, Enum):
    WORLD_WITNESS = "WORLD_WITNESS"
    TIMER_CADENCE = "TIMER_CADENCE"


@dataclass(frozen=True)
class StrategicNumberController:
    identity: str
    native_strategic_number_id: int
    value: int
    layer: StrategicNumberControllerLayer
    priority: int = 0
    activation_guard: Expression | None = None
    release_guard: Expression | None = None
    scope: StrategicNumberControllerScope = (
        StrategicNumberControllerScope.PERSISTENT
    )
    restoration: StrategicNumberRestorationPolicy = (
        StrategicNumberRestorationPolicy.REASSERT_UNDERLAY
    )
    release_evidence: StrategicNumberReleaseEvidence | None = None
    action_identity: str | None = None
    owner: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.identity, str) or not _IDENTIFIER_RE.fullmatch(
            self.identity
        ):
            raise ValueError(
                f"Strategic Number controller identity '{self.identity}' "
                "is not a valid .per identifier"
            )
        if not isinstance(self.native_strategic_number_id, int) or isinstance(
            self.native_strategic_number_id, bool
        ):
            raise ValueError("Strategic Number controller native id must be an integer")
        if not _NATIVE_SN_MIN <= self.native_strategic_number_id <= _NATIVE_SN_MAX:
            raise ValueError(
                "Strategic Number controller native id must be in range "
                f"{_NATIVE_SN_MIN}..{_NATIVE_SN_MAX}"
            )
        if not isinstance(self.value, int) or isinstance(self.value, bool):
            raise ValueError("Strategic Number controller value must be an integer")
        if not _NATIVE_VALUE_MIN <= self.value <= _NATIVE_VALUE_MAX:
            raise ValueError(
                "Strategic Number controller value must be in native constant range "
                f"{_NATIVE_VALUE_MIN}..{_NATIVE_VALUE_MAX}"
            )
        if not isinstance(self.priority, int) or isinstance(self.priority, bool):
            raise ValueError("Strategic Number controller priority must be an integer")
        if not self.owner.strip():
            raise ValueError("Strategic Number controller owner must not be empty")
        for field_name, guard in (
            ("activation_guard", self.activation_guard),
            ("release_guard", self.release_guard),
        ):
            if isinstance(guard, str) and not guard.strip():
                raise ValueError(
                    f"Strategic Number controller {field_name} must not be empty"
                )

        persistent_layers = {
            StrategicNumberControllerLayer.DEFAULT_BASE,
            StrategicNumberControllerLayer.AGE_BASE,
            StrategicNumberControllerLayer.STRATEGY,
        }
        override_layers = {
            StrategicNumberControllerLayer.TEMPORARY,
            StrategicNumberControllerLayer.ACTION,
            StrategicNumberControllerLayer.RECOVERY,
        }

        if self.layer in persistent_layers:
            if self.scope is not StrategicNumberControllerScope.PERSISTENT:
                raise ValueError(
                    f"{self.layer.value} controller must use PERSISTENT scope"
                )
            if self.release_guard is not None:
                raise ValueError(
                    "persistent Strategic Number controllers cannot define a release_guard"
                )
            if self.release_evidence is not None:
                raise ValueError(
                    "persistent Strategic Number controllers cannot define release_evidence"
                )
            if self.action_identity is not None:
                raise ValueError(
                    "persistent Strategic Number controllers cannot define action_identity"
                )
        elif self.layer is StrategicNumberControllerLayer.TEMPORARY:
            if self.scope is not StrategicNumberControllerScope.UNTIL_RELEASE:
                raise ValueError("TEMPORARY controller must use UNTIL_RELEASE scope")
            if self.release_guard is None:
                raise ValueError("TEMPORARY controller requires a release_guard")
            if self.release_evidence is None:
                raise ValueError("TEMPORARY controller requires release_evidence")
            if self.action_identity is not None:
                raise ValueError(
                    "TEMPORARY controller cannot define action_identity"
                )
        elif self.layer is StrategicNumberControllerLayer.ACTION:
            if self.scope is not StrategicNumberControllerScope.ACTION_SCOPED:
                raise ValueError("ACTION controller must use ACTION_SCOPED scope")
            if self.activation_guard is None:
                raise ValueError("ACTION controller requires an activation_guard")
            if self.release_guard is None:
                raise ValueError("ACTION controller requires a release_guard")
            if self.release_evidence is None:
                raise ValueError("ACTION controller requires release_evidence")
            if not self.action_identity or not self.action_identity.strip():
                raise ValueError("ACTION controller requires action_identity")
        elif self.layer is StrategicNumberControllerLayer.RECOVERY:
            if self.scope is not StrategicNumberControllerScope.UNTIL_RELEASE:
                raise ValueError("RECOVERY controller must use UNTIL_RELEASE scope")
            if self.activation_guard is None:
                raise ValueError("RECOVERY controller requires an activation_guard")
            if self.release_guard is None:
                raise ValueError("RECOVERY controller requires a release_guard")
            if self.release_evidence is None:
                raise ValueError("RECOVERY controller requires release_evidence")
            if self.action_identity is not None:
                raise ValueError(
                    "RECOVERY controller cannot define action_identity"
                )
        else:
            raise ValueError(
                f"unsupported Strategic Number controller layer {self.layer}"
            )

        if self.layer in override_layers and self.restoration is not (
            StrategicNumberRestorationPolicy.REASSERT_UNDERLAY
        ):
            raise ValueError(
                "all current Strategic Number overrides must restore by reasserting "
                "the current underlay"
            )

    @property
    def native_state_name(self) -> str:
        return f"sn-native-{self.native_strategic_number_id}"

    @property
    def activation_state_name(self) -> str:
        return f"sn-controller-{self.identity}-active"

    @property
    def precedence_key(self) -> tuple[int, int, int, str]:
        return (
            -self.layer.precedence,
            -self.priority,
            self.native_strategic_number_id,
            self.identity,
        )


@dataclass(frozen=True)
class StrategicNumberActionAttachment:
    identity: str
    controller_identity: str
    action_identity: str
    native_strategic_number_id: int
    value: int
    activation_state_name: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("identity", self.identity),
            ("controller_identity", self.controller_identity),
            ("action_identity", self.action_identity),
            ("activation_state_name", self.activation_state_name),
        ):
            if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
                raise ValueError(
                    f"Strategic Number action attachment {field_name} "
                    f"'{value}' is not a valid .per identifier"
                )
        if not _NATIVE_SN_MIN <= self.native_strategic_number_id <= _NATIVE_SN_MAX:
            raise ValueError(
                "Strategic Number action attachment native id must be in range "
                f"{_NATIVE_SN_MIN}..{_NATIVE_SN_MAX}"
            )
        if not _NATIVE_VALUE_MIN <= self.value <= _NATIVE_VALUE_MAX:
            raise ValueError(
                "Strategic Number action attachment value must be in native constant "
                f"range {_NATIVE_VALUE_MIN}..{_NATIVE_VALUE_MAX}"
            )


@dataclass(frozen=True)
class StrategicNumberArbitrationPlan:
    controllers: tuple[StrategicNumberController, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.controllers, tuple):
            raise TypeError("Strategic Number arbitration controllers must be a tuple")

        canonical: dict[str, StrategicNumberController] = {}
        for controller in self.controllers:
            existing = canonical.get(controller.identity)
            if existing is not None and existing != controller:
                raise ValueError(
                    f"duplicate Strategic Number controller identity '{controller.identity}'"
                )
            canonical[controller.identity] = controller

        grouped: dict[
            tuple[int, StrategicNumberControllerLayer, int, str],
            list[StrategicNumberController],
        ] = {}
        for controller in canonical.values():
            grouped.setdefault(
                (
                    controller.native_strategic_number_id,
                    controller.layer,
                    controller.priority,
                    _guard_key(controller.activation_guard),
                ),
                [],
            ).append(controller)

        for key, candidates in grouped.items():
            values = {item.value for item in candidates}
            if len(values) > 1:
                identities = ", ".join(
                    item.identity for item in sorted(candidates, key=lambda item: item.identity)
                )
                raise ValueError(
                    "conflicting Strategic Number controllers at equal precedence: "
                    f"{identities} for native Strategic Number {key[0]}"
                )

        object.__setattr__(
            self,
            "controllers",
            tuple(sorted(canonical.values(), key=lambda item: item.precedence_key)),
        )

    @property
    def native_strategic_number_ids(self) -> tuple[int, ...]:
        return tuple(
            sorted(
                {
                    controller.native_strategic_number_id
                    for controller in self.controllers
                }
            )
        )

    def controller(self, identity: str) -> StrategicNumberController:
        for controller in self.controllers:
            if controller.identity == identity:
                return controller
        raise KeyError(identity)

    def controllers_for_sn(
        self,
        native_strategic_number_id: int,
    ) -> tuple[StrategicNumberController, ...]:
        return tuple(
            controller
            for controller in self.controllers
            if controller.native_strategic_number_id == native_strategic_number_id
        )


def _guard_key(expression: Expression | str | None) -> str:
    if expression is None:
        return ""
    return expression.source if isinstance(expression, Expression) else expression


__all__ = [
    "StrategicNumberActionAttachment",
    "StrategicNumberArbitrationPlan",
    "StrategicNumberController",
    "StrategicNumberControllerLayer",
    "StrategicNumberControllerScope",
    "StrategicNumberReleaseEvidence",
    "StrategicNumberRestorationPolicy",
]
