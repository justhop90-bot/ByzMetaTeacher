# LearnerAI Compiler Research Checklist

Updated after the native-backend research and adapter implementation.

## What the community has already provided

### Native .per parsing and validation

aoe2-ai-parser is the closest existing native tool and should be treated as the backend rather than reimplemented.

Current pinned project identity:

    repository: https://github.com/joerollman/aoe2-ai-parser
    project: aoe2-ai-parser
    version: 0.1.0
    commit: 3dfa2583b7c2ec36b85ccb421ebd0abe9ff276ba
    Python: >= 3.12
    license: GPL-3.0-or-later

The project currently provides native .per parsing, command/fact/action validation, argument and role checks, logical operator arity, rule-length checks, load/package graph analysis, AIRef-backed reference inventories, diagnostics, formatting, and package reports.

We therefore do not need to build:

- a second native .per parser;
- a second command/parameter schema;
- a second native logical-operator validator;
- a second rule-length counter;
- a second load/package graph validator;
- a second AIRef command/object/tech/strategic-number inventory;
- a second native formatter.

### Higher-level AoE2 script compilers

Community projects also demonstrate the broader compiler space.

AgeOfPython provides a Python-like language translated into AoE2 script, with functions, loops, arrays, goals, and AIRef-derived information. It is useful as evidence that a higher-level compilation approach is viable, but it does not replace LearnerAI's deliberately smaller demand/lifecycle teaching model.

lewisc64/aoe2ai provides a higher-level AoE2 AI language which translates structured commands such as training, research, building, conditions, and repeated behavior into .per. It demonstrates that community authors have already attacked source-language ergonomics and code generation.

### Editor and tooling lineage

The older Jvinniec/aoe2-aiscript and KnightThymeTools/aoe2-aiscript projects provide the established editor-tooling lineage: syntax highlighting, completion, signatures, symbols, references, and earlier diagnostics.

These are evidence for the ecosystem's existing editor conventions, not replacement compiler semantics.

### Runtime/native extension work

FLWL/aoe2-ai-module exposes native AI functionality to external runtime code. That is useful precedent for engine integration, but it is not a static compiler backend.

### What this means for LearnerAI

The community has already supplied most of the raw-language machinery.

LearnerAI's differentiated work remains:

    persistent demand
        -> capability
        -> feasibility
        -> engine action
        -> pending state
        -> world-state witness
        -> release
        -> reassess

The compiler should therefore remain a semantic teaching compiler, not become an expensive reimplementation of the AoE2 parser ecosystem.

## Implemented

- [x] Native backend package boundary.
- [x] Typed native validation result models.
- [x] Pinned backend identity.
- [x] Python version verification.
- [x] Subprocess isolation with shell=False.
- [x] Redirected stdin.
- [x] Sanitized Python/proxy environment.
- [x] Temporary backend working directory.
- [x] Bounded backend timeout.
- [x] Strict native JSON parsing.
- [x] Native diagnostic normalization.
- [x] Native severity/confidence validation.
- [x] Source coordinate normalization.
- [x] Artifact-path verification.
- [x] Artifact SHA-256 identity.
- [x] Deterministic native diagnostic IDs.
- [x] Backend failure versus script rejection distinction.
- [x] Staged .per validation before output promotion.
- [x] Protocol fixture matrix.
- [x] Process-failure fixture coverage.
- [x] Compiler --validate-native integration.
- [x] Compiler --native-json normalized result output.
- [x] Compiler integration tests for promotion/rejection/backend failure.

## Next work, in order

### 1. Freeze the backend installation

Goal: make the external validator reproducible on another machine.

- [ ] Create tools/native-backends/aoe2-ai-parser/.
- [ ] Add an isolated Python 3.12 virtual environment.
- [ ] Install the exact pinned backend commit.
- [ ] Add manifest.json containing project version, source commit, and Python version.
- [ ] Record a source distribution/archive SHA-256 in the backend lock.
- [ ] Add a bootstrap/verification script with no automatic upgrade behavior.
- [ ] Test that a version match plus commit mismatch is rejected.
- [ ] Test that a valid pinned installation is accepted.

### 2. Add the golden native contract test

Goal: detect backend protocol drift before compiler semantics are affected.

- [ ] Store one known-valid backend JSON response.
- [ ] Store one known-invalid backend JSON response.
- [ ] Validate the full normalized result structure.
- [ ] Verify diagnostic IDs remain deterministic.
- [ ] Verify upstream human-message wording is not treated as diagnostic identity.
- [ ] Verify backend severity and confidence survive normalization unchanged.
- [ ] Verify malformed protocol remains a backend failure.

### 3. Connect semantic compilation and native diagnostics

Goal: make compiler output explain both semantic and native failures.

- [ ] Keep LearnerAI diagnostics in their own namespace.
- [ ] Keep native backend codes unchanged.
- [ ] Add a combined compiler validation report containing semantic diagnostics, native diagnostics, backend identity, generated artifact hash, and final validation state.
- [ ] Ensure semantic rejection prevents native invocation.
- [ ] Ensure native rejection does not erase the successful semantic result.
- [ ] Ensure backend failure is reported as missing validation evidence, not .per rejection.

### 4. Reuse native package analysis instead of recreating it

Goal: leverage community package knowledge when LearnerAI grows beyond one generated .per.

- [ ] Generate or stage a complete .ai + .per package when the language needs load graphs.
- [ ] Invoke the backend package validator.
- [ ] Consume normalized package diagnostics.
- [ ] Reuse native load/include/reference analysis instead of implementing another graph walker.
- [ ] Keep LearnerAI ownership/dependency analysis separate from native file/package reachability.

### 5. Expand LearnerAI semantic analysis

This is where the project should spend its original engineering effort.

- [ ] Explicit demand ownership.
- [ ] Capability ownership and admissibility.
- [ ] Feasibility/action separation across modules.
- [ ] Pending-state lifecycle beyond the first examples.
- [ ] Completion witnesses that are impossible to fake from pending/total state.
- [ ] Release and cancellation/obsolescence.
- [ ] Dependency chains between demands.
- [ ] Persistent intent under temporary resource failure.
- [ ] Ownership-conflict diagnostics.
- [ ] Dead-end/unfed/blocked/functionally-disconnected/open-loop analysis.
- [ ] Source-order and first-writer/first-consumer analysis for generated artifacts.

### 6. Build the teaching layer

- [ ] Explain why an engine action is not a completion witness.
- [ ] Explain why can-* authorizes but does not prove success.
- [ ] Explain pending versus completed counts.
- [ ] Explain resource arbitration without turning it into a generic manager.
- [ ] Show demand lifecycle traces for Castle, Spearman, Wheelbarrow, and later economic/production behaviors.
- [ ] Add exercises where the learner intentionally creates repeated actions, premature release, impossible witnesses, and ownership conflicts.

## Deliberately do not build

- [ ] No replacement for aoe2-ai-parser's raw .per parser.
- [ ] No replacement native command registry unless LearnerAI needs a teaching-specific subset.
- [ ] No replacement package/load graph validator.
- [ ] No replacement native formatter.
- [ ] No general-purpose Python compiler.
- [ ] No generic scheduler/manager abstraction.
- [ ] No runtime simulation pretending to be AoE2DE.

## Current verification

The current compiler suite contains:

    41 tests

The last clean-checkout run after native compiler integration passed all tests.

GitHub Actions currently has no recorded workflow run for the latest adapter commits, so local test results must not be described as CI verification.

## Research conclusion

The useful discovery was not "someone already built our compiler."

The useful discovery was narrower and more valuable:

the community has already built much of the native language toolchain, so LearnerAI can stop spending effort on that layer and concentrate on the semantic teaching problem it actually exists to solve.
