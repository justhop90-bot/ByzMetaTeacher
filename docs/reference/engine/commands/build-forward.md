# `build-forward`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-build-forward"></a>

## `build-forward`

- Kind: `command`
- Detail: Action - Buildings

Syntax: `(build-forward <BuildingId>)`

Builds the given building close to an enemy if the building is available to the player and the building can be constructed without escrowed resources. The Action allows the use of building line wildcard parameters for pBuildingId. The only wildcard parameter available is watch-tower-line. However, it is better to use watch-tower instead of watch-tower-line, even after Guard Tower or Keep upgrades due to some bugs with watch-tower-line. Simply using (build watch-tower) will work regardless of tower upgrades. Building classes cannot be used with this command. Important Note: Always use a can-build or up-can-build condition in every rule where you use the build-forward command. Without this condition, the building queue for this building may get stuck for the rest of the game. When this command is issued, the AI engine will add the specified building to the building placement queue. If snEnableNewBuildingSystem is set to 0, the engine will only add the building to the placement queue if there isn't already a building of the same type being constructed or waiting to be placed, but if the SN is set to 1 this check is removed, and an unlimited number of buildings of the same type are allowed to be queued for placement or be constructed at once. At the end of each script pass, the AI engine checks if the AI has explored the minimum percentage of the map required by snInitialExplorationRequired. If so, it will attempt to place each building that is currently in the placement queue. If the building was added to the queue with the build-forward command, the AI will place the building near the enemy player specified by snTargetPlayerNumber or the player specified by snAttackWinningPlayer if sn-target-player-number is set to 0. Buildings placed with build-forward will avoid placing the building on tiles where an enemy building already exists, and it will also avoid placing a building within any enemy building's line of sight, + 2 tiles.

[AIRef](https://airef.github.io/commands/commands-details.html#build-forward)

Completion insert text:

```text
(build-forward ${1:BuildingId})
```

