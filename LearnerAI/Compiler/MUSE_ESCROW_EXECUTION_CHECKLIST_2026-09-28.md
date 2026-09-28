# MUSE Escrow Execution Checklist — 2026-09-28

Base: `main` at `dca0458986d0e50e2ae26889d89f863a3c2ff923`
Working state: merged compiler escrow threading/validation seam; executable release lowering remains open

This checklist is the promotion gate for the escrow/resource-control tranche. It distinguishes native engine facts, community practice, compiler policy, and still-open runtime questions. Community repetition is not promoted to engine truth without native evidence.

## Authority cross-reference

| Evidence | What it establishes | Compiler use |
|---|---|---|
| AIRef Commands Index — [set-escrow-percentage](https://airef.github.io/commands/commands-index.html) | Escrow percentage is a native Action operating on a resource type. | Native command identity and arity. |
| AIRef Commands Index — `release-escrow`, `can-*-with-escrow` | Release and escrow-aware feasibility are distinct native surfaces. | Do not collapse policy, balance release, and feasibility. |
| UserPatch Patch Notes — [EscrowState](https://airef.github.io/tables/up-patch-notes.html) | `escrow-included` sees (T); `escrow-deducted` sees (T-E); ordinary commands are escrow-deducted; UP commands can select the state. | Exact affordability/resource-view formula and execution-mode compatibility. |
| JackkelDragon AoE2DE_AIBuilder — [builder upgrades.per](https://github.com/JackkelDragon/AoE2DE_AIBuilder/blob/master/AI%20Libraries/builder%20upgrades.per) | Repeated executable idiom: `can-research-with-escrow` followed by `release-escrow` and ordinary `research`; escrow thresholds are separately released. | Strong community corroboration for release-before-ordinary-action ordering. |
| Andygmb AoE2 AI Script corpus — [gist](https://gist.github.com/Andygmb/1e3a6d9d444b2dfa8c40) | Same release-before-research pattern appears across multiple civilization-specific scripts; percentage reset is separately expressed where needed. | Independent corroboration; not engine proof. |
| Repository forensic record — `forensics/AEGIS-Layer1-Hostile-Engine-Test/ENGINE_TEST_CHECKLIST.md` | Same-pass visibility and ownership transfer are separate proof obligations; no universal fairness scheduler is assumed. | Prevents accidental promotion of same-pass mutation into ownership semantics. |

## Promotion checklist

### A. Mutation ordering

- [x] Reserve/policy mutation is distinct from escrow-balance release.
- [x] `set-escrow-percentage(r, 0)` is never treated as `release-escrow(r)`.
- [x] For a non-escrow action, the semantic execution contract requires release before consumption.
- [x] Same-rule order is represented explicitly by rule order plus within-rule action order.
- [x] A release followed by an ordinary action is the canonical community shape.
- [ ] Native DE same-pass visibility of `release-escrow -> ordinary action` has a direct engine proof. This remains an evidence gate, not a compiler assumption.

### B. Ownership

- [x] Every escrow contract has one semantic owner.
- [x] Native escrow balance itself is not treated as an ownership token.
- [x] Percentage policy is not used as ownership identity.
- [x] Two active escrow contracts may not claim the same resource for different semantic owners without an explicit handoff layer.
- [x] Transient action-exclusion arbitration is kept separate from escrow ownership.
- [x] Operation owner must match the contract owner.

### C. Lifetime

- [x] Escrow balance lifetime and percentage-policy lifetime are separate.
- [x] Terminal paths are explicit release or consumption.
- [x] A policy reset after release is cleanup, not reacquisition.
- [x] Consumption after release is rejected as a stale lifecycle.
- [x] Release after consumption is rejected.
- [ ] Starvation/emergency release semantics have a direct native/runtime proof.
- [ ] Explicit multi-owner handoff semantics have a direct native/runtime proof.

### D. Acceptance fixtures

- [x] Two-owner same-resource hostile case.
- [x] Non-escrow release-before-consume, same rule.
- [x] Reversed same-rule order rejection.
- [x] Escrow-aware consumption without release.
- [x] Post-release stale consumption rejection.
- [x] Policy reset after release accepted as cleanup.
- [x] Operation owner mismatch rejection.
- [ ] Native artifact fixture proving actual same-pass release visibility.
- [ ] Native artifact fixture proving competing-owner behavior under the game engine.

## Compiler invariants implemented by this tranche

1. A non-escrow action cannot consume an escrow-protected balance until the release operation is earlier in the executable order.
2. An escrow-aware action may consume the protected balance without release because its native resource view explicitly includes escrow.
3. Release is terminal for the current semantic escrow contract. A later consumption requires a new acquisition/contract identity.
4. Setting escrow percentage to zero does not terminate balance lifetime.
5. Every executable escrow operation must identify the same semantic owner as its contract.
6. Resource contention is rejected before emission when two active escrow contracts are owned by different semantic identities.
7. The compiler does not claim that these static contracts prove native same-pass engine behavior.

## Non-goals

This tranche does not implement a commodity optimizer, starvation scheduler, automatic emergency arbitrator, or UP `EscrowState` action lowering. Those require separate native proof. In particular, no scheduler is invented merely because humans noticed that several resource demands can conflict and immediately became tempted to build an economic operating system.
