# Byzantine Meta Repair Pass v2

Date: 2026-10-03  
Base: `main` at `ab4c5f71760cc57500ae27715047084c56e5ec7c`

This tranche closes the verified Naga/Byzantine interface seams without replacing the existing Byzantine lifecycle owners. The implementation target is the native engine boundary, not another thousand-rule strategy forest.

## Exact holes closed

### Native combat control plane

The bot already owned attack grouping, siege muster, fortified approach, attack issuance, and recovery. It still left the engine's combat-control knobs at defaults.

The branch now explicitly initializes:

- `sn-attack-intelligence = 1`
- `sn-local-targeting-mode = 1`
- `sn-enable-offensive-priority = 1`
- `sn-zero-priority-distance = 255`

It also emits the full 14-member target-evaluation policy family and a Byzantine-specific offense/defense class table. The priority values are policy choices, not copied Naga truth.

### Target identity

`sn-focus-player-number` remains observation context. `sn-target-player-number` is now the persistent offensive identity.

The branch validates the target, derives it from focus when no offensive target exists, synchronizes focus to target when appropriate, locks the target while attack readiness is armed, and clears the lock when the offensive package is released.

Both `attack-now` issuance paths require a valid target-player identity before execution.

### Enemy fact layer

The branch materializes focus-player facts for military population, civilian population, barracks, ranges, stables, siege workshops, and castles. Those observations feed the existing counter-package arbitration rather than creating a scheduler.

### Production-provider readiness

Every current `can-train` / `can-train-with-escrow` admission in `Byzantine.per` is paired with `up-train-site-ready`. This keeps feasibility, provider readiness, queue protection, and world-state witnesses distinct.

### Natural food

The earlier Naga comparison correctly identified deer as a real missing economy subsystem, but the first implementation had two wiring problems: it relied on the repository's evidence-only `up-request-hunters` shortcut and reused the mill-demand goal as scratch selector state.

The current branch fixes both.

The deer controller now tracks object ID and distance, moves the scout to the selected deer, retasks nearby idle food villagers through the existing DUC path, refreshes the assignment, and invalidates stale/dead deer. The hunt-distance SN is restored to its documented native default `-1` when the controller releases.

Food-source-aware mill placement now has its own `byzantine-food-source-selector` side state. It distinguishes nearby forage from nearby deer through `sn-preferred-mill-placement` and leaves the existing mill demand/constructor lifecycle authoritative.

### Escrow boundary

The Naga comparison confirms that native escrow mutation is a real surface, but the checked-in compiler still marks UP escrow mutation and same-pass acquisition semantics OPEN.

This branch therefore deliberately does not emit:

- `up-modify-escrow`
- `up-release-escrow`
- `set-escrow-percentage`

The existing `can-research-with-escrow` + explicit `release-escrow` path remains intact. No fake reservation semantics are introduced until the native/runtime evidence supports them.

## Deliberate exclusions

Resource-specific native defense SNs, `sn-military-superiority`, generic scheduler behavior, and full naval execution remain outside this tranche. Byzantine's custom resource-front/static-defense geometry remains the owner for placement decisions.

## Audit gates

The focused seam test now checks:

- all 14 target-evaluation writes;
- offensive/defensive priority controls;
- target-player/focus separation and attack guards;
- focus-fact materialization;
- provider readiness on every production admission;
- deer object/distance/DUC retasking;
- food-source selector separation from the mill lifecycle;
- unique native alias definitions;
- fail-closed escrow mutation boundaries.

The repository workflow also runs the new focused test and the existing native zero-findings/full regression suite. The branch has not been re-certified by a fresh GitHub Actions run after the latest commits, so the prior successful run is not being reused as proof for this newer head.

Runtime match strength remains a separate playtest question.
