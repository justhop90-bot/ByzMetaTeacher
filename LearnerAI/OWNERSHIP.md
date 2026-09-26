# Ownership Matrix

Ownership answers who is responsible for the semantic truth represented by a state or fact.

| State or fact | Owner | Typical readers | External writers |
|---|---|---|---|
| Engine configuration | Engine | all relevant modules | none |
| Strategic posture | Strategy | all domains | Strategy |
| Strategic demand | Strategy | relevant domain | Strategy |
| Resource allocation | Economy | Strategy/domains | Economy |
| Construction lifecycle | Construction | Strategy/Engineering | Construction |
| Production lifecycle | Production | Strategy/Military/Engineering | Production |
| Enemy observation | Information | Strategy/Military/Economy | Information |
| Threat interpretation | Information | Strategy/Military | Information |
| Military posture | Strategy | Military | Strategy |
| Military execution | Military | Strategy/Engineering | Military |
| Completion meaning | owning domain | Strategy/Engineering | owner |
| Diagnostic interpretation | Engineering | humans/compiler | Engineering |

## Ownership rules

One semantic owner per persistent state variable.

Multiple readers are normal.

Competing writers require explicit transition semantics. Accidental source-order overwrites are defects.

A domain may consume another domain's state but should not mutate the owner's private state.

A release rule must explain what proved completion and what happens afterward.

Transient arbitration is not strategic ownership.

## State-entry test

Before adding a goal, strategic number, timer, claim, stage, or latch, ask:

1. Can current engine facts express the answer?
2. Can an existing demand express it?
3. Can rule order provide the needed precedence?
4. Is genuine multi-pass memory required?
5. Is there real resource or capability contention?
6. Does removing the state remove actual control capability?

If the first three are enough, prefer not adding state.

## Failure and invalidation

Execution failure changes timing, not strategic truth.

Strategy invalidation can destroy a strategic demand.

Capability loss can destroy a local execution claim while leaving the demand alive.

Finished execution state must be released.

An owner that can never release its state is an open loop.
