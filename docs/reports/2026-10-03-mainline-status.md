# Byzantine Mainline Status — 2026-10-03

## Authoritative state

- Repository: `justhop90-bot/ByzMetaTeacher`
- Branch: `main`
- Main commit: `f2f92810645da70c3dd080b711e05574609d71ee`
- Merged PR: #331, `feat: close Byzantine native engine and natural-food seams`
- PR #331 merge commit: `f2f92810645da70c3dd080b711e05574609d71ee`
- Remaining open PR: #327, resource-camp lifecycle regression work; branch is 83 commits behind current main and is not being treated as merge-ready.

## Byzantine.per mainline

The authoritative main bot now contains the audited #331 native-engine seam repairs:

- full 14-SN native target-evaluation policy;
- Byzantine offensive and defensive class-priority tables;
- separate persistent `target-player` identity from scouting `focus-player`;
- target validation and lock/release lifecycle;
- target guards on both `attack-now` execution paths;
- focus-player fact collection for military/civilian population and production/siege/fortification evidence;
- `up-train-site-ready` on all 42 current train admissions;
- Dark/early-Feudal deer selection with object ID, distance, scout movement, nearby food-villager retasking, refresh, and invalidation;
- separate forage/deer mill-placement selector state;
- fail-closed escrow boundary for unsupported native mutation surfaces.

Current static mainline audit:

| Check | Result |
|---|---:|
| Duplicate `defconst` definitions | 0 |
| Target-evaluation writes | 14, all unique |
| Offensive-priority writes | 20 |
| Defensive-priority writes | 9 |
| `attack-now` rules | 2 |
| `attack-now` rules missing target validation | 0 |
| Train admissions | 42 |
| Train admissions missing `up-train-site-ready` | 0 |
| New deer controller `up-request-hunters` usage | 0 |
| Deer villager retask paths | 2 |
| Deer target-point paths | 3 |
| `set-escrow-percentage` emitted by Byzantine.per | 0 |
| `up-modify-escrow` emitted by Byzantine.per | 0 |
| `up-release-escrow` emitted by Byzantine.per | 0 |

The source-level audit above is current repository evidence. A fresh post-merge GitHub Actions result for `f2f92810645da70c3dd080b711e05574609d71ee` was not exposed when this status was written, so the earlier pre-follow-up CI run is not reused as proof of the current mainline head.

## Compiler state

The generic compiler infrastructure remains ahead of the bot's strategic synthesis layer. The promoted compiler seams now include typed production-provider readiness, production timing observations, queue-capacity evidence, DUC execution slices, attack issue lowering, and escrow release/percentage-policy lowering.

The critical rule remains unchanged: compiler-policy support does not promote unverified DE runtime semantics into facts. Same-pass escrow visibility, provider busy/queued behavior, queue timing, DUC liveness, attack acknowledgement, timer granularity, and other native/runtime boundaries remain OPEN until independently evidenced.

## Strategy state

The Byzantine strategy now has a native engine combat control plane behind the existing attack lifecycle rather than relying on engine defaults. The strategy remains deliberately layered:

`OBSERVATION -> ARBITRATION -> EXECUTION -> WITNESS -> RECOVERY -> REASSESSMENT`.

The current land-oriented strategy includes:

- Dark/Feudal opening arbitration;
- Fast Castle, counter-Feudal, Boom, water posture, Castle conversion, and Imperial conversion;
- production scaling and provider-readiness admission;
- persistent scouting and enemy target/focus separation;
- Castle/Imperial military composition and siege approach;
- defensive geometry and fortified-front placement;
- deer/boar natural-food handling;
- bounded resource dropsite recovery;
- market/resource conversion;
- existing construction, research, escrow, and recovery lifecycle ownership.

Full naval execution and broader late-game strategic breadth remain future work.

## Pending camp-placement work

PR #327 contains a substantial resource-camp placement rewrite that is directly relevant to the previously observed failure mode where the bot could discover a new wood/gold/stone source without placing the appropriate nearby camp.

That branch has successful historical compiler runs, but it was based on an older main and now diverges from current main. It is therefore tracked as pending rebase/port work, not silently merged by inheritance.

The desired camp behavior remains:

resource observed -> nearest viable real resource object -> persisted point -> existing demand/builder lifecycle -> completion witness -> recovery/reselection.

## Next project frontier

1. Rebase/port the validated camp-placement lifecycle from PR #327 onto current main without regressing the #331 target/provider/natural-food repairs.
2. Run the complete compiler/native/determinism gate on the resulting mainline.
3. Continue native escrow runtime evidence where justified.
4. Continue Strategic Number evidence closure and broader community strategy synthesis.
5. Expand naval/transport execution only after the land control plane remains stable.

This file is the current status record. Historical closure reports are intentionally left unchanged.
