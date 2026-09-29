# Strategy runtime observation closure slice

This tranche promotes only native facts already supported by the compiler:
- `up-can-search` -> `DUC_SEARCH_AVAILABILITY`
- `can-afford-building-with-escrow`, `can-afford-unit-with-escrow`, `can-afford-research-with-escrow`, `can-build-with-escrow`, `can-research-with-escrow` -> `ESCROW_CAPABILITY`

`can-train-with-escrow` remains `UNIT_CAPABILITY` because its existing semantic identity is the train-capability observation. `attack-now` remains an Action and is explicitly rejected from strategic observation binding.

No new engine fact or runtime claim is introduced. Native DUC search state, attack controller state, and escrow same-pass/runtime semantics remain OPEN.
