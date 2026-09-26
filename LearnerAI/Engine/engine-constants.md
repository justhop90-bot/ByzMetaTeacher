# Engine Constants

Defines the identifier discipline for the player.

## Must contain

- verified unit IDs;
- verified building IDs;
- verified tech IDs;
- strategic-number IDs;
- timer ranges;
- version-sensitive aliases.

## Sources

Use docs/reference/inventories/, docs/reference/BYZANTINES_manifest.txt, and AIRef.

Never invent an identifier because its name looks plausible.

## Gate

Every identifier used in generated player code must resolve against the current reference data or be explicitly documented as a verified version-specific local alias.
