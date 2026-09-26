# Native AoE2 Backend

The native backend is the syntax and engine-language boundary for LearnerAI.

LearnerAI owns player semantics. The backend owns native .per legality. AoE2DE owns actual behavior.

## Pipeline

    player specification
      -> LearnerAI semantic compiler
      -> deterministic .per
      -> staged artifact
      -> aoe2-ai-parser
      -> normalized native diagnostics
      -> runtime

## Why external

The community already has a capable native parser/linter:

https://github.com/joerollman/aoe2-ai-parser

Pinned identity:

    project: aoe2-ai-parser
    version: 0.1.0
    commit: 3dfa2583b7c2ec36b85ccb421ebd0abe9ff276ba
    Python: 3.12

It provides native parsing, argument/role validation, logical operator arity, rule-length checks, package/load analysis, AIRef-backed inventories, diagnostics, and formatting.

Do not copy that implementation here.

## Authority split

LearnerAI semantic authority:

- demand;
- persistent intent;
- capability;
- feasibility/action separation;
- pending;
- witness;
- release;
- invalidation;
- ownership;
- dependency diagnostics.

Native backend authority:

- .per syntax;
- command and parameter schema;
- logical arity;
- native rule size;
- native identifiers and references;
- native package/load analysis.

Runtime authority:

- whether actions execute;
- asynchronous completion;
- actual world-state change;
- actual timing.

## Process boundary

The adapter invokes the backend as an isolated process with:

- shell disabled;
- redirected stdin;
- captured stdout/stderr;
- temporary working directory;
- bounded timeout;
- sanitized Python environment;
- locked backend identity.

Only valid JSON on stdout is validation protocol.

Backend failure means validation evidence is unavailable. It is not equivalent to script rejection.

## Staging

    compile -> stage -> native validate -> promote

An invalid or unvalidated artifact must not replace an existing valid artifact.

## Protocol

The backend returns a finding envelope containing path, finding count, findings, and a failed flag.

LearnerAI normalizes severity, confidence, coordinates, paths, references, and diagnostic identity.

Native diagnostic codes remain unchanged.

## Fixtures

Protocol fixtures live under:

    LearnerAI/Compiler/tests/fixtures/native_backend/protocol

They cover malformed JSON, missing fields, count mismatch, bad enums, invalid spans, path mismatch, exit-code inconsistency, and stderr-only output.

## Source map

Use LearnerAI/SOURCE_MAP.md for all other engine and community references.

## Product boundary

Native validation is necessary for safe compiler output.

It is not evidence that the Byzantine player is strategically competent.
