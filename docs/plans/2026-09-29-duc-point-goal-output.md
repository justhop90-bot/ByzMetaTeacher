# DUC point Goal output lowering

Cross-reference basis:
- AIRef documents `up-get-point <Point> <OutputGoalId>` as a native Action whose OutputGoalId is the first of two consecutive Goals, with valid extended starts 41..15998.
- AIRef's DUC tutorial demonstrates the command in a DUC rule followed by `up-set-target-point`.
- Community `lewisc64/aoe2ai` repeatedly uses `up-get-point` with Goal starts 41+, including 43 and 51, confirming the compiler's typed extended-Goal usage pattern.

Compiler scope:
- Promote only the output-storage binding.
- Use the existing `GoalSpanRequest` + `POINT_PAIR` allocator.
- Validate OutputGoalId at argument index 1 and the 41..15998 / width-2 contract.
- Rewrite only the OutputGoalId during emission.
- Do not infer or compute point coordinates, source-point semantics, or same-pass numeric visibility.

Acceptance:
- Focused DUC registry/binder/emission tests.
- Native DUC zero-findings fixture.
- Full Compiler regression, 9-way determinism, snapshot comparison, and aggregate verification gate.
