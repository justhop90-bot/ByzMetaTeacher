# Native DE Same-Pass Escrow Visibility Checklist

> **For agentic workers:** Use this checklist to track the repository-owned specification and evidence boundary. DE runtime execution is external to the compiler repository and remains user-owned.

**Goal:** Make the `release-escrow -> ordinary research` same-pass question a fully specified, machine-checked evidence gate without promoting it to engine truth until DE runtime evidence exists.

**Architecture:** Static compiler semantics remain responsible for ordering and fail-closed unknowns. The runtime experiment is represented as a capture-ready oracle candidate under `docs/reference/oracles/candidates/`. A dedicated Compiler unittest checks that the candidate, trace schema, transition model, and promotion boundary cannot silently drift.

**Tech Stack:** Markdown, JSON Schema Draft 2020-12, Python unittest, existing Compiler test discovery.

## Global constraints

- Runtime execution against DE is not performed by the compiler test suite.
- The current native fact remains OPEN until populated DE observations pass the oracle.
- The tested action family is only ordinary `research`.
- `release-escrow` is the only release operation under test.
- `set-escrow-percentage`, UP `EscrowState`, starvation/emergency release, ownership handoff, build, train, and age-up are outside this gate.
- Static compiler/parser acceptance is evidence for emitted syntax only; it is not runtime timing evidence.
- Candidate artifacts are never promotion evidence until populated from an actual DE run.

## Cross-reference matrix

| Concern | Authoritative repository artifact | Role |
|---|---|---|
| Experiment specification | `docs/plans/2026-09-28-native-escrow-same-pass-visibility.md` | Full experiment design, variants, trace fields, failure taxonomy |
| This implementation checklist | `docs/plans/2026-09-28-native-escrow-same-pass-visibility-checklist.md` | Repository implementation and evidence gate |
| Capture-ready oracle | `docs/reference/oracles/candidates/escrow-same-pass-research.native.json` | Unverified runtime candidate |
| Oracle schema | `docs/reference/oracles/escrow-same-pass-research.schema.json` | Portable artifact shape |
| Oracle boundary | `docs/reference/oracles/README.md` | Candidate versus native-observation promotion rules |
| Native unknown | `native_unknowns.md` | Same-pass visibility remains OPEN |
| MUSE execution gate | `LearnerAI/Compiler/MUSE_ESCROW_EXECUTION_CHECKLIST_2026-09-28.md` | Promotion status and runtime gate |
| MUSE research repair | `LearnerAI/Compiler/MUSE_ESCROW_RESEARCH_REPAIR_2026-09-28.md` | R3 ordering / R2 affordability boundary |
| MUSE next frontier | `LearnerAI/Compiler/MUSE_NEXT_IMPLEMENTATION_CHECKLIST_2026-09-28.md` | Remaining escrow tranche |
| Compiler implementation map | `implementation_map.md` | Exact module/test ownership |
| Static escrow semantic tests | `LearnerAI/Compiler/tests/test_escrow_resource_control.py` | Compiler ordering/ownership/lifetime contract |
| Release-only native acceptance | `LearnerAI/Compiler/tests/assert_escrow_native.py` | Parser/native artifact acceptance only |
| Oracle specification regression | `LearnerAI/Compiler/tests/test_escrow_same_pass_oracle_spec.py` | Machine-checks this checklist/candidate |

## Repository-owned implementation

### Specification

- [x] Exact positive/reversed/later-pass experiment is specified.
- [x] Five fixture variants are fixed:
  - `NORMAL_BASELINE`
  - `ESCROW_BLOCKED_NO_RELEASE`
  - `ESCROW_SAME_PASS_POSITIVE`
  - `ESCROW_SAME_PASS_REVERSED`
  - `ESCROW_LATER_PASS_CONTROL`
- [x] Research status model is fixed to `1 -> 2 -> 3), with `2 -> 2` and `3 -> 3` allowed.
- [x] Required controller/world-state trace fields are fixed.
- [x] Terminal failure precedence is fixed.
- [x] Ten fresh runs per variant are required for promotion.
- [x] Same-pass proof is restricted to ordinary research.

### Oracle artifact

- [x] Dedicated JSON Schema exists.
- [x] Candidate artifact exists under `docs/reference/oracles/candidates/`.
- [x] Candidate explicitly remains UNVERIFIED.
- [x] Candidate contains all five variants and their expected terminal outcomes.
- [x] Candidate contains the required status transition model.
- [x] Candidate contains required trace fields.
- [x] Candidate contains the promotion boundary.
- [x] Candidate contains repository cross-references.

### Static compiler verification

- [x] Existing release-only compiler emission test remains authoritative for native syntax.
- [x] Existing escrow semantic tests remain authoritative for ordering/ownership/lifetime.
- [x] New unittest machine-checks the runtime oracle specification.
- [ ] No compiler test claims actual DE same-pass timing.

## User-owned DE runtime gate

These are deliberately not checked off by repository CI.

- [ ] Freeze exact DE build, patch, AI layer, platform, and scenario.
- [ ] Run `NORMAL_BASELINE`.
- [ ] Run `ESCROW_BLOCKED_NO_RELEASE`.
- [ ] Run `ESCROW_SAME_PASS_POSITIVE`.
- [ ] Run `ESCROW_SAME_PASS_REVERSED`.
- [ ] Run `ESCROW_LATER_PASS_CONTROL`.
- [ ] Repeat each variant for ten fresh runs.
- [ ] Populate raw traces with the required fields.
- [ ] Populate assertion results from observed runtime state.
- [ ] Record one terminal result per run.
- [ ] Reject any non-PASS run.
- [ ] Reject byte-identical-input nondeterminism.
- [ ] Promote only after all variant/run gates pass.

## Native promotion gate

The repository must continue to report:

`NATIVE_ESCROW_SAME_PASS_VISIBILITY = OPEN`

until the populated native observation proves all of the following:

1. escrow starts at 75 gold while ordinary research is not affordable;
2. `release-escrow gold` reduces escrow to zero;
3. ordinary `research ri-loom` starts in the same executable rule/pass after the release;
4. research enters status `2`;
5. exactly the research cost is consumed;
6. status later reaches `3`;
7. reversed action order does not start research before release;
8. later-pass release/control succeeds;
9. the blocked-no-release control remains blocked.

Only then may the repository promote the narrow native statement:

> On the tested DE build, `release-escrow <Resource>` is visible to a later ordinary `research` action in the same executable rule/pass, and action order is material.

Do not generalize this promotion to another action family.
