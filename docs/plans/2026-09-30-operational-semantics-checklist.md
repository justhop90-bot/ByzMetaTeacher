# Operational Semantics Layer Checklist

## IR
- [x] Define OperationalLoopContract.
- [x] Define observation, stage, guard, request, control-reference, and recovery types.
- [x] Preserve UNKNOWN versus FALSE.
- [x] Make request issuance distinct from completion.
- [x] Make operational-plan ordering deterministic.

## Semantic validation
- [x] Validate all stage observation references.
- [x] Validate admission presence.
- [x] Validate request shape.
- [x] Reject timing-only re-observation.
- [x] Require fresh retry admission.
- [x] Preserve demand ownership through recovery.
- [x] Validate domain/request compatibility.

## Domain projections
- [x] SemanticDemand projection.
- [x] Native attack-plan projection.
- [x] Typed AttackExecution lifecycle projection through the existing attack_plan channel; nested native emission remains optional and unchanged.
- [x] DUC execution-plan projection.
- [x] Escrow release/policy projection.
- [x] Goal references.
- [x] Strategic Number references.
- [x] Timer references.
- [x] Production pending protection.
- [x] Research pending protection.

## Compiler integration
- [x] Export operational IR from Compiler.ir.
- [x] Export validators and builders from Compiler.semantic.
- [x] Run operational validation in _compile_ir_parts.
- [x] Merge domain-specific execution plans before validation.
- [x] Keep native emission unchanged.

## Verification
- [x] Add focused operational IR tests.
- [x] Add attack and DUC adapter tests.
- [ ] Confirm current-head compiler workflow completes.
- [ ] Confirm native zero-findings on current-head compiler fixtures.
- [ ] Confirm cross-platform determinism on current head.

## Follow-on repair: typed attack lifecycle bridge

- [x] Project AttackExecution into the operational control loop.
- [x] Preserve the persistent attack objective as the operational demand.
- [x] Treat target/capability state as compiler-policy observations only.
- [x] Reuse DUC identity recovery for DUC_TARGETED execution.
- [x] Keep native emission limited to AttackExecution.native_plan.
- [x] Keep one public attack_plan channel.
- [x] Add focused adapter and compile-path regression coverage.
