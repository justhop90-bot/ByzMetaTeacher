# Engine Debug

Defines how engine assumptions are investigated when static evidence is insufficient.

## Debug loop

source claim -> native validation -> minimal reproduction -> runtime test -> recorded result

## Must distinguish

- parser rejection;
- native feasibility false;
- action accepted but delayed;
- action accepted but world state unchanged;
- incorrect witness;
- source-order interaction;
- actual engine defect or undocumented behavior.

## Sources

Use LearnerAI/ENGINEERING.md, Compiler/backends/, docs/reference/engine/, and runtime evidence.

Do not turn debugging workarounds into permanent strategy state without proving that the state is actually required.
