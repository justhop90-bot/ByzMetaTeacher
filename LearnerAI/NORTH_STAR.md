# LearnerAI North Star

## What this workspace is building

LearnerAI is the design, teaching, semantic-validation, and compilation workspace for a competent **stock-style 1v1 Byzantine AoE2DE AI**.

The target is not an Arabia-only specialist.

The player should handle the ordinary map and game situations a normal stock AI is expected to recognize: open land, closed land, hybrid maps, meaningful water, naval starts, transport requirements, defensive fortifications, siege, Monks/relics, economic expansion, and late-game conversion.

The first civilization is Byzantines. Generalization to other civilizations comes after this player is coherent.

The end product must be able to:

- maintain a coherent Dark Age economy;
- choose a sensible opening/posture from current information;
- transition through Feudal without wrecking the next strategic objective;
- maintain a minimum defensible military;
- use the correct infrastructure for the current demand;
- reach Castle at sensible times for the position;
- expand its economy in Castle Age;
- use siege when the position requires it;
- use Monks and contest relics when economically and strategically appropriate;
- build docks and use fishing, naval combat, and transport when the map creates a real water problem or opportunity;
- use walls, gates, towers, Castles, and other defensive structures when their defensive capability is justified;
- recognize when late Bombard Towers or other expensive fortifications are useful instead of treating them as mandatory;
- adapt composition and infrastructure to observed enemy commitments;
- recover when a preferred plan is interrupted;
- reach Imperial with a functioning economy;
- convert Castle and Imperial economies into actual pressure.

A building or unit is not a checklist item. It is a capability provider activated by a real strategic or domain demand.

## North-star control loop

    WORLD STATE
      -> OBSERVE
      -> INTERPRET
      -> STRATEGIC POSTURE
      -> PERSISTENT DEMAND
      -> REQUIRED CAPABILITY
      -> ENGINE FEASIBILITY
      -> ENGINE ACTION
      -> WORLD-STATE WITNESS
      -> RELEASE / INVALIDATE
      -> REASSESS

Three kinds of knowledge remain separate:

Strategic memory survives a pass because the decision remains meaningful. Examples: Castle commitment, BOOM posture, minimum army intent, naval commitment.

Derived state is reconstructed from current facts. Examples: current enemy cavalry, current dock opportunity, current farm pressure, current resource shortage.

Execution state exists only when the engine needs memory for a real lifecycle, contention problem, or asynchronous operation. Examples: pending construction, live resource claim, transport preparation, bounded execution backoff.

The bot is a heuristic player, not a global finite-state machine.

## Product coverage

### Land economy and military

The player must work on the common land-map families rather than one scripted Arabia opening.

Required families:

- open land;
- closed land;
- hybrid land;
- standard random-map variations within the above.

### Water and hybrid play

If the map supplies meaningful water, the player must be capable of recognizing the opportunity or threat.

This includes:

- deciding whether a dock is justified;
- fishing and fish-trap economy;
- naval production and upgrades;
- transport ships when land access is interrupted;
- naval defense/offense when water control matters;
- shifting resources back to land when the water plan loses strategic value.

On a mostly land map, the player may correctly ignore docks.

Ignoring a dock when the map makes water economically or strategically important is not acceptable.

### Fortifications and defensive infrastructure

The player must understand fortification as a capability, not a ritual.

Possible demands include:

- palisades and gates;
- walls and stone walls;
- Outposts/watch towers;
- Guard Towers;
- Bombard Towers;
- defensive Castles.

The conditions should depend on map geometry, exposed economy, enemy pressure, strategic posture, resources, age, and opportunity cost.

The player should not build towers merely because the building exists.

### Siege

Siege is a strategic capability family.

The player must recognize when a Siege Workshop, Rams, Mangonels/Onagers, Scorpions, Bombard Cannons, or other appropriate siege tools solve a current problem.

Examples:

- ranged mass needs area damage;
- enemy buildings/walls require siege;
- a Castle/fortification needs sustained pressure;
- the player needs anti-building conversion;
- late-game composition requires scalable siege support.

Siege demand must connect to production capability and completion/replacement logic. One Siege Workshop existing is not proof that siege is actually being produced.

### Monks and relics

Monks are not merely another military unit.

The player must be able to recognize:

- healing value;
- conversion value where relevant;
- relic opportunity;
- relic denial/contestation;
- monastery capability requirements;
- faith/relic economy consequences;
- recovery after losing Monks.

Relic play should be opportunistic and position-aware. The player should not sacrifice its Castle economy simply to collect a relic that costs more than it returns.

### Castle and Imperial

Castle is the first major conversion milestone.

Castle demand, prerequisites, resource protection, construction, witness, and release must form one lifecycle, while downstream economy and military demands emerge from the new position.

Imperial is a conversion phase. Reaching Imperial without the ability to exploit it is not success.

## Interruption is a first-class requirement

Preferred plans will be interrupted.

    Castle plan
      -> enemy pressure
      -> defensive demand rises
      -> temporary military investment
      -> Castle intent survives
      -> pressure falls
      -> Castle becomes feasible
      -> Castle completes

    Water boom
      -> enemy gains naval superiority
      -> naval demand changes
      -> land economy/army rises
      -> water investment is reduced
      -> strategic position is reassessed

    Relic plan
      -> Monks are lost
      -> relic demand becomes expensive or unsafe
      -> demand cancels
      -> economy returns to military/expansion

    Boom
      -> raid
      -> army floor rises
      -> economy reallocates
      -> raid ends
      -> boom demand survives
      -> expansion resumes

Execution failure changes timing. It should not erase valid strategic truth.

## What the compiler is for

The compiler is an engineering instrument for building the player, not the player itself.

It should eventually prove that important behaviors have:

- an owner;
- a persistent reason;
- a demand;
- at least one viable capability provider;
- engine-native feasibility;
- one controlled action path;
- a pending/completion lifecycle when required;
- a world-state witness;
- release or invalidation;
- recovery from transient execution failure.

It should be capable of reasoning about the same broad player surface:

- land infrastructure;
- water/docks/ships;
- fortifications;
- siege;
- Monks/relics;
- economic expansion;
- military composition.

The compiler does not replace the AoE2 native parser. The pinned native backend handles native .per legality.

## Information hierarchy

Start at LearnerAI/SOURCE_MAP.md.

Use the repository's AIRef source and inventories for native command and parameter semantics. Use docs/reference/engine and docs/reference/BYZANTINES_manifest.txt for engine and civ data. Use Basilisk/Basilisk.per plus validation and audit documents for proven local patterns and known failure modes. Use established community AIs and tutorials for practical idioms. Use runtime testing for behavior static sources cannot prove.

## Relationship to Basilisk

Basilisk remains the current production controller and the strongest local implementation reference.

LearnerAI is not a hidden Basilisk rewrite. Learn from Basilisk, compare against it, and reuse verified mechanisms where appropriate. The new learner player must earn its own behavior through explicit specifications and runtime evidence.

## Development test

Every subsystem must answer:

- What real player problem does this solve?
- What observation justifies it?
- What intent survives the pass?
- What demand represents the required world state?
- What capability provides the means?
- What engine predicate proves feasibility?
- What action is issued?
- What world-state fact proves completion?
- What happens if it fails?
- What happens if the strategy becomes obsolete?
- What resource opportunity cost does it impose?
- What information causes reassessment?

If those answers cannot be traced, the subsystem is not ready.
