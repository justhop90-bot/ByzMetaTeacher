# Byzantine Core v1 — Earlier Upgrade Cross-Reference and Final Completeness Checklist

Branch: `bot/byzantine-core-v1`
Patch target: Update 185872
Scope: 1v1 Byzantine bot built through the existing compiler strategy path.

## Earlier upgrade cross-reference

| Earlier tranche | Expected addition | Current branch status |
|---|---|---|
| Community strategy synthesis | Economy/research, Castle/Imperial conversion, standing composition, siege, monks, outpost, scouting/map policy, water policy | PRESENT in stock Byzantine strategy |
| Native building aliases | Town Center, Stable, Siege Workshop, University, Outpost aliases | PRESENT |
| Canonical stock strategy | `build_byzantine_strategy()` wired into compiler | PRESENT |
| Typed naval/transport execution | Water posture, transport phase, loss/recovery, naval defense/control | PRESENT |
| Varangian/map/opening/economy | Varangian pressure branch, MapProfile, OpeningSelector, civilian SN allocation | PRESENT |
| Deployable Core v1 bot | Dark→Feudal→Castle bot-local production, infrastructure, housing, conditional military, Imperial conversion | PRESENT |
| DUC ObjectData repair | Numeric ObjectData operand validated against authoritative inventory | PRESENT |
| Basic economy closure | Lumber Camp, Mining Camp, Mill, Farm, Market, dropsite-distance policy | CLOSED IN THIS PATCH |
| Basic Feudal floor | Small Spearman screen without creating a universal Feudal scheduler | CLOSED IN THIS PATCH |

## Final bot checklist

### Economy and opening

- [x] Villager production is staged through Imperial.
- [x] Housing has a bounded stage ladder.
- [x] First Lumber Camp demand exists.
- [x] Second Lumber Camp demand responds to wood dropsite distance.
- [x] First Mining Camp demand exists when mineral resources are discovered.
- [x] Additional Mining Camp demand responds to mineral dropsite distance.
- [x] Mill demand exists before farm expansion.
- [x] Farm bank expands through bounded stages.
- [x] Market capability exists as Feudal recovery/imbalance support.
- [x] Existing economy-controller allocation remains the single worker-allocation controller.
- [x] Dropsite placement policy uses the existing Strategic Number surface, not a second scheduler.

### Military

- [x] Conditional Feudal Spear response exists.
- [x] Conditional Feudal Skirmisher response exists.
- [x] Castle Knight/Cataphract/Varangian branches exist.
- [x] Siege capability and bounded siege support exist.
- [x] Monk support exists.
- [x] Imperial Halberdier/Elite Skirmisher/Heavy Camel conversion exists.
- [x] Imperial Hand Cannoneer conversion exists.
- [x] Elite Cataphract conversion requires the existing Logistica/research chain.
- [x] Existing attack lifecycle/DUC target substrate remains connected.

### Water and transport

- [x] Islands Dock demand exists.
- [x] Dark-Age Fishing Ship opening exists.
- [x] Transport capability exists.
- [x] Naval defense/control branches exist.
- [x] Transport-loss recovery remains owned by the existing water execution plan.
- [ ] Successful transport landing remains an OPEN runtime witness.
- [ ] Exact dock/landing placement remains OPEN rather than being faked.

### Information and control

- [x] Existing exploration Strategic Number modes remain connected.
- [x] Existing age-specific explorer-cap Strategic Number modes remain connected from the stock policy.
- [x] Initial exploration requirement is explicitly set.
- [x] Existing Goal/SN/Timer control plane remains the only persistent-control path.
- [x] Existing DUC plan remains the target/search control path.
- [x] Native ObjectData DUC operands are numeric and inventory-validated.

### Intentionally not claimed

- [ ] Exact wall/gate placement quality.
- [ ] Relic acquisition/pathing completion.
- [ ] Native `up-send-scout` movement behavior as a fully proven strategic scout controller.
- [ ] Exact queue-exit/birth timing.
- [ ] Exact same-pass escrow visibility.
- [ ] Battlefield victory from `attack-now`.
- [ ] Runtime economy income simulation or placement optimality.
- [ ] Universal map/water discovery beyond the proven map predicates used by the current strategy.

## Cross-reference rule

A feature is counted as present only when the generated bot exposes a concrete demand/control path with a native condition, action, witness or release signal, and existing compiler validation. Merely having a symbol, catalog entry, or strategy document does not count as bot behavior.

The final artifact must be regenerated after every policy change and accepted only after deterministic compilation, native zero-findings, full compiler regression, and the existing cross-platform determinism gate pass.
