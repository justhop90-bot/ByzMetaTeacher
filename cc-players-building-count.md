# `cc-players-building-count`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-cc-players-building-count"></a>

## `cc-players-building-count`

- Kind: `command`
- Detail: Fact - Buildings, Cheat, Counting, Other Player Info

Syntax: `(cc-players-building-count <PlayerNumber> <compareOp> <Value>)`

A cheating version of players-building-count. This command works even if cheats are disabled. For use in scenarios only. The fact checks the given player's building count. Both existing buildings and buildings under construction are included regardless of whether they have been seen - fog is ignored. Unlike building-count, buildings that existed from the start of the game, such as the starting town center, are included. Also, farms are included, but walls and gates are not included. The Fact allows "focus-player", "target-player", and "any"/"every" wildcard parameters for pPlayerNumber. It also allows for scenario-player-# and lobby-player-#, where # is between 1 and 8. scenario-player-# refers to the player color (where red = scenario-player-2), and lobby-player-# refers to the player slot (where the lobby host or a human player playing a single player campaign is always lobby-player-1).

[AIRef](https://airef.github.io/commands/commands-details.html#cc-players-building-count)

Completion insert text:

```text
(cc-players-building-count ${1:PlayerNumber} ${2:compareOp} ${3:Value})
```

