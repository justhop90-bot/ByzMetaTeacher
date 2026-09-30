# MUSE Community Gap Synthesis

Date: 2026-09-30
Status: research input for the authoritative compiler roadmap.

## Scope

This pass cross-checked the reorganized repository, the 32-idiom catalog, the compiler gap matrix, native-unknown register, current AIRef/UserPatch documentation, and community repositories including Niek AI, lewisc64/aoe2ai, and The Duke.

## Core finding

The compiler is no longer missing a general semantic foundation. The remaining problem is native control synthesis: turning recurring community .per control patterns into existing typed compiler objects and deterministic lowering paths.

## Community findings

1. Production patterns routinely combine can-train, unit-type-count-total, up-pending-objects, and train. These are distinct admission, observation, pending, and action concerns. The missing relation is production arbitration ownership.

2. DUC is a coherent execution subsystem: search, filters, search state, target selection, groups, group flags, point outputs, cost outputs, object data, and direct control. The compiler must preserve provenance and target identity rather than flattening DUC into isolated commands.

3. Attack-now is an issue primitive, not a complete attack lifecycle. Community control systems combine attack groups, targeting settings, timers, exploration state, DUC, and reset behavior.

4. Goals, Strategic Numbers, and Timers form a persistent control plane. Community scripts use them for state machines, age modes, cadence, defense, attack, production, and recovery.

5. Escrow is a separate resource-control plane. Percentage policy, balance release, escrow-aware admission, ordinary resource consumption, and emergency release must remain distinct.

6. Mature community scripts increasingly combine DUC with adaptive attack and economic behavior. This means DUC closure and attack lifecycle closure are mutually reinforcing work, not independent feature islands.

7. The community corpus contains recurring higher-level patterns: goal FSMs, TSA ladders, military parity, counter trains, defense toggles, starvation recovery, water splits, map tables, and persistent research protection.

## Repository findings

Already substantially closed and should not be reopened as separate foundation work:
- Goal and GoalSpan storage/binding;
- generic demand lifecycle;
- completion witness/release/invalidation;
- capability graph and validation;
- source graph;
- construction lifecycle;
- typed research state;
- Timer allocation;
- Strategic Number storage;
- generic capability recovery;
- deterministic lowering and native acceptance;
- unified semantic program;
- military composition proof assembly;
- narrow DUC lowering;
- attack issue lowering;
- escrow release and percentage lowering.

Material gaps that remain:
- production/train arbitration;
- DUC SearchSession/TargetSession execution closure;
- attack lifecycle/controller semantics;
- expanded escrow/resource arbitration;
- active Strategic Number evidence closure;
- remaining Byzantine factual nodes;
- strategy synthesis from community idioms;
- broad community-corpus verification.

## Evidence boundaries that remain OPEN

- SN 264 exact DE enforcement and provider busy/queued behavior;
- production birth/queue-exit/next-pass ordering;
- same-pass escrow release visibility;
- attack-now completion and controller mediation;
- DUC target/object liveness and retained-filter behavior;
- timer countdown/pass granularity;
- resource-found latch/live behavior;
- load-random RNG/weight semantics;
- .xs/.per bridge semantics;
- package collisions between co-loaded AIs.

## Source set

AIRef: https://airef.github.io/
AIRef commands: https://airef.github.io/commands/commands-index.html
AIRef Strategic Numbers: https://airef.github.io/strategic-numbers/sn-index.html
AIRef limits: https://airef.github.io/resources/articles/data-limits.html
AIRef DUC/performance: https://airef.github.io/resources/articles/command-performance.html
UserPatch reference: https://userpatch.aiscripters.net/reference.html
UserPatch patch notes: https://airef.github.io/tables/up-patch-notes.html
Niek AI: https://github.com/niektb/AI
lewis64 aoe2ai: https://github.com/lewisc64/aoe2ai
The Duke AI: https://github.com/tim-kos/the_duke_ai

## MUSE conclusion

The highest-leverage path is production arbitration -> DUC target execution -> attack lifecycle -> escrow arbitration -> strategy synthesis -> community corpus closure.

This sequence uses existing compiler seams and keeps runtime uncertainty explicitly outside compiler fact.