# Ownership Matrix

| State/fact | Semantic owner | Typical readers | External writers |
|---|---|---|---|
| Engine configuration | Engine | Relevant modules | None |
| Strategic posture | Strategy | All domains | Strategy |
| Strategic demands | Strategy | Relevant domains | Strategy |
| Economic allocation | Economy | Strategy/domains | Economy |
| Construction state | Construction | Strategy/Engineering | Construction |
| Production state | Production | Military/Strategy/Engineering | Production |
| Enemy observations | Information | Strategy/Military/Economy | Information |
| Threat interpretation | Information | Strategy/Military | Information |
| Military posture | Strategy | Military | Strategy |
| Military execution state | Military | Strategy/Engineering | Military |
| Completion meaning | Owning domain | State/Strategy/Engineering | Domain owner |
| Witness validation | Engineering | Domain/Strategy | Engineering |
| Diagnostics | Engineering | Human/debugging | Engineering |

## Rules

1. One semantic owner per persistent state variable.
2. Multiple readers are acceptable; competing writers are not.
3. External modules request or consume outcomes rather than mutating another module's private state.
4. State names must have defined lifecycle meaning.
5. A release condition must identify what proves completion and what happens afterward.
6. Temporary arbitration is not a substitute for strategic ownership.

## Read/write principle

Read broadly when necessary. Write narrowly.

This is intentionally practical for .per; the language does not provide modern encapsulation, so ownership must be enforced by discipline, naming, source organization, and audits.
