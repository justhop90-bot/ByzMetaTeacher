# DUC group-size Goal output lowering

Goal: promote the already-contracted `up-get-group-size` width-1 Goal output from semantic-only state into the normal native storage/binding/emitter path.

Contract:
- Native syntax is `(up-get-group-size <typeOp> <GroupId> <OutputGoalId>)`.
- GroupId is restricted to 0..19 by the existing DUC group contract.
- OutputGoalId is a single persistent Goal in 1..16000.
- The compiler uses an existing `GoalSlotRequest` with role `NATIVE_OUTPUT`; no new storage allocator is introduced.
- The native output argument is rewritten deterministically from the allocated GoalSlot.
- The repair does not infer the group size value, group membership, or runtime group persistence beyond existing semantic group contracts.

Verification target:
- Focused DUC binder/registry/emission tests.
- Updated native DUC zero-findings fixture covering search-state width-4 plus group-size width-1 output allocation.
- Full Compiler regression, native-support determinism, snapshot comparison, and Compiler verification gate.
