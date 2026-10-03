"""Native Byzantine resource-front and camp-placement control."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..ast import SourceLocation
from ..runtime_binding import StrategicNumberRequest
from .model import SemanticId, StorageRequestId
from .native_control import NativeControlPlan, NativeControlRule, NativeControlState
from .strategic_number import StrategicNumberOrigin


class CampResource(str, Enum):
    WOOD = "wood"
    GOLD = "gold"
    STONE = "stone"


@dataclass(frozen=True)
class CampPlacementPolicy:
    resource: CampResource
    distance_sn: str
    native_strategic_number_id: int
    dark_distance: int
    feudal_distance: int
    castle_distance: int
    imperial_distance: int
    widening_step: int = 4

    @property
    def max_distance(self) -> int:
        return self.imperial_distance

    def __post_init__(self) -> None:
        values = (
            self.dark_distance,
            self.feudal_distance,
            self.castle_distance,
            self.imperial_distance,
            self.widening_step,
        )
        if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
            raise ValueError("camp placement distances must be integers")
        if not (
            1 <= self.dark_distance <= self.feudal_distance <= self.castle_distance
            <= self.imperial_distance <= 255
        ):
            raise ValueError("camp placement distances must be monotonic and in 1..255")
        if not 1 <= self.widening_step <= 32:
            raise ValueError("camp widening step must be in 1..32")
        if not self.distance_sn.strip():
            raise ValueError("camp distance Strategic Number name must not be empty")


@dataclass(frozen=True)
class ByzantineCampControllerPlan:
    controller_id: str
    policies: tuple[CampPlacementPolicy, ...]
    adjacent_dropsites_sn: str = "sn-allow-adjacent-dropsites"
    adjacent_dropsites_native_id: int = 272
    separation_sn: str = "sn-dropsite-separation-distance"
    separation_native_id: int = 248
    separation_distance: int = 6

    def __post_init__(self) -> None:
        if not self.controller_id.strip():
            raise ValueError("camp controller id must not be empty")
        if len(self.policies) != 3:
            raise ValueError("Byzantine camp controller requires wood, gold, and stone policies")
        resources = {policy.resource for policy in self.policies}
        if resources != set(CampResource):
            raise ValueError("camp controller must cover exactly wood, gold, and stone")
        if not 1 <= self.separation_distance <= 32:
            raise ValueError("dropsite separation distance must be in 1..32")


def default_byzantine_camp_controller() -> ByzantineCampControllerPlan:
    return ByzantineCampControllerPlan(
        controller_id="byzantine-camp-controller-v1",
        policies=(
            CampPlacementPolicy(
                CampResource.WOOD,
                "sn-lumber-camp-max-distance",
                260,
                16,
                20,
                28,
                36,
            ),
            CampPlacementPolicy(
                CampResource.GOLD,
                "sn-mining-camp-max-distance",
                261,
                16,
                20,
                28,
                36,
            ),
            CampPlacementPolicy(
                CampResource.STONE,
                "sn-mining-camp-max-distance",
                261,
                16,
                20,
                28,
                36,
            ),
        ),
    )


def lower_byzantine_camp_controller(
    plan: ByzantineCampControllerPlan,
    profile,
) -> NativeControlPlan:
    from ..semantic.analyzer import parse_expression

    states = [
        NativeControlState(
            plan.adjacent_dropsites_sn,
            StrategicNumberRequest(
                StorageRequestId(
                    SemanticId(plan.controller_id, plan.adjacent_dropsites_sn),
                    "camp-placement-strategic-number",
                ),
                why_not_goal=(
                    "Native camp placement Strategic Number controlling the one-tile "
                    "resource dropsite buffer."
                ),
                stability_key=f"{plan.controller_id}:272",
                origin=StrategicNumberOrigin.NATIVE_REFERENCE,
                native_strategic_number_id=plan.adjacent_dropsites_native_id,
            ),
        ),
        NativeControlState(
            plan.separation_sn,
            __import__("LearnerAI.Compiler.runtime_binding", fromlist=["StrategicNumberRequest"]).StrategicNumberRequest(
                StorageRequestId(
                    SemanticId(plan.controller_id, plan.separation_sn),
                    "camp-placement-strategic-number",
                ),
                why_not_goal=(
                    "Native dropsite spacing Strategic Number used to keep camp "
                    "placement clustered without overlap."
                ),
                stability_key=f"{plan.controller_id}:248",
                origin=StrategicNumberOrigin.NATIVE_REFERENCE,
                native_strategic_number_id=plan.separation_native_id,
            ),
        ),
    ]

    for policy in plan.policies:
        states.append(
            NativeControlState(
                policy.distance_sn,
                __import__("LearnerAI.Compiler.runtime_binding", fromlist=["StrategicNumberRequest"]).StrategicNumberRequest(
                    StorageRequestId(
                        SemanticId(plan.controller_id, policy.distance_sn),
                        "camp-placement-strategic-number",
                    ),
                    why_not_goal=(
                        "Native resource-specific camp placement radius; the controller "
                        "uses it to keep lumber/mining camps tied to the active resource front."
                    ),
                    stability_key=f"{plan.controller_id}:{policy.native_strategic_number_id}",
                    origin=StrategicNumberOrigin.NATIVE_REFERENCE,
                    native_strategic_number_id=policy.native_strategic_number_id,
                ),
            )
        )

    def rule(identity: str, facts: tuple[str, ...], actions: tuple[str, ...]) -> NativeControlRule:
        return NativeControlRule(
            identity,
            facts=tuple(parse_expression(expr, SourceLocation(1)) for expr in facts),
            actions=tuple(parse_expression(expr, SourceLocation(1)) for expr in actions),
        )

    rules: list[NativeControlRule] = [
        rule(
            "camp-placement-buffer-and-separation",
            (
                "(or "
                "(up-compare-sn sn-allow-adjacent-dropsites != 0) "
                "(up-compare-sn sn-dropsite-separation-distance != 6)"
                ")",
            ),
            (
                "(set-strategic-number sn-allow-adjacent-dropsites 0)",
                "(set-strategic-number sn-dropsite-separation-distance 6)",
            ),
        ),
    ]

    age_caps = (
        ("dark", 16, 20, 28, 36),
    )
    del age_caps

    for label, guard, wood_value, mine_value in (
        ("dark", "(current-age < feudal-age)", 16, 16),
        ("feudal", "(and (current-age >= feudal-age) (current-age < castle-age))", 20, 20),
        ("castle", "(and (current-age >= castle-age) (current-age < imperial-age))", 28, 28),
        ("imperial", "(current-age >= imperial-age)", 36, 36),
    ):
        rules.append(
            rule(
                f"camp-placement-radius-{label}",
                (guard,),
                (
                    f"(set-strategic-number sn-lumber-camp-max-distance {wood_value})",
                    f"(set-strategic-number sn-mining-camp-max-distance {mine_value})",
                ),
            )
        )

    for policy in plan.policies:
        remote = profile.observation(f"camp-front-{policy.resource.value}-remote").expression
        rules.append(
            rule(
                f"camp-placement-widen-{policy.resource.value}",
                (
                    remote,
                    f"(strategic-number {policy.distance_sn} < {policy.max_distance})",
                ),
                (
                    f"(up-modify-sn {policy.distance_sn} c:+ {policy.widening_step})",
                ),
            )
        )

    return NativeControlPlan(states=tuple(states), rules=tuple(rules))


__all__ = [
    "ByzantineCampControllerPlan",
    "CampPlacementPolicy",
    "CampResource",
    "default_byzantine_camp_controller",
    "lower_byzantine_camp_controller",
]
