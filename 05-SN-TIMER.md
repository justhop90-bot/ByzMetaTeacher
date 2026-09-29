# 05 — Strategic Number / Timer versioned inventory @ `cd923b5a`

Catalog version `STRATEGIC_NUMBER_CATALOG_VERSION="airef-de-2026-04-29-v1"` (`primitives/strategic_number_catalog.py:11`);
inventory `docs/reference/inventories/airef-strategic-number-inventory.json` (`version_filter="de == 1"`,
`strategic_number_count=171`, `unfiltered=313`, fetched `2026-04-29T08:59:30Z`; loader enforces DE-filter + count).
Allocator `ALLOCATOR_VERSION="native-storage-v5"`, manifest v4 (`runtime_binding:31-33`).
Support enum `primitives/native_binder.py:32-38`; interaction support `EVIDENCE_ONLY/ENGINE_SEMANTICS_MAPPED/OPEN`
(`native_controller_interactions:76-80`). Version families AOK/TC/WK/DE/UP.

## 1. Namespaces + allocation (ENGINE GUARANTEE for shape)

SN: namespace `0..511` (`SN_NAMESPACE=frozenset(range(512))`); DE-documented 171; compiler candidates 340
(`512−171−{511}`, top `506..510`); reserved 511 never allocated (skipped + rejected);
SN value int32 `−2147483648..2147483647` clamped (`ir/strategic_number:10-11`); constant operand `−32768..32767`;
compiler-owned SN initial `−32768..32767`; numeric target `0..511`; allocation DESCENDING highest-free-first;
requires explicit `StrategicNumberInventory` + non-blank `why_not_goal`, role forced `PERSISTENT_STATE`;
manifest binding with `request_contract{role,stability_key,why_not_goal,native_contract_id}` +
`provenance{inventory_sha,request_fingerprint}` (SHA256 of canonical request).
Timers: `1..50` ascending-first-free; `TimerRequest{request_id,initialization_policy,stability_key,role=EXECUTION_MEMORY}`,
purpose `timer:{name}`; `TimerSlot{id,role,provenance_id,initialization_policy}`, default `DISABLE_BEFORE_FIRST_USE`;
emission `(defconst <name> <id>)` + `(disable-timer <name>)`. Abstract machine DISABLED/RUNNING/TRIGGERED
(`test_timer_semantics:11-81`) is compiler policy, NOT engine proof.

## 2. Command contracts

- `set-strategic-number (SnId Value)` Action 2 args — `ENGINE_SEMANTICS_MAPPED` (generic shape; per-SN effects for 157/171 unmapped). Control-plane Action-only vocabulary. TEST `test_native_control_plane:106-181`.
- `strategic-number (SnId cmp Val)` Fact 3 args — `ENGINE_SEMANTICS_MAPPED`.
- `up-modify-sn (SnId mathOp Val)` Fact/Action 3 args — `ENGINE_SEMANTICS_MAPPED` (typed math core). 12 operators `= + - * / z/ mod min max neg %* %/`; `/` nearest-int, `z/` floor, `mod=a−trunc(a/b)·b`, `%*=trunc(a·b/100)`, `%/=trunc(a·100/b)`, int32-clamped (compiler contract from AIRef/UP, not silicon proof). Fact-position use REJECTED (`native_control:227-230`). Diagnostics SNSEM-001..009 (arity/operator/prefix/literal/range/zero-divisor/missing-dep/target/future-same-rule-dep); constant zero-divisor at parse, dynamic at evaluation; future same-rule read-before-write ERROR. TEST all 12 ops + neg-div + zero-divisor; fixture `strategic_number.per` (all c:/g:/s: domains, 32-element rule limit).
- `up-compare-sn` Fact 3 args (schema arg0 quirk labels GoalId type Sn — cited verbatim) — `EXECUTABLE_SAFE` (only SN command at this level). 6 compare ops; `c:` optional. TEST `:230-343`; SN-264 exact-equality consumer (`registry:1017-1087`).
- `up-compare-goal` / `up-modify-goal` — `SEMANTICALLY_ADAPTED` via head-rewrite reuse. TEST control-plane shared scheduler state.
- Generic `assess_support`: set/strategic-number/up-modify-sn → engine-semantics-mapped; up-compare-sn → executable-safe; 5 timer commands + set-goal/goal/compare/modify-goal/disable-self/up-jump-rule → engine-semantics-mapped; attack-now/up-reset-attack-now → unsupported on generic path (attack reaches SAFE only via dedicated binder).

## 3. Versioned SN table (TYPE=all persistent engine integer; MUTABLE=Y; AUTO-MUTATED=UNKNOWN — no AUTO_MUTATES targets any SN; READABLE=Y; WRITABLE=Y)

| ID | NAME | VALID RANGE (required / allowable) | DEFAULT | VER | CONTROLLER (descriptive only; executable ownership UNKNOWN) | EVIDENCE |
|---|---|---|---|---|---|---|
| 36 | sn-number-attack-groups | 0..Max / Min..Max | 0 | AoE1 | attack-group-control (EVIDENCE_ONLY, COMMUNITY_PRACTICE) | IDIOM + AIRef record |
| 227 | sn-percent-attack-soldiers | 0..100 / Min..Max | 75 | AoC | attack-group-control | IDIOM + AIRef record |
| 42 | sn-number-explore-groups | 0..Max / Min..Max | 0 | AoE1 | exploration-control | IDIOM + AIRef record |
| 18 | sn-total-number-explorers | −1..Max / Min..Max | 4 | AoE1 | exploration-control | IDIOM + AIRef record |
| 167 | sn-initial-exploration-required | 0..100 / Min..Max | 2 | AoE1 | exploration-control | IDIOM + AIRef record |
| 74 | sn-maximum-town-size | 0..255 / Min..Max | 20 | AoE1 | town-size-defense-targeting | IDIOM + AIRef record |
| 20 | sn-enemy-sighted-response-distance | 0..50 / Min..50 | 25 | AoE1 | town-size-defense-targeting | IDIOM + AIRef record |
| 117 | sn-food-gatherer-percentage | 0..100 / 0..100 | 0 | AoE1 | civilian-task-allocation | IDIOM + AIRef record |
| 120 | sn-wood-gatherer-percentage | 0..100 / (Min..Max family) | 0 | AoE1 | civilian-task-allocation | IDIOM + AIRef record |
| 118 | sn-gold-gatherer-percentage | 0..100 | 0 | AoE1 | civilian-task-allocation | IDIOM + AIRef record |
| 119 | sn-stone-gatherer-percentage | 0..100 | 0 | AoE1 | civilian-task-allocation | IDIOM + AIRef record |
| 1 | sn-percent-civilian-builders | 0..100 | 0 | AoE1 | civilian-task-allocation | IDIOM + AIRef record |
| 0 | sn-percent-civilian-explorers | 0..100 | 34 | AoE1 | civilian-task-allocation | IDIOM + AIRef record |
| 2 | sn-percent-civilian-gatherers | 0..100 | 66 | AoE1 | civilian-task-allocation | IDIOM + AIRef record |

Surfaces seeded `native_controller:484-496,497-514,593-606,622-635` (all `status=EVIDENCE_ONLY`; SN-kind surfaces
default `evidence=ENGINE_FACT` by kind-default `:323-340` — a kind-level default, NOT per-SN proof; executable gate
additionally requires controller+surface CONTRACTED + ENGINE_FACT `:187-214`, which none satisfies, proven fail-closed
`test_native_controller_semantics:145-167,104-110`).

SN 264 special (`sn-enable-training-queue`, default 0, 0..15, ver UP) — `OPEN`: head must be `up-compare-sn`,
target ∈ {name,"264"}, op exactly `==`, value int 0..15, canonicalized `(up-compare-sn 264 == N)`, catalog cross-check
else REJECTED → `ProductionQueueCapacityControlEvidence{OPEN, slots=N, documented_total=N+1}`. Total-capacity `N+1`,
provider-idle, queued-vs-training distinctions OPEN (`registry:899-921` raises on OPEN queue/provider state).

Remainder: other 157 DE SNs `NATIVE_KNOWN` (presence only; `bind_strategic_number_accesses` skips unmapped;
unmapped 510 → no binding while mapped binds, `test_strategic_number_semantics:28-53`). 340 candidates: scratch,
UNKNOWN by construction.

## 4. Timers

`enable-timer` Action 2 (TimerId,Value) / `disable-timer` Action 1 / `timer-triggered` Fact 1 (non-consuming read) /
`up-timer-status` Fact 3 (TimerId,cmp,State) / `up-set-timer` Action 4 (constant `c:` TimerId selector REQUIRED
`native_control:301-306`; interval c:/g:/s: with declared-state cross-check) — all `ENGINE_SEMANTICS_MAPPED`.
TEST `test_native_control_plane:24-103,106-181,240-256`; `test_timer_allocation:60-87`; `assert_timer_native:48-58`.
UNKNOWN: owner/rearm/cleanup across passes; triggered-vs-status delta; up-set-timer typeOp matrix beyond selector;
gap-map row "Timers: STORAGE COMPLETE / SEMANTICS PARTIAL".

## 5. Control plane (static gate everything crosses)

`NativeControlPlan{states,rules}` (`ir/native_control:54-69`); states require `GoalSlot|StrategicNumber|TimerRequest`
identifiers (`^[a-z][a-z0-9_-]*$`, no dupes); rules need ≥1 fact; typed-operand g:/s: cross-check; up-set-timer
selector/interval rule; up-jump-rule integer delta; logical-operator arity/nesting. Closed 15-command vocabulary
(set-goal/goal/compare/modify-goal/set-SN/SN/compare-SN/modify-SN/enable/disable-timer/triggered/up-set-timer/
up-timer-status/disable-self/up-jump-rule). Anything else as Action → rejected; non-EXECUTABLE_SAFE/
ENGINE_SEMANTICS_MAPPED → rejected (why generic `attack-now` cannot cross — dedicated binder only). Report only:
no lowering change, no scheduler invention. `ENGINE_SEMANTICS_MAPPED` gate / policy `EXECUTABLE_SAFE` for shape.

OPEN ledger: full 512-SN effect inventory + `Min..Max` bound authority (only spot-verified defaults above are usable);
controller ownership of SN writes (represent descriptively, validate lookups, emit nothing controller-specific);
interaction promotion (manual mapping with ENGINE_FACT + DE-scope + review only; 240/40 MEDIUM/FAST advisory, not a
cost model); attack completion/release/reassessment; timer lifetime/rearm/cleanup; SN264 capacity semantics.
