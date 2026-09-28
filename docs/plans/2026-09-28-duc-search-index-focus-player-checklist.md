# DUC Search-Index Focus-Player Lifecycle

Date: 2026-09-28
Base lineage: PR #74 target-data head `17e0930c3c01055f4bfc53d3b2f312cf75f9be9b`

## Native contract

- [x] AIRef/UserPatch evidence establishes that `sn-focus-player-number` drives `focus-player`.
- [x] UserPatch documents that a changed focus player resets the remote search-index offset.
- [x] The reset is modeled as equivalent remote-index invalidation, without touching LOCAL search-index state.

## Compiler state

- [x] Remote search index starts with native focus-player default `0`.
- [x] Remote index stores focus-player signature.
- [x] Remote index stores provenance of the latest focus-player mutation.
- [x] New reset reason: `FOCUS_PLAYER_CHANGED`.
- [x] `set-strategic-number sn-focus-player-number <literal>` updates the focus signature.
- [x] Constant `up-modify-sn sn-focus-player-number ...` reuses the existing Strategic Number evaluator.
- [x] Dynamic Goal/SN operands remain UNKNOWN rather than being evaluated speculatively.
- [x] Proven unchanged assignments update provenance without churning the remote cursor.
- [x] Search operations expose the focus signature/provenance that governed their index state.
- [x] Cross-pass persistence preserves focus signature/provenance.
- [x] Branch joins clear divergent focus identity and provenance.

## Hostile regression coverage

- [x] Same-rule focus mutation resets a later remote search.
- [x] Constant `up-modify-sn` assignment resets the remote search.
- [x] Same-value assignment does not reset the remote search.
- [x] LOCAL searches are unaffected.
- [x] Dynamic Goal-driven mutation resets the remote search but leaves focus identity UNKNOWN.
- [x] Focus provenance persists across pass advancement.
- [x] Divergent control-flow paths produce ambiguous focus state and clear provenance.
- [x] Initial native default focus is recorded as `0`.

## Remaining search-index gaps

- [ ] Exact post-search cursor advancement remains unmodeled because the engine-side returned offset needs native/runtime evidence.
- [ ] Exact focus-player value provenance for arbitrary dynamic expressions is intentionally UNKNOWN until the broader Strategic Number state graph is connected to DUC.
- [ ] Search-index mutations from every native focus-player-equivalent mechanism are not yet exhaustively inventory-checked.
