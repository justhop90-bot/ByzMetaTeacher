# Community Strategy Implementation Audit — 2026-10-02

## Candidate

PR #273, branch `community-strategy-synthesis-2026-10-02`.

## Implemented in this candidate

### Economy / research
- Castle economic expansion demand.
- Imperial conversion demand with protected food/gold.
- Verified Byzantine research package for economy, ranged support, and Imperial conversion.
- Escrow-aware research lifecycle through existing execution machinery.
- Resource floors remain policy, not income simulation.

### Production / composition
- Castle Stable / Range / Siege Workshop / Monastery / University capability demands.
- Standing Castle Knight and Cataphract floors.
- Castle Mangonel support.
- Imperial Bombard Cannon conversion against enemy Castle evidence.
- Monk replacement floor.
- Existing counter-package arbitration remains authoritative.

### Information / scouting boundary
- Strategy-owned enemy pressure observations.
- Enemy siege observation.
- Enemy Castle observation.
- Research completion/pending observations.
- Existing DUC SearchSession/TargetSession substrate reused rather than duplicated.

### Fortification
- Conditional Outpost capability under sustained pressure.
- Exact wall/tower/Castle placement remains OPEN and is not falsely encoded.

### Water
- Dedicated professional water behavioral contract.
- Dock-gated fishing continuity in the stock strategy.
- Full water/transport environmental discovery and naval-control semantics remain staged behind proven observations and the existing water contract.

### Recovery
- Build demands preserve strategic demand through capability loss.
- Research demands preserve strategic demand through temporary execution loss.
- Training demands preserve replacement intent through provider loss.
- Existing generic recovery/reassertion substrate remains authoritative.

## Explicitly NOT closed

These are runtime or evidence gaps, not missing generic architecture:

- exact native production birth/queue-exit behavior;
- DUC target liveness and retained-filter behavior;
- exact attack acknowledgement and group-membership causality;
- automatic map/water profile discovery where native predicates are not proven;
- exact dock placement heuristics;
- exact transport landing completion;
- relic discovery/acquisition semantics;
- wall/tower placement quality;
- Strategic Number runtime effects where current evidence is incomplete;
- behavioral game/replay regression corpus.

## Closure rule

A strategy family is only promoted from OPEN when:

`community precedent -> typed contract -> executable lowering -> focused test -> native zero-findings -> full compiler regression -> determinism -> empirical confirmation where runtime semantics matter`

This candidate intentionally stops at the compiler-policy boundary when runtime evidence is missing.
