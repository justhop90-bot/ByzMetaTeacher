# Implementation Workspace

LearnerAI is the build workspace for the new Byzantine player.

The documents here are not the final bot. They define the contracts that executable implementation must satisfy.

## Reserved modules

Engine/
State/
Information/
Strategy/
Economy/
Construction/
Production/
Military/
Engineering/

Each directory begins with focused specifications and source-location guidance. Executable implementation is added only after the relevant behavior has an agreed owner and lifecycle.

## Reserved engineering artifacts

- engine primitive lessons;
- verified AIRef references;
- verified identifiers;
- rule-order diagrams;
- demand/capability/action/witness traces;
- static validation checklists;
- runtime test matrices;
- failure and recovery cases;
- Byzantine-specific behavior traces;
- community-pattern comparisons;
- compiler semantic diagnostics.

## How to use the workspace

Before adding code:

1. Find the source in SOURCE_MAP.md.
2. Read the module contract.
3. Trace the equivalent or closest Basilisk behavior.
4. Define the player behavior before adding state.
5. Prefer current engine facts and direct rule order.
6. Add persistent state only when it buys real control capability.
7. Add tests before declaring the subsystem complete.

## Non-goals

Do not turn this workspace into a universal manager, scheduler, simulator, or parser replacement.

Do not optimize every civilization or map before the Byzantine land vertical slice works.

The workspace exists to build a player.
