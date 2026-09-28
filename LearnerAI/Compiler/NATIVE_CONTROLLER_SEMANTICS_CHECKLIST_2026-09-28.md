# Native Controller Semantics Checklist
Date: 2026-09-28

## Purpose

This tranche cross-references the largest remaining semantic hole identified in the compiler: the native AI control plane that .per drives through persistent control surfaces.

The compiler already models native state lifetime, recurrent rule execution, lifecycle causality, source reachability, capability/dependency semantics, and substantial DUC state. The missing layer was the relationship between those state surfaces and the larger native controllers they steer.

This document is a boundary record, not a claim that every Strategic Number has been reverse-engineered. The interaction layer now records causal direction, endpoint type, lifetime, visibility, automatic mutation ownership, engine-version scope, and advisory performance/cardinality metadata.

## Community cross-reference

| Controller family | Concrete community evidence | Compiler disposition |
|---|---|---|
| Civilian task allocation | AIRef Strategic Number catalog documents gatherer/allocation controls; community examples explicitly change food/wood/gold/stone allocation by age and economic state; The Duke Resource-Control script repeatedly retunes these controls. | Typed controller + representative SN surfaces are catalogued; interactions remain evidence-only. |
| Exploration | AIRef and community attack examples use exploration group/count controls as prerequisites for finding enemy objects; attack documentation explicitly states that attack methods operate on explored enemy objects. | Typed controller + representative SN surfaces are catalogued; attack dependency is evidence-only. |
| Attack-group control | Community attack documentation uses attack-now/attack-groups with persistent SN and timer control; mature scripts contain dedicated attack-control modules. | Typed controller + representative command/SN surfaces are catalogued; runtime attack-state semantics remain evidence-only. |
| Town-size defense/targeting | Community documentation shows town size and enemy-sighted response controls being changed together to alter defensive/targeting behavior. | Typed controller + representative SN surfaces are catalogued; targeting interaction is evidence-only. |
| Resource/escrow control | The community scripting guide documents escrow percentages and explicit release; The Duke contains a dedicated Resource-Control module using Goals and SNs around resource allocation. | Typed controller + escrow command surfaces are catalogued; persistent arbitration semantics remain outside this tranche. |
| DUC search state | AIRef documents stateful local/remote search lists, bounded capacities, search-state, and reset behavior; lewisc64/aoe2ai has explicit DUC search/reset/group rules. | Typed controller + representative search surfaces are catalogued; detailed SearchSession/TargetSession semantics remain in the DUC tranche. |

Sources:
- https://airef.github.io/
- https://airef.github.io/strategic-numbers/sn-index.html
- https://airef.github.io/resources/articles/command-performance.html
- https://userpatch.aiscripters.net/reference.html
- https://github.com/lewisc64/aoe2ai
- https://github.com/niektb/AI
- https://forums.ageofempires.com/t/three-ways-to-get-the-ai-to-attack/205476
- https://forums.ageofempires.com/t/creating-simple-ai-scripts-for-your-custom-campaigns/210881

## Implemented contracts

- [x] Typed native controller domains.
- [x] Typed control-surface kinds.
- [x] Typed controller-to-controller interaction relations.
- [x] Explicit evidence class and practice status on controllers, surfaces, and edges.
- [x] Deterministic controller/surface/edge ordering.
- [x] Duplicate identity detection.
- [x] Duplicate native lookup-key detection.
- [x] Unknown controller reference detection.
- [x] Self-interaction rejection.
- [x] Fail-closed executable-surface gate.
- [x] Native control surfaces remain evidence-only until a controller and surface both have contractual engine facts.
- [x] Nine controller families seeded from explicit community/native references.
- [x] Representative Strategic Number, command, DUC target, production-admission, and research-admission surfaces seeded.
- [x] Strategic Number semantic analysis emits deterministic controller binding metadata without changing arithmetic or lowering.
- [x] Unmapped Strategic Numbers remain valid semantic/native state without fabricated controller claims.
- [x] Deterministic controller fingerprinting.
- [x] Typed controller-to-controller and surface-to-controller interaction contract.
- [x] Directed interaction validation with contradiction rejection.
- [x] Feedback relations excluded from dependency edges.
- [x] Explicit interaction lifetime and pass-visibility semantics.
- [x] Explicit engine-version scope and fail-closed scope mismatch validation.
- [x] Explicit mutation ownership distinguishing automatic engine mutation from compiler action.
- [x] Evidence-only interaction status preserved until native mapping is justified.
- [x] DUC local/remote cardinality and advisory performance metadata recorded.
- [x] Strategic Number report carries deterministic inbound/outbound interaction bindings.

## Native Controller Interaction Semantics

The interaction substrate is implemented in `semantic/native_controller_interactions.py`. It is intentionally descriptive and does not alter `.per` lowering. The seeded corpus covers attack-group gating by exploration, town-size effects on attack targeting, civilian-allocation/resource-escrow coupling, escrow-aware production/research admission, DUC search-to-target handoff, and documented automatic DUC search-index resets caused by filter changes. The DUC search interactions carry explicit local/remote cardinality bounds of 240/40 and qualitative performance classes derived from AIRef benchmarks.

All seeded relationships remain `EVIDENCE_ONLY`. No interaction has been promoted to `ENGINE_SEMANTICS_MAPPED` merely because community practice is strong. Interaction version scope must cover the target DE family, feedback relations are non-dependency edges, and automatic mutations require explicit `ENGINE_AUTOMATIC` ownership.

## Deliberately not claimed

- [ ] Complete 512-Strategic-Number controller classification.
- [ ] Native controller simulation.
- [ ] Automatic strategy selection from controller state.
- [ ] Attack-engine completion/release semantics.
- [ ] Full DUC SearchSession/TargetSession implementation.
- [ ] Performance-cost propagation through recurrent loops.
- [ ] Automatic promotion of community interactions to executable mappings.

## Acceptance boundary

The tranche is accepted as a substrate only when:

1. The focused Native Controller tests pass.
2. Strategic Number semantic regression tests pass.
3. Full compiler regression remains green.
4. Cross-platform native-support determinism remains green.
5. Native zero-findings fixtures remain unchanged.
6. The controller graph remains descriptive/evidence-backed and does not alter emitted .per behavior.
