# Byzantine technology manifest materialization

This tranche closes the machine-provable Byzantine technology coverage backed by the pinned 185872 technology snapshot.

Closed:
- Age-advance native TechIds 101, 102, and 103 now count as modeled manifest technology nodes because they are already represented as typed `AgeAdvanceDef.native_tech_id` records.
- 51 previously unmodeled technology nodes are materialized from the authoritative manifest plus the pinned 185872 aoe2techtree snapshot.
- Materialized fields are limited to manifest name/age/provider plus snapshot cost/research time.
- Every materialized technology carries both repository-manifest and immutable ENGINE_DATA provenance.
- Seed generation is fail-closed on normalized manifest/snapshot name conflicts.

Remaining:
- TechIds 54, 408, and 909 remain unmodeled because the pinned snapshot's IDs disagree with the manifest's semantic identities.
- The remaining 16 unmodeled manifest nodes are units/buildings and require separate factual sources.
- Prerequisites, effects, broader civ overlays, native IDs, and replayable patch overlays remain outside this tranche.
