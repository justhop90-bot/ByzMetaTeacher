# `players-building-type-count`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-players-building-type-count"></a>

## `players-building-type-count`

- Kind: `command`
- Detail: Fact - Buildings, Cheat, Counting, Other Player Info

Syntax: `(players-building-type-count <PlayerNumber> <BuildingId> <compareOp> <Value>)`

A cheating version of players-building-type-count. This command works even if cheats are disabled. For use in scenarios only. This fact checks the given player's building count for the given building. Both existing buildings and buildings under construction of the given type are included regardless of whether they have been seen - fog is ignored. The Fact allows "focus-player", "target-player", "any"/"every" wildcard parameters for pPlayerNumber. It also allows for scenario-player-# and lobby-player-#, where # is between 1 and 8. scenario-player-# refers to the player color (where red = scenario-player-2), and lobby-player-# refers to the player slot (where the lobby host or human player playing a single player campaign is always lobby-player-1). It also allows the use of building line wildcard parameters for pBuildingId. The only wildcard parameter available is watch-tower-line. However, it is better to use watch-tower instead of watch-tower-line, even after Guard Tower or Keep upgrades due to some bugs with watch-tower-line. Simply using (cc-players-building-type-count any-enemy watch-tower > 0) will work regardless of tower upgrades. There are four ways you can specify the building "type":Building Name: the name of an individual building, such as house, watch-tower, or town-center.Building Id: the numerical ID assigned to each building, such as 12 (the barracks) or 70 (the house). See the ID column in the Objects Table for a list.Building Line: the building line for the building. The only option here is watch-tower-line, and avoid using it as there are various bugs with it. Simply use watch-tower instead.Building Class: the class of a building, such as building-class, tower-class, or farm-class. Classes group several building types together into a single category. Using a building class will count all buildings of this class. See the Class column in the Objects Table to see each building's class. Classes don't work for enemy players with players-building-type-count, but they do work with cc-players-building-type-count.

[AIRef](https://airef.github.io/commands/commands-details.html#players-building-type-count)

Completion insert text:

```text
(players-building-type-count ${1:PlayerNumber} ${2:BuildingId} ${3:compareOp} ${4:Value})
```

