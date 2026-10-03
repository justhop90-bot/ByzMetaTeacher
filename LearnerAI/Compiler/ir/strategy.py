        "Mounted pressure has cleared enough to resume the economic trajectory",
        "Castle commitment is obsolete once Imperial Age is reached without the strategic Castle path",
        "Castle completion materially changes the strategic posture",
    }

    def annotate_meta(evidence: StrategicEvidence) -> StrategicEvidence:
        if evidence.label in meta_labels:
            return replace(
                evidence,
                source=StrategicEvidenceSource.COMMUNITY_META,
                provenance=meta_provenance,
            )
        return evidence

    def annotate_demand(demand: StrategicDemandSpec) -> StrategicDemandSpec:
        execution = demand.execution
        if demand.identity == "feudal-transition":
            execution = replace(
                execution,
                requirements=(
                    *execution.requirements,
                    "(research-completed 22)",
                ),
            )
        return replace(
            demand,
            reason=tuple(annotate_meta(evidence) for evidence in demand.reason),
            admissibility=tuple(annotate_meta(evidence) for evidence in demand.admissibility),
            invalidation=tuple(annotate_meta(evidence) for evidence in demand.invalidation),
            execution=execution,
        )

    demands = tuple(annotate_demand(demand) for demand in profile.demands)
    transitions = tuple(
        replace(
            transition,
            evidence=tuple(
                replace(
                    evidence,
                    source=StrategicEvidenceSource.COMMUNITY_META,
                    provenance=meta_provenance,
                )
                if evidence.label in meta_labels
                else evidence
                for evidence in transition.evidence
            ),
        )
        for transition in profile.transitions
    )
    from ..semantic.policy_recipe import default_byzantine_policy_recipes
    from .counter_strategy import default_byzantine_counter_packages

    counter_demands = _byzantine_counter_demands()
    return replace(
        profile,
        demands=(*demands, *counter_demands),
        transitions=transitions,
        provenance=(*profile.provenance, *meta_provenance),
        capability_observations=_byzantine_capability_observations(effective),
        strategic_number_modes=_byzantine_strategic_number_modes(),
        policy_recipes=default_byzantine_policy_recipes(),
        counter_packages=default_byzantine_counter_packages(effective),
        attack_plan=_default_byzantine_attack_plan(profile.profile_id),
        duc_plan=_default_byzantine_duc_plan(profile.profile_id),
    )

def _validate_capability_intent(
    demand: StrategicDemandSpec,
    effective: EffectiveCivData,
) -> None:
    _validate_capability_intent_value(demand, demand.capability_intent, effective)


def _validate_capability_intent_value(
    demand: StrategicDemandSpec,
    intent: CapabilityIntent,
    effective: EffectiveCivData,
) -> None:
    if intent.kind is CapabilityIntentKind.BUILD:
        if int(intent.entity_id) not in effective.available_buildings:
            raise ValueError(
                f"strategic demand '{demand.identity}' references unknown building {intent.entity_id}"
            )
        if intent.provider_building is not None:
            effective.building(int(intent.provider_building))
    elif intent.kind is CapabilityIntentKind.TRAIN: