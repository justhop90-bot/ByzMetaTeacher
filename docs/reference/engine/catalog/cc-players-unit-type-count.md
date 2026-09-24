# `cc-players-unit-type-count`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-cc-players-unit-type-count"></a>

## `cc-players-unit-type-count`

- Kind: `command`
- Detail: Fact - Cheat, Counting, Other Player Info, Units

Syntax: `(cc-players-unit-type-count <PlayerNumber> <UnitId> <compareOp> <Value>)`

A cheating version of players-unit-type-count. This command works even if cheats are disabled. For use in scenarios only, though most AI tournaments allows its use to see if particular Gaia objects are on the map at the beginning of the game, for custom map detection purposes. For example, some scripts will check to see if fish are on the map to detect if the map is a water map. This fact checks the given player's unit count. Only trained units of the given type are included and fog is ignored. The Fact allows "focus-player", "target-player", and "any"/"every" wildcard parameters for pPlayerNumber. It also allows for scenario-player-# and lobby-player-#, where # is between 1 and 8. scenario-player-# refers to the player color (where red = scenario-player-2), and lobby-player-# refers to the player slot (where the lobby host or human player playing a single player campaign is always lobby-player-1). Counting Gaia units (player number 0) is not considered cheating. There are four ways you can specify the unit "type":Unit Name: the name of an individual unit, such as villager, spearman, or monk.Unit Id: the numerical ID assigned to each unit, such as 4 (the archer) or 74 (militiaman). See the ID column in the Objects Table for a list.Unit Line: the unit line for the unit. This includes all units in a unit line. For example, archer-line includes archers, crossbowmen, and arbalests.Unit Class: the class of a unit, such as infantry-class, cavalry-archer-class, or monastery-class. Classes group several unit types together into a single category. Using a unit class will count all units of this class. See the Class column in the Objects Table to see each unit's class. Classes don't work for enemy players with players-unit-type-count, but they do work with cc-players-unit-type-count.

[AIRef](https://airef.github.io/commands/commands-details.html#cc-players-unit-type-count)

Completion insert text:

```text
(cc-players-unit-type-count ${1:PlayerNumber} ${2:UnitId} ${3:compareOp} ${4:Value})
```

