# `can-build-with-escrow`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-can-build-with-escrow"></a>

## `can-build-with-escrow`

- Kind: `command`
- Detail: Fact - Buildings, Can Do

Syntax: `(can-build-with-escrow <BuildingId>)`

This fact checks whether the computer player can build the given building if escrowed resources are included. You cannot use building classes with this command. This command does not work with walls or gates. However, you can use can-build-wall-with-escrow, can-build-gate-with-escrow, up-can-build-line, or up-can-build to check if walls or gates can be built. In particular it checks:It's available to the computer player's civ.Tech tree prerequisites are met (also works for the Khmer building prerequisites bonus).Resources needed for the building are available including escrow stockpiles.It does not check whether villagers exist to build it, or if there is adequate space for the building. The fact allows the use of building line wildcard parameters for pBuildingId. The only wildcard parameter available is watch-tower-line. However, it is better to use watch-tower instead of watch-tower-line, even after Guard Tower or Keep upgrades due to some bugs with watch-tower-line. Simply using (can-build-with-escrow watch-tower) will work regardless of tower upgrades. Important Note: Always use a can-build, can-build-with-escrow, or up-can-build condition in every rule where you use the build or up-build command. Without this condition, the building queue for this building may get stuck for the rest of the game.

[AIRef](https://airef.github.io/commands/commands-details.html#can-build-with-escrow)

Completion insert text:

```text
(can-build-with-escrow ${1:BuildingId})
```

