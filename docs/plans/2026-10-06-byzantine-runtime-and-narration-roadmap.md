# Byzantine Runtime + Next-Generation Narration Roadmap — 2026-10-06

Status: **ACTIVE runtime roadmap** for the Byzantine bot on `main`.

This roadmap combines the six-prompt next-generation narration plan with the latest runtime evidence. Runtime correctness takes precedence over narration polish: the bot must first advance through the intended strategic ages and execute the existing plan before it gets better at explaining itself.

## Runtime evidence captured 2026-10-06

### Match A — Standard Arabia

**Result:** Byzantine bot defeated the Moderate AI.

Interpretation:
- This is a meaningful baseline success on standard open land.
- The current bot can complete a full match sufficiently well to produce a win against Moderate on Arabia.
- Preserve this behavior as a regression scenario.
- Do not infer that the strategic system is solved. One successful Arabia game does not close age timing, resource-placement, attack execution, or late-game robustness.

Acceptance requirement:
- Future repairs must not regress the Arabia win baseline.
- Keep Arabia as the primary open-land smoke scenario after major runtime changes.

### Match B — Arena

**Result:** Bot became stuck in Feudal and continued producing villagers until roughly 60 villagers, after which the human stopped the game.

Interpretation:
- This is a **P0 runtime blocker**.
- The defect is not cosmetic and not a narration issue.
- Arena exposes a missing or broken transition from Feudal economic execution into Castle-age commitment.
- Continuous villager production while the bot is already economically large indicates that the economy is being allowed to continue operating without a hard strategic transition that protects the next age.
- The correct fix is not simply "train fewer villagers." The compiler/runtime must establish a valid Castle-age demand, protect its resource requirements, arbitrate that demand against ordinary economy spending, and witness the age-up completion before resuming normal Castle-phase priorities.
- The Arena failure must be reproduced and diagnosed before treating the narration roadmap as the primary next task.

Acceptance requirement:
- Arena must reach Castle under a normal no-pressure opening.
- Villager production must not starve Castle-age commitment.
- After Castle completion, normal Castle production/economic priorities may resume.
- If Castle commitment becomes impossible because a required resource or capability is unavailable, the bot must enter an explicit recovery/reassessment path rather than silently farming villagers forever.

## Priority order

1. **P0 — Arena Feudal lock:** identify the first broken edge in Feudal -> Castle demand, resource protection, age action, or completion witness.
2. **P0 — Preserve Arabia baseline:** every runtime repair must retain the Standard Arabia Moderate win.
3. **P1 — Early economy coherence:** resource camps, nearby viable resource selection, DBA/Horse Collar timing, and resource-front continuity.
4. **P1 — Castle timing and conversion:** ensure the bot turns a successful Feudal economy into a timely Castle commitment and then changes posture.
5. **P1 — Military execution:** group, push, siege, and recover rather than merely accumulating units.
6. **P1 — Continuous late-game spending:** prevent surplus economy from becoming passive villager inflation.
7. **P2 — Next-generation internal narration:** implement the six-prompt narration plan below, using only facts, decisions, and witnesses that already exist.

## Next-generation narration plan

There are **6 implementation prompts**. Each prompt is a reviewable slice with focused tests and no strategy rewrite.

### Prompt 1/6 — Typed narration contract + persistent narrative context

Goal:
Create a typed narrative layer over the existing native voice system without creating a second planner.

Files/components:
- `LearnerAI/Compiler/ir/strategic_voice.py`
- `LearnerAI/Compiler/ir/strategy.py`
- `LearnerAI/Compiler/ir/program.py`
- `LearnerAI/Compiler/compiler.py`
- `LearnerAI/Compiler/emitter/per.py`
- `LearnerAI/Compiler/ir/community_strategy_packs.py`

Checklist:
- [ ] Add `NarrativeTopic`: OPENING, ECONOMY, POSTURE, COUNTER, FORCE, SIEGE, ATTACK, OBJECTIVE, RECOVERY, ENDGAME.
- [ ] Add `NarrativeStage`: OBSERVE, DECIDE, COMMIT, WITNESS, RECOVER.
- [ ] Add `NarrativeEvidence`: FACT, DECISION, WITNESS.
- [ ] Extend `VoiceRule` with declarative narrative metadata.
- [ ] Add deterministic alternative-message metadata.
- [ ] Keep unknown facts silent. No executable UNKNOWN speech mode.
- [ ] Define presentation-only narrative context and prove it cannot be consumed by production, economy, research, construction, attack, posture, or resource arbitration.
- [ ] Preserve all current voice triggers, clears, priorities, latches, timers, cooldowns, budget, and `focus-player` audience behavior.
- [ ] Do not rewrite the strategy pipeline.
- [ ] Add focused metadata, validation, isolation, compatibility, and determinism tests.
- [ ] Run focused voice tests plus strategy compiler integration.

### Prompt 2/6 — Early-game and economic monologue

Goal:
Narrate the actual opening decision chain:

`OPENING -> RESOURCE FRONT -> FEUDAL COMMITMENT -> ECONOMIC MULTIPLIER -> CASTLE COMMITMENT`

Checklist:
- [ ] Map narration to existing resource-front observations and camp demands.
- [ ] Narrate successful camp placement only from a witnessed state.
- [ ] Narrate Feudal commitment from the actual age-up decision/state.
- [ ] Narrate Double-Bit Axe, Horse Collar, and Wheelbarrow only from their actual research/action witnesses.
- [ ] Narrate Castle commitment from an actual Castle-age demand/decision, not from elapsed time.
- [ ] Add bounded alternative lines so repeated matches do not sound mechanically identical.
- [ ] Keep all lines short, concrete, present-tense, and strategically meaningful.
- [ ] Add focused tests for opening, failed/blocked resource front, research completion, and Castle commitment.

Important runtime dependency:
- Prompt 2 must not hide or paper over the Arena Feudal lock. The narration should expose that transition cleanly once the underlying runtime defect is fixed.

### Prompt 3/6 — Battlefield interpretation

Goal:
Narrate changes in the problem rather than merely announcing unit counts.

Checklist:
- [ ] Map existing enemy observations into cavalry, ranged, infantry, siege, and resource-pressure topics.
- [ ] Distinguish observed threat from predicted threat.
- [ ] Narrate counter decisions only when the corresponding demand/arbitration exists.
- [ ] Narrate posture changes only when the posture actually changes.
- [ ] Add deterministic variants for repeated pressure events.
- [ ] Preserve fail-closed behavior when evidence is weak or stale.
- [ ] Add tests proving the narration cannot invent an enemy composition.

### Prompt 4/6 — Attack, witness, recovery, reassessment

Goal:
Make the monologue follow the attack lifecycle:

`PREPARE -> COMMIT -> MOVE -> WITNESS -> RECOVER -> REASSESS -> SECOND WAVE`

Checklist:
- [ ] Narrate force preparation from existing package/role state.
- [ ] Narrate attack commitment only when attack state is actually issued.
- [ ] Narrate movement/pressure from existing operational state, not imagined pathing.
- [ ] Narrate objective opening only from the existing offensive-objective witness.
- [ ] Narrate failed pushes from the existing recovery state.
- [ ] Narrate gold/resource recovery only from existing recovery evidence.
- [ ] Narrate second-wave conversion from an actual renewed objective/force state.
- [ ] Keep role controllers and attack ownership unchanged.

### Prompt 5/6 — AIRef-powered contextual enrichment

Goal:
Use available native evidence at the edge of what is safely expressible, without turning voice into an unstable pseudo-LLM.

Potential evidence channels:
- existing threat data;
- existing player/target identities;
- existing DUC/strategy state;
- bounded numeric/contextual facts;
- deterministic message selection.

Checklist:
- [ ] Audit `up-get-threat-data` and `up-chat-data-to-player` against the current command inventory before use.
- [ ] Only expose values already proven safe and deterministic for narration.
- [ ] Use numeric context sparingly and only when it materially improves meaning.
- [ ] Never let dynamic text become an input to strategic arbitration.
- [ ] Preserve parser-safe message constraints.
- [ ] Add deterministic output fixtures.
- [ ] Explicitly label any remaining AIRef uncertainty OPEN.

### Prompt 6/6 — Verification, artifact sync, runtime acceptance, pruning

Goal:
Make the narration system release-quality rather than an ever-growing pile of things the bot might someday say.

Checklist:
- [ ] Run focused voice tests.
- [ ] Run strategy compiler integration.
- [ ] Run native zero-findings validation.
- [ ] Run cross-platform determinism.
- [ ] Regenerate/synchronize authoritative `Byzantine.per`.
- [ ] Verify the checked-in artifact matches the source compiler.
- [ ] Run Standard Arabia acceptance and retain the Moderate win baseline.
- [ ] Run Arena acceptance and verify timely Castle transition.
- [ ] Run pressure/counter/attack/recovery scenarios.
- [ ] Prune redundant voice rules after replay evidence.
- [ ] Record exact Git SHA and acceptance evidence.

## P0 diagnosis — Arena Feudal lock, corrected 2026-10-06

The Arena replay with Market, Blacksmith, Barracks, Mill, two mining camps, a lumber camp, extensive housing, and 71 villagers rules out missing Feudal infrastructure as the primary blocker.

The broken edge is a **feasibility/queue circularity**:

`civilian-villager-continuity` uses `can-research-with-escrow castle-age` to decide when villager production should stop. Native Castle-age research feasibility requires the research provider queue to be free. The Town Center is also the continuous villager-production provider. Therefore:

`train villager -> TC occupied -> can-research-with-escrow false -> villager guard stays open -> train villager`

The Castle-age demand itself correctly retains `can-research-with-escrow castle-age` as its final execution gate. That predicate must remain there.

Smallest repair:
- [ ] In `LearnerAI/Compiler/ir/community_strategy_packs.py`, change only the Castle-stop guard inside `civilian-villager-continuity` from `(can-research-with-escrow castle-age)` to `(can-afford-research castle-age)`.
- [ ] Keep the existing 28-villager, Blacksmith, and Market guards unchanged.
- [ ] Do **not** weaken the Castle action itself: `can-research-with-escrow castle-age` remains the native execution/queue-feasibility gate.
- [ ] Add a focused regression proving villagers stop once the Castle bank is affordable even when `can-research-with-escrow` is false because the TC is occupied.
- [ ] Regenerate `Byzantine.per`.
- [ ] Verify Standard Arabia still reaches/wins the existing Moderate baseline.
- [ ] Verify Arena transitions to Castle instead of continuing toward the 60–71 villager stall.

This is a queue-arbitration repair, not an Arena-specific strategy rewrite.

## Runtime repair tracks

### Track A — Arena Feudal -> Castle lock

**First diagnostic boundary:**
`OBSERVATION -> ARBITRATION -> EXECUTION -> WITNESS`

Investigate in that order:
- [ ] Is Castle actually demanded after Feudal under Arena's map/posture conditions?
- [ ] Is the Castle demand admissible and capable?
- [ ] Are food/gold reserves protected from ordinary villager/economic spending?
- [ ] Does the age-up action actually fire?
- [ ] Is the age-up completion witness visible to the posture/strategy transition?
- [ ] If the demand is blocked, does recovery/reassessment change the situation?
- [ ] Identify the **first broken edge**, not the last visible symptom.
- [ ] Add a focused regression reproducing the 60-villager Feudal stall.

Explicit non-fix:
- Do not simply reduce the villager cap and declare victory. That would treat the smoke alarm as the fire.

### Track B — Arabia baseline preservation

- [ ] Record the successful Standard Arabia Moderate win as a baseline.
- [ ] Repeat after every P0/P1 runtime change.
- [ ] Track age timing, resource camps, research, production, attack, and endgame state.
- [ ] Treat any Arabia regression as a release blocker until explained.

### Track C — Resource-front and early economy

Existing runtime evidence requiring attention:
- [ ] Build mining/lumber camps at viable nearby resources instead of sending villagers on unnecessary long walks.
- [ ] Support distinct later gold sources when the first source is no longer sufficient.
- [ ] No Dark Age stone mining unless a verified strategic demand requires it.
- [ ] Preserve nearest viable gold selection where known.
- [ ] Add the nearby second berry mill where the existing evidence/geometry supports it.
- [ ] Buy Double-Bit Axe and Horse Collar promptly after the relevant age transition instead of accumulating Feudal bank without the multiplier.

### Track D — Military execution

Existing runtime evidence requiring attention:
- [ ] Group the army before committing it.
- [ ] Issue autonomous attacks at a reachable minimum endgame threshold.
- [ ] Use siege meaningfully when the enemy position requires it.
- [ ] Avoid walking villagers under enemy Castles for exposed gold.
- [ ] Preserve the successful building-targeted escalation already present in the current strategy.

### Track E — Late-game spending

- [ ] Convert sustained surplus into military, siege, technology, or strategic infrastructure.
- [ ] Prevent the economy from continuing to inflate villagers after military/age demands are starving.
- [ ] Use hysteresis and recovery rather than oscillating between production priorities.
- [ ] Keep continuous spending subordinate to Castle/Imperial timing and essential upgrades.

## Runtime acceptance matrix

| Scenario | Current result | Priority | Acceptance |
|---|---|---:|---|
| Standard Arabia vs Moderate | **Won** | P0 regression baseline | Continue to win after repairs |
| Arena, normal opening | **Stuck Feudal, ~60 villagers** | P0 blocker | Timely Castle transition |
| Early gold / wood camp placement | Previously deficient | P1 | Nearby viable camps are built |
| Feudal eco upgrades | Previously inconsistent | P1 | DBA/Horse Collar purchased promptly |
| Castle conversion | Too late / missing on some runs | P0/P1 | Age-up demand wins arbitration |
| Late-game attack | Previously absent or too late | P1 | Autonomous baseline attack occurs |
| Siege execution | Underused | P1 | Siege participates in appropriate pushes |
| Internal narration | v1 sparse | P2 | Lifelike, evidence-bound narration |

## Global rules

- Strategy decisions remain compiler-owned. Voice is a projection of strategy state.
- Facts, decisions, and witnesses must remain distinguishable.
- Unknown behavior stays silent/fail-closed.
- Timers provide cadence, never truth.
- Pending is not completion.
- `can-*` is permission/feasibility, not world-state proof.
- Do not invent engine facts to make a line sound intelligent.
- Prefer one causal repair over many compensating rules.
- Preserve `main` as the authoritative runtime artifact.
- A successful game is evidence, not proof of closure.
- A failed game is a diagnostic signal, not permission to rewrite the architecture blindly.

## Definition of done for this roadmap

The roadmap is complete when:
1. Arena no longer gets trapped in Feudal under the standard no-pressure test.
2. The Arabia Moderate win baseline remains intact.
3. Resource placement and early economic transitions are materially improved.
4. Castle timing reliably changes strategic posture.
5. Autonomous military/siege execution is demonstrated in runtime play.
6. The six-prompt narration system is implemented, validated, synchronized, and demonstrably tied to real strategy state.
7. Remaining uncertainty is explicitly marked runtime/open rather than disguised as compiler certainty.

