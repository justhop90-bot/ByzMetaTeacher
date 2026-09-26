# LearnerAI Source Map

This file answers one practical question:

Where does the information needed to build the Byzantine player come from?

Do not invent an abstraction merely because the source location is unclear. Find the real source first.

## Authority hierarchy

Native .per command and parameter semantics: AIRef and docs/reference/AIREF-COMMAND-SOURCE.md.

Strategic numbers, objects, techs, and classes: docs/reference/inventories and docs/reference/BYZANTINES_manifest.txt.

Engine facts and behavior: docs/reference/engine, AIRef, and runtime verification where documentation is insufficient.

Current official AI direction: current World's Edge update notes, used for broad adaptation/recovery trends.

Community .per practice: established community AIs such as The Duke, Naga, Promisory-style stock AI, and scripting tutorials.

Current local controller: Basilisk/Basilisk.per plus docs/project and validation material.

Compiler semantics: LearnerAI/SCHEMAS.md, LIFECYCLE.md, Compiler/README.md, and the Compiler implementation.

Runtime truth: AoE2DE itself.

## Local reference families

### Native engine reference

Read:

    docs/reference/AIREF-COMMAND-SOURCE.md
    docs/reference/inventories/
    docs/reference/engine/
    docs/reference/BYZANTINES_manifest.txt

PER_PRIMITIVE_MAP.md is a teaching index into this material. It is not a substitute for AIRef.

### Community and Basilisk reference

Read:

    docs/project/BotDirection.txt
    docs/project/Basilisk-Controller-Specification.md
    docs/project/Preemption-Implementation-Checklist.md
    docs/audits/Basilisk-Lifecycle-Audit-2026-09.md
    docs/audits/Basilisk-Removable-State-Audit-2026-09.md
    validation/repair-lifecycle-replay.js
    validation/strategy-rush-checklist.md
    validation/castle-capability-checklist.md

For actual implementation behavior, trace Basilisk/Basilisk.per. Comments are intent, rules are implementation, and validation is regression evidence.

## Module-specific sources

Engine needs AIRef, native inventories, engine reference, and current Byzantine data.

Information needs scouting/search primitives, enemy composition facts, map context, and Basilisk scouting/threat rules. Read docs/reference/engine, PER_PRIMITIVE_MAP.md, and Basilisk/Basilisk.per.

Strategy needs opening interpretation, strategic posture, age objectives, adaptation, cancellation, and opportunity cost. Read docs/project/BotDirection.txt, docs/project/Basilisk-Controller-Specification.md, Basilisk/Basilisk.per, and validation/strategy-rush-checklist.md.

Economy needs worker continuity, resource shortages, farms, dropsites, age-up protection, Castle/TC investment, and recovery. Read Basilisk/Basilisk.per, docs/project/BotDirection.txt, docs/audits/Basilisk-BOOM-Patch-Checklist-2026-09.md, LearnerAI/Economy, and docs/reference/engine.

Construction needs prerequisites, builders, placement, pending state, resource claims, completion, and cancellation. Read Basilisk/Basilisk.per, validation/castle-capability-checklist.md, validation/repair-lifecycle-replay.js, docs/audits/Basilisk-Lifecycle-Audit-2026-09.md, and PER_PRIMITIVE_MAP.md.

Production needs current plus queued counts, production capability, standing targets, villager continuity, unit-role demands, research, and duplicate-queue guards. Read Basilisk/Basilisk.per, docs/project/BotDirection.txt, docs/audits/Basilisk-Lifecycle-Audit-2026-09.md, and LearnerAI/Production.

Military needs threat facts, minimum defense, counter packages, attack reserve, production scaling, retreat, reinforcement, siege, and reassessment. Read Basilisk/Basilisk.per, validation/strategy-rush-checklist.md, docs/project/BotDirection.txt, docs/reference/BYZANTINES_manifest.txt, and LearnerAI/Military.

State needs ownership, durable strategy memory, local execution memory, timers, release, and invalidation. Read LearnerAI/OWNERSHIP.md, SCHEMAS.md, LIFECYCLE.md, and docs/audits/Basilisk-Removable-State-Audit-2026-09.md.

Engineering needs parser constraints, rule size, logical arity, source order, lifecycle analysis, native validation, and runtime acceptance criteria. Read LearnerAI/ENGINEERING.md, validation/basilisk-validator.js, validation/basilisk-validator-selftest.js, validation/repair-lifecycle-replay.js, and LearnerAI/Compiler.

Compiler needs schemas, lifecycle rules, primitive profiles, IR, emitter, native backend protocol, and future ownership/dependency diagnostics. Read SCHEMAS.md, LIFECYCLE.md, Compiler/README.md, Compiler/RESEARCH_CHECKLIST.md, and Compiler/backends/README.md.

## Research workflow

1. Find the authority here.
2. Verify the native primitive in AIRef/inventories.
3. Find at least one established community pattern where available.
4. Compare against current Basilisk behavior.
5. Put the behavior in the correct owner.
6. Define demand, capability, feasibility, action, witness, release/invalidation.
7. Add static regression coverage.
8. Runtime-test the actual game.
9. Record the source and the failure mode in the relevant module document.

This keeps LearnerAI connected to the information it actually needs.
