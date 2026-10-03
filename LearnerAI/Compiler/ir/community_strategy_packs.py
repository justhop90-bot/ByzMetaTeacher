            action=f"(train {action_symbol})",
            witness=f"(unit-type-count {witness_symbol} >= {minimum})",
            release=f"(unit-type-count {witness_symbol} >= {minimum})",
        ),
        recovery=_CapabilityRecoveryContract(),
    )


_CASTLE_BANK_HARD_FOOD = 800
_CASTLE_BANK_HARD_GOLD = 200

_FEUDAL_RESEARCH_BANKS = {
    "wheelbarrow": ((Resource.FOOD, 1000), (Resource.GOLD, 250)),
    "double-bit-axe": ((Resource.FOOD, 900), (Resource.GOLD, 250)),
    "horse-collar": ((Resource.FOOD, 900), (Resource.GOLD, 250)),
    "gold-mining": ((Resource.FOOD, 900), (Resource.GOLD, 250)),
}

def _feudal_research_bank_floors(
    effective: EffectiveCivData,
    tech_name: str,
) -> tuple[tuple[Resource, int], ...]:
    """Keep the Castle bank intact after a Feudal technology is paid."""
    if tech_name not in _FEUDAL_RESEARCH_BANKS:
        return ()
    policy = dict(_FEUDAL_RESEARCH_BANKS[tech_name])
    tech = _tech(effective, tech_name)
    cost = tech.base_cost
    if isinstance(cost, ResourceCost):
        policy[Resource.FOOD] = max(
            policy.get(Resource.FOOD, 0),
            _CASTLE_BANK_HARD_FOOD + cost.food,
        )
        policy[Resource.GOLD] = max(
            policy.get(Resource.GOLD, 0),
            _CASTLE_BANK_HARD_GOLD + cost.gold,
        )
    else:
        # Variable costs are not a justified hard bank rule. Preserve the
        # established research floor and leave the variable portion OPEN.
        policy[Resource.FOOD] = max(
            policy.get(Resource.FOOD, 0),
            _CASTLE_BANK_HARD_FOOD,
        )
        policy[Resource.GOLD] = max(
            policy.get(Resource.GOLD, 0),
            _CASTLE_BANK_HARD_GOLD,
        )
    return tuple(sorted(policy.items(), key=lambda item: item[0].value))

_RESEARCH_PACK = (
    ("research-wheelbarrow", "economy", "feudal-age", "wheelbarrow", _StrategicPriority.SUPPORT, (Resource.FOOD,)),
    ("research-double-bit-axe", "economy", "feudal-age", "double-bit-axe", _StrategicPriority.SUPPORT, (Resource.FOOD, Resource.WOOD)),
    ("research-horse-collar", "economy", "feudal-age", "horse-collar", _StrategicPriority.SUPPORT, (Resource.FOOD, Resource.WOOD)),
    ("research-hand-cart", "economy", "castle-age", "hand-cart", _StrategicPriority.SUPPORT, (Resource.FOOD, Resource.WOOD)),
    ("research-bow-saw", "economy", "castle-age", "bow-saw", _StrategicPriority.SUPPORT, (Resource.WOOD, Resource.GOLD)),
    ("research-two-man-saw", "economy", "imperial-age", "two-man-saw", _StrategicPriority.SUPPORT, (Resource.WOOD, Resource.GOLD)),
    ("research-bodkin-arrow", "military", "castle-age", "bodkin-arrow", _StrategicPriority.SUPPORT, (Resource.FOOD, Resource.GOLD)),
    ("research-conscription", "military", "imperial-age", "conscription", _StrategicPriority.SUPPORT, (Resource.FOOD, Resource.GOLD)),
    ("research-chemistry", "military", "imperial-age", "chemistry", _StrategicPriority.SUPPORT, (Resource.GOLD,)),
    ("research-gold-mining", "economy", "feudal-age", "gold-mining", _StrategicPriority.SUPPORT, (Resource.FOOD,)),
    ("research-gold-shaft-mining", "economy", "castle-age", "gold-shaft-mining", _StrategicPriority.SUPPORT, (Resource.FOOD, Resource.GOLD)),
    ("research-heavy-plow", "economy", "castle-age", "heavy-plow", _StrategicPriority.SUPPORT, (Resource.FOOD, Resource.WOOD)),
    ("research-fletching", "military", "feudal-age", "fletching", _StrategicPriority.SUPPORT, (Resource.FOOD, Resource.GOLD)),
)


def community_strategy_observations(
    effective: EffectiveCivData,
) -> tuple[_StrategicObservationSpec, ...]:
    town_center = _building(effective, "town-center")
    outpost = _building(effective, "outpost")
    monastery = _building(effective, "monastery")
    siege_workshop = _building(effective, "siege-workshop")
    stable = _building(effective, "stable")
    archery_range = _building(effective, "archery-range")
    dock = _building(effective, "dock")
    blacksmith = _building(effective, "blacksmith")
    barracks = _building(effective, "barracks")
    castle = _building(effective, "castle")
    university = _building(effective, "university")
    lumber_camp = _building(effective, "lumber-camp")
    mining_camp = _building(effective, "mining-camp")
    observations = [
        _observation(
            "strategy-castle-age",
            "(current-age >= castle-age)",
            effective.age_advance(Age.CASTLE).provenance,
        ),
        _observation(
            "strategy-imperial-age",
            "(current-age >= imperial-age)",
            effective.age_advance(Age.IMPERIAL).provenance,
        ),
        _observation(
            "strategy-arena-map",
            "(map-type arena)",
            _airef_provenance(effective, "commands/commands-details.html#map-type"),
        ),
        _observation(
            "strategy-arabia-map",
            "(map-type arabia)",
            _airef_provenance(effective, "commands/commands-details.html#map-type"),
        ),
        _observation(
            "strategy-opening-pressure",
            "(players-unit-type-count any-enemy militia-line >= 5)",
            effective.unit_line("militia-line").provenance,
        ),
        _observation(
            "strategy-enemy-pressure",
            "(or (players-unit-type-count any-enemy knight >= 3) "
            "(or (players-unit-type-count any-enemy archer-line >= 4) "
            "(players-unit-type-count any-enemy militia-line >= 5)))",
            tuple(
                dict.fromkeys(
                    (*effective.unit_line("knight-line").provenance,
                     *effective.unit_line("archer-line").provenance,
                     *effective.unit_line("militia-line").provenance)
                )
            ),
        ),
        _observation(
            "strategy-arabia-early-pressure",
            "(or (players-unit-type-count any-enemy militia-line >= 3) "
            "(or (players-unit-type-count any-enemy scout-cavalry-line >= 3) "
            "(or (players-unit-type-count any-enemy archer-line >= 3) "
            "(or (players-unit-type-count any-enemy knight >= 1) "
            "(and (players-building-type-count any-enemy barracks >= 1) "
            "(players-military-population any-enemy >= 3)))))",
            tuple(
                dict.fromkeys(
                    (*effective.unit_line("knight-line").provenance,
                     *effective.unit_line("scout-cavalry-line").provenance,
                     *effective.unit_line("archer-line").provenance,
                     *effective.unit_line("militia-line").provenance)
                )
            ),
        ),
        _observation(
            "strategy-arabia-early-pressure-cleared",
            "(and (players-unit-type-count any-enemy militia-line < 3) "
            "(players-unit-type-count any-enemy scout-cavalry-line < 3) "
            "(players-unit-type-count any-enemy archer-line < 3) "
            "(players-unit-type-count any-enemy knight < 1))",
            tuple(
                dict.fromkeys(
                    (*effective.unit_line("knight-line").provenance,
                     *effective.unit_line("scout-cavalry-line").provenance,
                     *effective.unit_line("archer-line").provenance,
                     *effective.unit_line("militia-line").provenance)
                )
            ),
        ),
        _observation(
            "strategy-enemy-infantry-pressure",
            "(players-unit-type-count any-enemy militia-line >= 5)",
            effective.unit_line("militia-line").provenance,
        ),
        _observation(
            "strategy-enemy-infantry-pressure-cleared",
            "(players-unit-type-count any-enemy militia-line < 5)",
            effective.unit_line("militia-line").provenance,
        ),
        _observation(
            "strategy-enemy-ranged",
            "(players-unit-type-count any-enemy archer-line >= 4)",
            effective.unit_line("archer-line").provenance,
        ),
        _observation(
            "strategy-enemy-siege",
            "(players-unit-type-count any-enemy mangonel-line >= 2)",
            effective.unit_line("mangonel-line").provenance,
        ),
        _observation(
            "strategy-enemy-castle",
            f"(players-building-type-count any-enemy {int(castle.id)} >= 1)",
            castle.provenance,
        ),
        _observation(
            "strategy-town-center-capability",
            f"(building-type-count-total {int(town_center.id)} < 2)",
            town_center.provenance,
        ),
        _observation(
            "strategy-town-center-complete",
            f"(building-type-count-total {int(town_center.id)} >= 2)",
            town_center.provenance,
        ),
        _observation(
            "strategy-outpost-capability",
            f"(building-type-count-total {int(outpost.id)} < 1)",
            outpost.provenance,
        ),
        _observation(
            "strategy-monastery-capability",
            f"(building-type-count-total {int(monastery.id)} < 1)",
            monastery.provenance,
        ),
        _observation(
            "strategy-siege-workshop-capability",
            f"(building-type-count-total {int(siege_workshop.id)} < 1)",
            siege_workshop.provenance,
        ),
        _observation(
            "strategy-stable-capability",
            f"(building-type-count-total {int(stable.id)} < 1)",
            stable.provenance,
        ),
        _observation(
            "strategy-archery-capability",
            f"(building-type-count-total {int(archery_range.id)} < 1)",
            archery_range.provenance,
        ),
        _observation(
            "strategy-dock-exists",
            f"(building-type-count-total {int(dock.id)} >= 1)",
            dock.provenance,
        ),
        _observation(
            "strategy-water-islands",
            "(map-type islands)",
            _airef_provenance(effective, "commands/commands-details.html#map-type"),
        ),
        _observation(
            "strategy-own-transport-capable",
            "(unit-type-count transport-ship >= 1)",
            effective.unit(545).provenance,
        ),
        _observation(
            "strategy-enemy-naval-pressure",
            "(or (players-unit-type-count any-enemy galley-line >= 2) "
            "(players-unit-type-count any-enemy fire-galley-line >= 2))",
            tuple(
                dict.fromkeys(
                    (*effective.unit_line("galley-line").provenance,
                     *effective.unit_line("fire-galley-line").provenance)
                )
            ),
        ),
        _observation(
            "strategy-enemy-naval-pressure-cleared",
            "(and (players-unit-type-count any-enemy galley-line < 2) "
            "(players-unit-type-count any-enemy fire-galley-line < 2))",
            tuple(
                dict.fromkeys(
                    (*effective.unit_line("galley-line").provenance,
                     *effective.unit_line("fire-galley-line").provenance)
                )
            ),
        ),
        _observation(
            "strategy-own-warboat-floor",
            "(warboat-count >= 2)",
            _airef_provenance(effective, "commands/commands-details.html#warboat-count"),
        ),
        _observation(
            "strategy-blacksmith-exists",
            f"(building-type-count-total {int(blacksmith.id)} >= 1)",
            blacksmith.provenance,
        ),
        _observation(
            "strategy-barracks-exists",
            f"(building-type-count-total {int(barracks.id)} >= 1)",
            barracks.provenance,
        ),
        _observation(
            "strategy-university-exists",
            f"(building-type-count-total {int(university.id)} >= 1)",
            university.provenance,
        ),
        _observation(
            "strategy-arabia-loom-admission",
            "(and (map-type arabia) "
            "(and (current-age == dark-age) "
            "(and (unit-type-count-total villager >= 13) "
            "(and (building-type-count-total lumber-camp >= 1) "
            "(and (building-type-count-total mining-camp >= 1) "
            "(food-amount >= 50))))))",
            tuple(
                dict.fromkeys(
                    (*_airef_provenance(effective, "commands/commands-details.html#map-type"),
                     *lumber_camp.provenance,
                     *mining_camp.provenance,
                     *effective.tech(22).provenance)
                )
            ),
        ),
        _observation(
            "research-loom-complete",
            "(research-completed 22)",
            effective.tech(22).provenance,
        ),
        _observation(
            "research-loom-pending",
            "(not (research-completed 22))",
            effective.tech(22).provenance,
        ),
    ]

    # resource-found is the supported native resource-front fact. Its latch/live
    # behavior remains OPEN, so this layer treats it as an observation signal only;
    # actual camp service is witnessed independently through dropsite distance.
    for resource, gatherer_sn, distance_sn, label in (
        (CampResource.WOOD, "sn-wood-gatherer-percentage", "sn-lumber-camp-max-distance", "wood"),
        (CampResource.GOLD, "sn-gold-gatherer-percentage", "sn-mining-camp-max-distance", "gold"),
        (CampResource.STONE, "sn-stone-gatherer-percentage", "sn-mining-camp-max-distance", "stone"),
    ):
        observations.extend(
            (
                _observation(
                    f"camp-front-{label}-active",
                    (
                        "(and (current-age >= castle-age) (and (stone-amount < 650) (resource-found stone)))"
                        if resource is CampResource.STONE
                        else f"(resource-found {resource.value})"
                    ),
                    _airef_provenance(effective, "commands/commands-details.html#resource-found"),
                ),
                _observation(
                    f"camp-front-{label}-remote",
                    f"(or (dropsite-min-distance {resource.value} <= -1) (dropsite-min-distance {resource.value} s:>= {distance_sn}))",
                    _airef_provenance(effective, "commands/commands-details.html#dropsite-min-distance"),
                ),
            )
        )


    for identity, _owner, _age, tech_name, _priority, _resources in _RESEARCH_PACK:
        tech = _tech(effective, tech_name)
        observations.append(
            _observation(
                f"{identity}-complete",
                f"(research-completed {int(tech.id)})",
                tech.provenance,
            )
        )
        observations.append(
            _observation(
                f"{identity}-pending",
                f"(not (research-completed {int(tech.id)}))",
                tech.provenance,
            )
        )

    return tuple(observations)


def community_strategy_demands(
    effective: EffectiveCivData,
) -> tuple[_StrategicDemandSpec, ...]:
    town_center = _building(effective, "town-center")
    outpost = _building(effective, "outpost")
    monastery = _building(effective, "monastery")
    siege_workshop = _building(effective, "siege-workshop")
    stable = _building(effective, "stable")
    archery_range = _building(effective, "archery-range")
    university = _building(effective, "university")
    lumber_camp = _building(effective, "lumber-camp")
    mining_camp = _building(effective, "mining-camp")
    observations = community_strategy_observations(effective)

    demands: list[_StrategicDemandSpec] = []

    demands.append(
        _research_demand(
            effective=effective,
            identity="research-loom",
            owner="economy",
            posture=_StrategyPosture.BOOM,
            priority=_StrategicPriority.CORE,
            age_guard=(
                "(and (map-type arabia) "
                "(and (or (goal opening-plan 1) (goal opening-plan 2)) "
                "(and (current-age == dark-age) "
                "(and (unit-type-count-total villager >= 13) "
                "(and (building-type-count-total lumber-camp >= 1) "
                "(and (building-type-count-total mining-camp >= 1) "
                "(food-amount >= 50)))))))"
            ),
            age_observation_ref="strategy-arabia-loom-admission",
            tech_name="loom",
            reason_label="Standard Arabia opening requires Loom before the Feudal click window",
            resources=(Resource.FOOD,),
        )
    )

    camp_specs = (
        (CampResource.WOOD, lumber_camp, 6, "sn-lumber-camp-max-distance"),
        (CampResource.GOLD, mining_camp, 5, "sn-mining-camp-max-distance"),
        (CampResource.STONE, mining_camp, 5, "sn-mining-camp-max-distance"),
    )
    for resource, building, max_count, distance_sn in camp_specs:
        label = resource.value
        active_ref = f"camp-front-{label}-active"
        remote_ref = f"camp-front-{label}-remote"
        active_expression = next(