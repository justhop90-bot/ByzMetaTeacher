# Engine Config

Defines the DE environment assumptions used by the learner player.

## Must record

- target DE build;
- AI folder/package assumptions;
- .ai/.per loading model;
- version-sensitive commands;
- native backend version;
- runtime test environment.

## Sources

Use docs/reference/engine/, docs/reference/AIREF-COMMAND-SOURCE.md, and the native backend lock in Compiler/backends/.

## Gate

Version-sensitive behavior is recorded as an assumption until runtime evidence confirms it.
