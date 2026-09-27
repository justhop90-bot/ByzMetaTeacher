# Strategic Number Semantics Design

**Date:** 2026-09-26
**Scope:** Generic AoE2DE `.per` compiler only. No strategy client or Basilisk behavior is introduced by this tranche.

## Goal

Represent and validate the minimum native Strategic Number mutation semantics needed to compile Naga-class recurrent `.per` faithfully: typed operands, native math operators, persistent same-pass visibility, cross-state dependencies, and native-parser acceptance.

## Engine contract

The compiler models the native UserPatch/DE contract, not a host-language approximation:

- Strategic Numbers use IDs 0-511 and persistent integer values.
- `set-strategic-number <SnId> <Value>` is direct assignment.
- `up-modify-sn <SnId> <mathOp> <Value>` mutates only the target SN.
- The operand domain is selected by the operator prefix: `c:` constant, `g:` Goal, `s:` Strategic Number.
- Supported `mathOp` values are `=`, `+`, `-`, `*`, `/`, `z/`, `mod`, `min`, `max`, `neg`, `%*`, `%/`.
- `min` stores the lesser value; `max` stores the greater value.
- `/` rounds to the nearest integer according to the documented engine behavior; `z/` truncates downward. `%*` computes `(current * operand) / 100` with truncation; `%/` computes `(current / operand) * 100` with truncation.
- The target SN is the only mutated state. Referenced Goal/SN values are reads/dependencies.
- Persistent state mutations are immediately visible to later actions and later rules in the same scheduler pass. Rule-guard facts are evaluated before that rule's RHS actions.
- Cross-pass visibility is persistent rather than snapshot-based.
- Goal/SN values are signed 32-bit engine integers. Literal/defconst constant operands are constrained to the documented 16-bit constant range (-32768..32767); dynamic Goal/SN operands use the full signed 32-bit state range.
- Constant division/modulo by zero is a compile-time semantic error. Dynamic zero divisors are a runtime scheduler error because their value is not statically known.

## Typed IR

`LearnerAI/Compiler/ir/strategic_number.py` defines:

- `StrategicNumberMathOp`
- `StrategicNumberOperandKind`
- `StrategicNumberOperand`
- `StrategicNumberMutation`
- `StrategicNumberDependency`
- `StrategicNumberExpression`
- diagnostic enums/classes for structural and semantic rejection.

The typed mutation retains the target SN, operator, operand domain/value, source location, rule order, and action order. It never collapses `c:`, `g:`, and `s:` into an untyped string.

## Semantic lowering

`LearnerAI/Compiler/semantic/strategic_number_semantics.py` parses supported native expressions into typed IR, validates arity, domains, operator names, integer syntax, constant bounds, and statically provable zero divisors, and exposes a deterministic evaluator for scheduler tests.

`up-modify-sn` creates two semantic views:

1. target mutation/write;
2. operand dependency read when the operand domain is Goal or Strategic Number.

Dependency analysis is explicit. A same-rule dependency on a later RHS writer is rejected because RHS actions execute sequentially. A cross-rule dependency resolves through persistent state in effective rule order. Absence of an explicit writer is not itself an error because the engine supplies initialized/default persistent state.

## Persistent-state integration

`persistent_state.py` recognizes `up-modify-sn` as a target SN writer and records its source dependency metadata. Existing Goal/SN/Timer source-order reporting remains intact. SN-specific dependency diagnostics are produced by the typed semantic pass so ordinary state-order diagnostics are not overloaded with expression parsing.

## Scheduler integration

`PassScheduler` gains Goal/SN stores and recognizes:

- `set-strategic-number`
- `up-modify-sn`
- `strategic-number`
- `up-compare-sn`

SN mutations are committed immediately in RHS order. A subsequent rule in the same pass therefore reads the new value. The scheduler uses the same typed operator evaluator as static semantic tests.

## Native validation

A dedicated CI fixture generator emits representative native rules covering every supported operator and each operand domain. `assert_native_zero.py` validates the generated artifact with the pinned `aoe2-ai-parser` validator. The workflow records the fixture as native-validation evidence and fails closed on any parser finding.

## Hostile fixtures

The suite covers:

- all operators and all operand domains;
- same-rule sequential mutations;
- cross-rule same-pass visibility;
- Goal-to-SN and SN-to-SN dependency edges;
- later-writer dependency rejection;
- invalid type prefixes;
- invalid operators;
- wrong arity;
- malformed numeric literals;
- constant divide/modulo by zero;
- dynamic divisor acceptance;
- signed values;
- min/max direction;
- `/` versus `z/`;
- `%*` and `%/`;
- 32-bit boundary rejection;
- target-only write semantics.

## Non-goals

This tranche does not implement DUC/search semantics, strategy policy, XS, generic Goal arithmetic beyond reading Goal operands from `up-modify-sn`, or a universal native `.per` interpreter. It adds only the SN substrate required by the recurrent compiler model.
