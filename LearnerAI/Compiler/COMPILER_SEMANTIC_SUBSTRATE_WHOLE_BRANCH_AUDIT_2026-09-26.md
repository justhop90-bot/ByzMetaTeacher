# Compiler Semantic Substrate Whole-Branch Audit
Date: 2026-09-26
Base: 471f5affdc11ced3c493b448512a9a9cbdc9c0f0
Audited head: bee6066109775c3002c4f5234f6ebd8472538a68
Branch: compiler-semantic-substrate-phase0
PR: #51

## Scope
The complete unmerged compiler branch was audited against `main`. At this audit point the branch is 77 commits ahead of `main), with 22 changed files. The review covers the engine-semantic mapping catalog, native evidence/provenance contracts, primitive promotion, runtime storage binding, .per emission, community-engine lifecycle contracts, generated artifact reproducibility, replay schemas, and all focused regression fixtures added by the branch.

## Causal path audited
`native schema -> primitive adapter -> engine semantic mapping -> NativeWitness/NativeStorageUse/PassExecutionConstraint -> promotion -> runtime binding -> lowering -> emitted .per -> native zero-findings -> replay determinism`.

The intended rule remains fail-closed: descriptive evidence may exist without executable promotion; executable promotion requires a contracted native mapping plus native witness/storage/pass contracts actually consumed by lowering.

## Findings repaired

### 1. Completion witness contradiction
The engine-semantic action mappings and community lifecycle contracts used `building-type-count-total` and `unit-type-count-total` as completion witnesses. The compiler explicitly treats total/pending observations as non-completion evidence.

Repair:
- build completion now maps to `building-type-count`;
- train completion now maps to `unit-type-count`;
- lifecycle validation rejects feasibility or pending facts reused as completion witnesses;
- focused tests assert the distinction.

### 2. Evidence-class leakage into executable native contracts
`NativeWitness` and `NativeStorageUse` previously accepted inferred mappings as if they were native facts. That allowed an inferred semantic mapping to support executable promotion.

Repair:
- hard native witness semantics require `DOCUMENTED_FACT`;
- hard native storage semantics require `DOCUMENTED_FACT`;
- benchmark evidence cannot define native execution semantics;
- focused negative tests cover inferred evidence.

### 3. False Goal-span namespace restriction
`NativeStorageUse` hard-coded Goal spans to 41..508 even though the existing AIRef-derived native span contracts legitimately reach the upper Goal namespace.

Repair:
- native Goal-span validation now checks the documented Goal namespace 1..16000;
- command-specific span contracts continue to carry their own precise start bounds;
- native-contract catalog validation now also rejects overlapping Goal spans;
- focused test covers a high Goal span.

### 4. Revalidation-event audit hole
Citation revalidation events could claim one set of changes while their previous/current URLs, locators, hashes, or excerpts implied another.

Repair:
- event construction now validates URL, locator, source-hash, and excerpt-hash deltas against `changes`;
- result classes requiring concrete changes enforce those changes;
- available revalidation results require a current citation identity;
- the test fixture now records its actual URL/locator/source-hash changes.

### 5. Undervalidated engine-managed storage state
`ENGINE_MANAGED_STATE` previously had no complete shape validation branch and could accept unrelated storage kinds.

Repair:
- only FLAG and ESCROW are accepted for engine-managed state;
- invalid state kinds fail closed;
- symbolic storage uses now require a binding purpose.

### 6. Silent unsupported pass semantics
`PassExecutionConstraint` exposed `failure_mode` and `requires_next_pass`, but only `maximum_successes` affected lowering.

Repair:
- unsupported next-pass semantics are rejected during promotion;
- unsupported failure modes are rejected during promotion;
- current executable pass constraints are therefore only those the emitter actually understands;
- focused tests cover both rejection paths.

### 7. Primitive contract-reference hygiene
Primitive contract ID tuples could contain duplicates, and pass constraints attached to a command could exist without being declared by the primitive.

Repair:
- primitive contract references must be unique;
- every pass constraint registered for an action must be explicitly declared by that primitive.

### 8. Focused native-contract fixtures were too shallow
The first implementation tests accidentally exercised promotion failures before reaching the intended lowering failure boundary.

Repair:
- storage and pass-constraint fixtures now retain the complete default primitive catalog;
- mutated build primitives are isolated only at the intended contract seam;
- this preserves the test's diagnostic target and makes red/green behavior meaningful.

## Deliberately partial surfaces
The branch does not claim full executable support for DUC search/list/group state, arbitrary Strategic Numbers, or timer lifecycle lowering. Those structures remain evidence/catalog material until their native state lifetime and binding contracts are wired through promotion and emission. They must not silently become executable merely because the schema contains them.

Repository-wide citation resolution is now contracted for the executable native substrate. The Goal evidence layer is now explicitly split into three native meanings: **ordinary persistent Goal storage**, **extended Goal spans**, and **GoalId parameter ranges**. Ordinary Goal storage is constrained to 1..512, matching AIRef's Goals section; extended spans are shape-specific (2-wide point spans through 15998, 4-wide cost/search/guard spans through 15996); GoalId command parameters remain a separate 1..16000 parameter contract. This prevents the earlier semantic collapse where the 1..16000 parameter range was incorrectly used as a storage-capacity citation. The native catalog binds each storage/parameter contract to a citation with a matching semantic scope, and cross-domain provenance is rejected.

 `CitationRecordCatalog.audit()` now mechanically checks the repository catalog for unused records, duplicate source locations, stale citation states, and weak locators. The catalog audit found no unused, duplicate, or stale records. It found four weak entries: the three command citations used the generic AIRef command-details URL, and the Goal-storage citation used the broad `Goals` heading instead of the exact `Goals: 1 to 16,000` table entry. Those four records were strengthened to command-specific AIRef URLs and an exact table-entry locator. Focused regression tests cover each repaired finding plus synthetic detection of unused, duplicate, stale, and weak records.

 `CitationRecordCatalog` resolves every `AIRefProvenance.citation_id` attached to native witnesses, storage uses, and pass constraints. Missing citations fail closed; BROKEN, REVIEW_REQUIRED, UNAVAILABLE, CANDIDATE, and SUPERSEDED citation states are not promotable. The default catalog contains the five currently executable AIRef citations, with source locators and evidence excerpts. `NativeContractCatalog.validate_all_provenance()` is part of catalog construction, so an invalid citation cannot reach primitive promotion or lowering.

## Verification state
The fresh Compiler Tests workflow for the CitationRecord implementation completed successfully with **351 tests**, including native zero-findings acceptance and cross-platform native-support determinism. The generated Basilisk fixture remained reproducible.

The current Basilisk Validator workflow still fails at the established baseline assertion `[Pikeman] action boundary must re-check the package capability witness` in `validation/basilisk-validator.js`; the validator failure is on the pre-existing validator baseline and is independent of the compiler CitationRecord resolution work.

No runtime gameplay result is used as proof of compiler correctness. Runtime remains a strategy-quality grading layer only.
