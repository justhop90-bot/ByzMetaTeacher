# Byzantine Production Depth Scaling Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Byzantine military production capacity expand from witnessed standing-army demand instead of remaining at shallow fixed building floors.

**Architecture:** Reuse the existing `StrategicDemandSpec` / `_build_demand` lifecycle. Each provider-building ladder is admitted only by a native standing-unit observation and existing `can-build` feasibility. Current/queued production depth is deliberately not inferred from queue state because queue-capacity semantics remain OPEN. The resulting demands lower through the existing construction, capability, resource, and release machinery.

**Tech Stack:** Python strategy IR, existing semantic/lifecycle compiler, generated AoE2 .per, unittest, GitHub Actions native parser/determinism gates.

## Global Constraints

- Preserve DEMAND -> ADMISSIBILITY -> CAPABILITY -> FEASIBILITY -> ACTION -> WORLD-STATE WITNESS -> RELEASE.
- Preserve OBSERVATION -> ARBITRATION -> EXECUTION -> WITNESS -> RECOVERY -> REASSESSMENT.
- Standing-unit counts are engine observations, not queue witnesses.
- `can-build` remains permission/feasibility only.
- Do not add queue-depth facts, a second scheduler, or a second .per language.
- Production expansion must remain subordinate to age-transition and defensive/economic floors through the existing strategic priority/opportunity-cost machinery.
- Community AI patterns are behavioral evidence, not copied code.

### Task 1: Define demand-driven provider-depth ladders

**Files:**
- Modify: `LearnerAI/Compiler/ir/community_strategy_packs.py`
- Test: `LearnerAI/Compiler/tests/test_community_strategy_packs.py`

**Interfaces:**
- Consumes: `EffectiveCivData`, existing `StrategicDemandSpec`, `_build_demand`, verified unit/building symbols.
- Produces: Castle/Imperial provider-building demands for Barracks, Stable, Archery Range, and Siege Workshop.

- [ ] Add threshold observations for standing demand: stable at 6/12/18 cavalry, barracks at 6/12/18 halberdier-or-Varangian, range at 6/12/18 arbalest, siege workshop at 2/4/6 siege units.
- [ ] Add provider floors 2/3/4 respectively, with age guards and existing `can-build` admission.
- [ ] Witness completion with `building-type-count` and release from the completed floor.
- [ ] Use deterministic demand identities and existing strategic priorities. Do not inspect queue state.

### Task 2: Execute the red-green regression

**Files:**
- Test: `LearnerAI/Compiler/tests/test_community_strategy_packs.py`
- Generated artifact verification: `Byzantine.per`

- [ ] Add assertions for all four provider ladders and their exact threshold/building-count guards.
- [ ] Run the focused community strategy-pack test and require failure because the new demand identities are absent.
- [ ] Implement the strategy demands.
- [ ] Re-run the identical focused test and require success.
- [ ] Compile the strategy vertical slice and verify the generated .per contains the provider-depth demands without queue primitives.

### Task 3: Synchronize artifact and acceptance documentation

**Files:**
- Modify: `Byzantine.per`
- Modify: `docs/plans/2026-10-02-byzantine-expert-opponent-roadmap.md`
- Create: `docs/plans/2026-10-05-byzantine-production-depth.md`

**Interfaces:**
- Consumes: compiler-generated provider-depth policy.
- Produces: deterministic checked-in runtime artifact and recorded evidence boundary.

- [x] Implement standing-demand provider depth in the typed compiler: 12 Castle/Imperial provider demands with sequential floor witnesses and no queue-depth inference.
- [x] Synchronize `main/Byzantine.per` with equivalent root-local provider-depth lifecycles.
- [x] Record that production-depth scaling is standing-demand driven and queue semantics remain OPEN.
- [x] Add a regression note that the replay gap is shallow production infrastructure, not a request for larger unconditional premium-unit floors.

### Task 4: Full verification

- [ ] Run the focused test suite.
- [ ] Run the strategy production vertical-slice/native validation.
- [ ] Run the full compiler/native zero-findings/determinism workflow.
- [ ] Compare the checked-in artifact and compiler-produced artifact for deterministic equality.
- [ ] Do not claim runtime improvement without an actual AoE2 replay.
