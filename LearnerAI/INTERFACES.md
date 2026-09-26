# Interfaces and Ownership Contracts

These contracts describe how the modules cooperate to build one Byzantine player.

## Engine

Owns native facts, actions, strategic-number interfaces, timers, identifiers, and engine quirks.

Provides what the engine can report or attempt.

Does not decide strategic purpose.

Source: docs/reference/AIREF-COMMAND-SOURCE.md, docs/reference/inventories/, docs/reference/engine/, docs/reference/BYZANTINES_manifest.txt.

## Information

Owns observations and interpretations of the external position:

- scouting;
- enemy composition;
- map/game context;
- threat facts;
- observation freshness;
- re-observation.

Provides facts to Strategy and domains.

Does not directly execute counters or economic responses.

Source: AIRef/engine references plus current Basilisk scouting and threat rules.

## Strategy

Owns why the player wants a position.

Creates and cancels strategic posture and persistent demands.

Examples:

- Castle commitment;
- BOOM posture;
- controlled Feudal pressure;
- defensive posture;
- Imperial conversion.

Strategy does not directly build, train, research, or attack.

Source: docs/project/BotDirection.txt, docs/project/Basilisk-Controller-Specification.md, Basilisk/Basilisk.per.

## State

Owns persistent strategic representation and genuinely necessary execution memory.

A state value must have one owner, legal values, initialization, readers, writers, transition rules, and release/invalidation.

State represents decisions and lifecycles. It does not invent strategy.

Source: LearnerAI/OWNERSHIP.md, SCHEMAS.md, LIFECYCLE.md.

## Economy

Owns worker allocation, resources, farms, economic technologies, capital protection, and transient resource arbitration.

Its question is:

What resource shortage currently prevents the chosen strategy from functioning?

Economy does not decide which strategy exists.

Source: Basilisk/Basilisk.per, docs/project/BotDirection.txt, docs/audits/Basilisk-BOOM-Patch-Checklist-2026-09.md.

## Construction

Owns building capability and construction lifecycle.

It consumes building demands and produces infrastructure.

It must distinguish:

existing;
pending/foundation;
feasible;
action issued;
completed;
obsolete.

A build command is never the completion witness.

Source: validation/castle-capability-checklist.md, validation/repair-lifecycle-replay.js, docs/audits/Basilisk-Lifecycle-Audit-2026-09.md.

## Production

Owns production capability and queues for villagers, units, and technologies.

Capacity follows live production demand.

Production must be queue-aware and must not silently invent strategic purpose.

Source: Basilisk/Basilisk.per, docs/project/BotDirection.txt, LearnerAI/Production.

## Military

Owns military demands below strategic posture and military execution:

- minimum defense;
- counters;
- army readiness;
- attack reserve;
- attack;
- retreat;
- reinforcement;
- siege;
- recovery.

Military may translate Strategy and Information into military demands but does not rewrite global strategy silently.

Source: Basilisk/Basilisk.per, validation/strategy-rush-checklist.md, docs/project/BotDirection.txt.

## Engineering

Owns static validation, lifecycle diagnostics, native-validation plumbing, and verification discipline.

Engineering diagnoses.

It is not a hidden scheduler or gameplay manager.

Source: LearnerAI/ENGINEERING.md, validation/, LearnerAI/Compiler/.

## Compiler

Compiler is infrastructure shared by all modules.

It owns:

- source parsing;
- semantic lifecycle validation;
- demand/capability/witness diagnostics;
- deterministic .per emission;
- native backend integration.

It does not own gameplay strategy.

## Universal contract

Strategy owns why.

Domains own how.

Engine owns feasibility and execution.

World state proves completion.

Engineering validates the chain.

Compiler makes the semantic contract explicit and deterministic.
