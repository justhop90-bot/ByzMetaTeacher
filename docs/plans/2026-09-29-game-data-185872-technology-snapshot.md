# Game-data 185872 technology snapshot promotion

Scope:
- Pin the current machine-readable aoe2techtree technology table for AoE2DE Update 185872.
- Preserve exact upstream provenance: repository revision 3bb43b1439eef88dfe7fe892d7f7dc41ac9dd76f and blob SHA c4f7da961e82a8231b1ba49459949c4d6e479bc8.
- Normalize only TechId, internal name, resource cost, and research time into a deterministic 201-record artifact.

Compiler contract:
- Parse the pinned artifact through the existing parse_dat_technologies_json normalization boundary.
- Construct ENGINE_DATA provenance from the pinned source metadata.
- Fill only unresolved TechnologyDef.base_cost and TechnologyDef.research_time_seconds values when TechId and name match exactly.
- Preserve existing providers, prerequisites, effects, unlocks, civ availability, and any non-null GameData fields.
- Do not claim raw-DAT semantics, runtime research behavior, patch-overlay replay, or completion of the remaining 73 manifest nodes.

Acceptance:
- Focused game-data test validates artifact schema, exact source revision/blob, 201 records, and a real Byzantine unresolved-field enrichment case for Tech 47 (Chemistry).
- Full Compiler regression, native zero-findings, cross-platform determinism, snapshot comparison, and aggregate Compiler verification gate remain authoritative.
