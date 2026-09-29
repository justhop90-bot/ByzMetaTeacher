# DAT-derived technology snapshot import boundary

This repair adds the compiler-owned ingestion seam for DAT-derived technology metadata.

Imported factual fields:
- TechId
- native civ id
- resource cost
- research time
- research location
- effect id
- required technology ids

Promotion rules:
- snapshot patch must exactly equal the target GameData patch
- immutable source content hash and ENGINE_DATA evidence are mandatory
- TechId must exist in GameData
- technology names must match exactly
- existing non-null GameData cost/time values are preserved
- existing prerequisites, effects, provider data, and civ availability are not synthesized from the snapshot

No current live DAT values are committed by this tranche. The snapshot parser is the deterministic source boundary that a verified current DAT extraction can populate later.
