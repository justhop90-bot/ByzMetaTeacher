# Basilisk defconst lifecycle audit findings

Audited controller: `Basilisk/Basilisk.per` on `main`, controller blob SHA `cb09509a1f7b9d8b5d01ed877cc51724f8cc95da`.
Audited inventory: 421 `defconst` declarations across 804 parsed rules.
AIRef schema: `extracted/inventories/airef-command-schema.json`, current checked-in schema inventory reports 385 commands.

## Hard totals

- 421/421 defconst declarations are present in the matrix.
- 16 are unused after declaration. These are the only constants with no rule-level reference.
- 45 are declaration-only in the semantic matrix because their sole post-declaration role is not a lifecycle state writer/reader; the machine-readable JSON preserves the exact command occurrence instead of discarding it.
- 225 classify as CLOSED state/data lifecycles under the command-semantic model: at least one state writer and one reader are present.
- 103 are READ-ONLY. Most are symbolic values, thresholds, timer IDs, or engine-output constants. They are not automatically defects.
- 23 are ENGINE-ONLY. These are predominantly constants supplied to engine actions such as cost-data setup/output or direct engine commands.
- 9 are WRITE-ONLY under the narrow state-reader classification. Several are stage/failure literals or scratch/output goals and therefore require semantic review rather than automatic deletion.
- 16 are UNUSED and are the clearest hygiene debt.

## The 16 genuinely unused declarations

`bt-farm-demand-low`, `bt-farm-demand-medium`, `bt-farm-demand-high`, `bt-farm-demand-very-high`, `bt-siege-tower-max-wall-attempts`, `bt-imperial-food`, `bt-imperial-gold`, `bt-scale-mail-bank-delta-stone-goal`, `bt-chain-mail-bank-delta-stone-goal`, `bt-pikeman-bank-delta-stone-goal`, `bt-elite-skirmisher-bank-delta-stone-goal`, `bt-farm-feudal-emergency-food`, `bt-farm-castle-emergency-food`, `bt-farm-build-wood`, `bt-max-barracks`, and `bt-max-ranges`.

These should not be removed blindly. The farm-demand values, for example, may be obsolete policy remnants; the bank-delta stone goals are more suspicious because the surrounding composite-cost machinery still owns adjacent output goals. The correct repair is to verify each against the current engine command consumers before deleting it.

## Completion-witness audit

The demand/claim/project state families were checked for writer rules that also contain concrete world-state witnesses. The only three state-like writers that lack one of the standard completion witnesses are:

- `bt-siege-tower-approach-watchdog-timer`
- `bt-siege-tower-unload-watchdog-timer`
- `bt-siege-tower-assault-watchdog-timer`

These are timers, not completion-state goals, so the absence of `research-complete`, `unit-type-count`, `building-type-count`, or `current-age` is expected. The actual Siege Tower lifecycle uses timer transitions and DUC execution-state witnesses instead.

No ordinary `*-demand-goal`, `*-claim`, `*-project-goal`, `*-stage-goal`, `*-target-goal`, or `*-commitment-goal` was found to have writers but no concrete completion/witness rule under the audit's standard witness set.

## Invalidation

The matrix records every state writer, including reset-to-zero writes and writers in rules containing failure/backoff/timeout/cancel/crisis/unsafe/lost/reset/retry predicates. This is deliberately conservative: a state transition to another enum value is not mislabeled as an invalidation merely because it is a write.

One important special case is `bt-opening-stage-goal`. Its lifecycle terminates by transitioning to the explicit `bt-opening-stage-complete` value rather than resetting to zero. That is completion, not invalidation.

## Important semantic distinction

The matrix does not treat every `defconst` as a persistent variable. Basilisk uses numeric goals as engine-native storage, but many constants are:

- enum values;
- timer IDs;
- resource thresholds;
- engine-output goal IDs;
- composite-cost scratch/output goals;
- DUC state/failure codes;
- unit/building IDs;
- strategic-number IDs.

Calling every read-only constant a broken lifecycle would be cargo-cult auditing. The matrix therefore preserves command-level evidence so each apparent orphan can be judged by its actual engine role.

## Deliverables

The exhaustive human-readable matrix is in `audit/Basilisk-defconst-lifecycle-matrix.md`.
The machine-readable matrix is in `audit/Basilisk-defconst-lifecycle-matrix.json`.

Neither file modifies `main`; both are on the isolated audit branch `audit/basilisk-defconst-lifecycle-2026-09-23`.
