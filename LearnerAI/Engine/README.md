# Engine Module

Engine is the native AoE2DE interface layer for the player.

It does not choose strategy.

## Owns

- native facts;
- native actions;
- constants and identifiers;
- strategic numbers;
- timers;
- engine configuration;
- documented engine quirks.

## Provides

- observations;
- capability facts;
- can-* feasibility;
- executable actions;
- world-state facts used as witnesses.

## Sources

Primary:

    docs/reference/AIREF-COMMAND-SOURCE.md
    docs/reference/inventories/
    docs/reference/engine/
    docs/reference/BYZANTINES_manifest.txt

Supplement with current official update notes and runtime tests when documentation is incomplete.

## Boundary

Engine permission is not completion.

An action is a request.

The game is the final authority.
