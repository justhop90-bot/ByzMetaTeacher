# LearnerAI North Star

## What this workspace is building

LearnerAI is the design, teaching, semantic-validation, and compilation workspace for a competent 1v1 standard-land Byzantine AoE2DE AI.

The end product is not a tutorial script, parser demo, research simulator, or generic software framework. It is a heuristic player that can maintain a coherent Dark Age economy, survive Feudal pressure, reach Castle at sensible times, expand its economy, build the infrastructure its strategy actually needs, adapt composition to the opponent, recover when the preferred plan is interrupted, and convert Castle and Imperial economies into military pressure.

The first battlefield is deliberately narrow: 1v1 standard-land Byzantine play. Generalization comes after this player is coherent.

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

Strategic memory survives a pass because the decision remains meaningful. Examples: BOOM posture, Castle commitment, minimum army intent.

Derived state is reconstructed from current facts. Examples: current enemy cavalry, current farm pressure, current resource shortage.

Execution state exists only when the engine needs memory for a real lifecycle, contention problem, or asynchronous operation. Examples: pending construction, a live resource claim, bounded execution backoff.

The bot is a heuristic player, not a global finite-state machine.

## Behavioral target

Economy answers the binding shortage that currently prevents the chosen strategy from functioning.

Feudal military is a minimum credible commitment, not an automatic mass-production phase.

Castle is a conversion milestone. Its demand, prerequisites, resource protection, construction, completion witness, and downstream economic/military consequences must form one traceable lifecycle.

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

    Boom
      -> raid
      -> army floor rises
      -> economy reallocates
      -> raid ends
      -> boom demand survives
      -> expansion resumes

    Counter package
      -> enemy composition changes
      -> old package becomes obsolete
      -> old demand releases
      -> new package opens
      -> production capability follows

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
