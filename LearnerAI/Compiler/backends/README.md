# Native AoE2 Backend

The LearnerAI compiler does not own the raw AoE2 .per language. It owns the teaching semantics layered on top of it.

The native backend is an external validator boundary:

    LearnerAI DSL
        -> parser / AST
        -> LearnerAI semantic analysis
        -> semantic IR
        -> deterministic .per emitter
        -> staged .per artifact
        -> native backend adapter
        -> subprocess: aoe2-ai-parser
        -> JSON diagnostics
        -> normalized NativeDiagnostic[]
        -> validation result

The AoE2 runtime remains the final authority for actual engine behavior.

## Why an external backend

Research found that the AoE2 community already has a substantially capable native parser/linter:
https://github.com/joerollman/aoe2-ai-parser

The current pinned upstream source is:

    project: aoe2-ai-parser
    version: 0.1.0
    commit: 3dfa2583b7c2ec36b85ccb421ebd0abe9ff276ba
    Python: >= 3.12
    license: GPL-3.0-or-later

It provides native .per parsing, command/fact/action validation, argument and role validation, logical operator arity checks, rule-length checks, load/package analysis, AIRef-backed native inventories, diagnostics, formatting, and package reporting.

That makes it unnecessary and undesirable for LearnerAI to rebuild those facilities.

The upstream implementation is not imported into LearnerAI. It is treated as a separately installed executable backend and invoked through an operating-system process boundary.

Do not copy its parser/linter implementation into this repository.

## Other related projects found during research

These projects are useful reference points, but none replaces the LearnerAI semantic layer.

- JOTworks/AgeOfPython: https://github.com/JOTworks/AgeOfPython
  A limited Python-like compiler for AoE2 script. It demonstrates a more general compiler approach with functions, loops, arrays, goals, and AIRef-derived information, but it is an alpha-scale general compiler rather than a lifecycle teaching DSL.
- ks07/aoe2-ai-fmt: https://github.com/ks07/aoe2-ai-fmt
  Basic .per parsing and formatting. It does not provide the semantic backend required here.
- KnightThymeTools/aoe2-aiscript: https://github.com/KnightThymeTools/aoe2-aiscript
  Editor/tooling lineage covering syntax, linting, signatures, and related conveniences.
- Jvinniec/aoe2-aiscript: https://github.com/Jvinniec/aoe2-aiscript
  Older editor tooling with completion and limited diagnostics.
- FLWL/aoe2-ai-module: https://github.com/FLWL/aoe2-ai-module
  Exposes native AI functionality to external code at runtime. It is not a compiler or static validation backend.
- mboop127/AlphaScripter: https://github.com/mboop127/AlphaScripter
  Explores generated/evolved AI scripts rather than compiler semantics.

Conclusion: no discovered project matches LearnerAI's specific combination of persistent demand lifecycle, capability/feasibility separation, pending state, world-state witnesses, release semantics, ownership, and teaching-oriented diagnostics.

## Authority split

Three authorities remain separate.

### LearnerAI semantic authority

LearnerAI owns:

- demand lifecycle;
- semantic roles;
- persistent intent;
- capability versus demand separation;
- feasibility versus execution;
- pending lifecycle;
- completion witnesses;
- release rules;
- ownership and lifecycle diagnostics;
- future dependency and teaching analysis.

### Native backend authority

The pinned aoe2-ai-parser owns:

- native .per syntax;
- native command/fact/action schemas;
- native parameter validation;
- native logical operator arity;
- native rule-length checking;
- load/package graph analysis;
- AIRef-backed native references;
- native diagnostic codes and locations.

### AoE2 runtime authority

The game engine owns:

- whether a command actually executes;
- whether resources, queues, prerequisites, and engine state permit an action;
- whether the intended world state actually appears;
- timing and asynchronous completion behavior.

A successful native lint is not runtime proof.

## Process boundary

The adapter invokes the backend as an independent process.

Conceptually:

    <backend-python> -m aoe2_ai_lab lint <staged-per> --profile default --json

The process is started with:

- shell=False;
- stdin redirected to DEVNULL;
- stdout captured as machine-readable protocol;
- stderr captured as process diagnostics only;
- a temporary working directory;
- a bounded timeout;
- PYTHONPATH, PYTHONHOME, PYTHONSTARTUP, and proxy variables removed;
- PYTHONNOUSERSITE=1;
- PYTHONDONTWRITEBYTECODE=1;
- PYTHONHASHSEED=0;
- NO_PROXY=* and no_proxy=*.

The adapter never imports aoe2_ai_lab.

Backend stderr is never parsed as a native finding. A message printed only to stderr does not become a NativeDiagnostic.

## Pinning

aoe2-ai-parser.lock is the source-of-truth pin.

Required identity:

    name = aoe2-ai-parser
    project_version = 0.1.0
    commit_sha = 3dfa2583b7c2ec36b85ccb421ebd0abe9ff276ba
    python_major_minor = 3.12

A version match with a different source commit is a mismatch.

The installation also exposes a local manifest.json containing the same identity. The adapter checks that manifest before invoking lint.

The backend is not auto-upgraded by the compiler.

## Protocol

The current single-file backend JSON envelope is:

    {
      "path": "...",
      "finding_count": 0,
      "findings": [],
      "failed": false
    }

Each upstream finding contains:

    {
      "path": "...",
      "line": 1,
      "severity": "error",
      "confidence": "definite",
      "code": "...",
      "message": "...",
      "suggestion": null,
      "references": [],
      "span": null
    }

LearnerAI immediately normalizes this into its own typed result model.

The adapter is therefore resilient to backend presentation changes without making the rest of the compiler depend directly on the upstream wire format.

## Normalization rules

Diagnostic codes are copied without renaming.

Severity is restricted to:

    error
    warning
    info

Confidence is restricted to:

    definite
    conditional

Unknown enum values are protocol errors.

The backend reports line numbers as one-based. Backend span columns are zero-based and end-exclusive. LearnerAI canonical source columns are one-based and end-exclusive.

Therefore:

    canonical.column     = backend.start_col + 1
    canonical.end_column = backend.end_col + 1

The adapter never invents a source span. A null span becomes a location with the backend line and null column/end coordinates.

Diagnostic paths are resolved relative to the backend working directory and must resolve to the staged artifact being validated. A finding for another file is a protocol error rather than something to be silently remapped.

The upstream finding count must equal len(findings). LearnerAI recomputes all summary counts from normalized diagnostics.

References are copied as opaque objects. The adapter does not interpret or rewrite their internal structure.

Diagnostic order is preserved.

## Diagnostic identity

Each normalized diagnostic receives a deterministic SHA-256 identifier based on:

    backend name
    backend commit
    diagnostic code
    canonical source path
    line
    column
    end line
    end column
    message

The fingerprint intentionally excludes suggestion, references, severity, and confidence.

## Result states

    VALIDATED
        backend ran successfully and reported no findings

    REJECTED
        backend ran successfully and reported a failed validation

    BACKEND_UNAVAILABLE
        executable or installation is missing

    BACKEND_VERSION_MISMATCH
        project version, source commit, or Python version is wrong

    BACKEND_PROTOCOL_ERROR
        stdout is malformed or structurally inconsistent

    BACKEND_TIMEOUT
        backend did not complete within the configured timeout

    BACKEND_PROCESS_ERROR
        process launch/execution failed before usable protocol output

Only VALIDATED and REJECTED represent native validation evidence.

All BACKEND_* states mean that LearnerAI does not possess valid native validation evidence.

## Failure consistency

The current upstream single-file CLI returns a nonzero exit code when its failed flag is true.

These combinations are therefore protocol errors:

    exit_code == 0  and failed == true
    exit_code != 0  and failed == false

A malformed JSON document is also a protocol error.

A timeout is a backend timeout, not a script rejection.

A process crash with no usable JSON is a process error, not a script rejection.

## Fixture matrix

Protocol fixtures live under:

    LearnerAI/Compiler/tests/fixtures/native_backend/protocol/

Current cases include:

- valid clean JSON;
- valid native rejection;
- malformed JSON;
- missing findings;
- finding-count mismatch;
- non-object finding;
- unknown severity;
- unknown confidence;
- missing span coordinate;
- negative span coordinate;
- reversed span;
- non-integer span coordinate;
- diagnostic path mismatch;
- failed=true with exit code 0;
- failed=false with nonzero exit code;
- stderr-only diagnostic text.

Process-boundary tests additionally cover:

- timeout;
- backend process launch failure;
- missing executable;
- project version mismatch;
- backend commit mismatch;
- Python version mismatch.

The tests assert the distinction between REJECTED and every BACKEND_* state.

## Staging rule

Validation must operate on a staged generated artifact.

    compile -> stage -> native validate -> promote on success

A failed or unvalidated generated artifact must not overwrite a previously valid artifact.

This also prevents the native validator from accidentally operating on an old generated file while the compiler is testing a new source change.

## Current implementation status

Implemented:

- typed result models;
- backend lock file;
- isolated subprocess runner;
- backend identity checks;
- Python version check;
- timeout handling;
- protocol parsing;
- diagnostic normalization;
- artifact hashing;
- deterministic diagnostic IDs;
- protocol fixture matrix;
- process failure tests.

Current local verification:

    38 tests passed

No GitHub Actions workflow run exists for the latest adapter commits, so that result is local verification only.

## What remains deliberately outside the backend

Do not move these concerns into the native adapter:

- demand creation;
- persistent strategy;
- ownership;
- capability modeling;
- pending lifecycle semantics;
- action/witness separation;
- completion/release logic;
- cancellation/obsolescence;
- dependency graphs;
- compiler teaching diagnostics;
- runtime behavioral claims.

Those remain LearnerAI's semantic layer or AoE2 runtime territory.
