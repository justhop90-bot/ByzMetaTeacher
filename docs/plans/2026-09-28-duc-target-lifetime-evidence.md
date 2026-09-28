# DUC Target Lifetime Evidence Record

Date: 2026-09-28
Branch: duc-native-transition-contracts

## Mapped native facts

- `up-set-target-object` is a native Fact/Action.
- UserPatch documents that an out-of-range object index makes `up-set-target-object` return false as a Fact.
- The native target contract therefore exposes:
  - `supports_fact = True`
  - `returns_false_on_invalid_index = True`
  - `failed_action_preserves_previous_target = None`

These fields deliberately separate documented Fact failure semantics from unresolved Action failure effects.

## Compiler policy

The compiler records target Fact outcomes conservatively:

- Static source/list absence or an index outside the native list capacity is `GUARANTEED_FALSE`.
- An in-range index remains `RUNTIME_DEPENDENT` because capacity does not prove that a runtime object exists at that position.
- A runtime-dependent target Fact does not fabricate a selected target in the static state.

For a failed `up-set-target-object` Action with an existing target, the compiler preserves the previous target in its static state but emits a warning identifying the native failure effect as unresolved. This is preservation of compiler knowledge, not a claim that the engine necessarily preserves the target.

## Open native boundaries

The following remain `OPEN`:

- exact failed-Action target effect after an invalid `up-set-target-object`;
- target lifetime after `up-filter-distance`, `up-filter-exclude`, `up-filter-garrison`, `up-filter-include`, or `up-filter-range`;
- target lifetime after query/type/class reset;
- target lifetime after focus-player remote-index reset;
- target lifetime after `up-clean-search`;
- target lifetime after `up-remove-objects` where static object matching cannot prove the selected object is removed or preserved.

Community usage patterns may support the existence of persistent target state, but they do not promote these lifetime claims to engine semantics.

## Verification intent

Hostile regressions must keep the distinction between:

`search-index reset != target invalidation`

and:

`list mutation != proof that the selected object died`.

Any future promotion requires direct native evidence or an explicitly scoped engine observation.
