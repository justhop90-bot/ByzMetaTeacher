# Compiler false assumptions (unsupported or too strong)
1. Fixture-only DUC/SN/timer tests imply emission coverage — they don't (synthetic EffectiveRule).
2. `test_pending_and_total_state_cannot_be_completion_witness` as engine truth — it is
   COMPILER POLICY without runtime proof (G-04).
3. Source-order visibility assumed uniform — lifecycle accesses are excluded from
   source_order.py by design (G-05).
4. `fires_guaranteed` path implies provable firing — always False; no rule fires guaranteed.
5. `_compiler_owned_state_identifiers` prefix-inference equals binding truth — string heuristic.
6. Duplicate `building-available` key + escrow-variant observation primitives imply
   coverage — second wins / no adapters.
7. NATIVE_TYPED promotion assumed semantically useful — registry vs binder gates disagree.
8. Strategy Barry-lowering assumed policy-neutral — Byzantine token sets baked into
   `_validate_native_operand`.
