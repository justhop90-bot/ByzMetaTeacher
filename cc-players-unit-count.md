# `cc-players-unit-count`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-cc-players-unit-count"></a>

## `cc-players-unit-count`

- Kind: `command`
- Detail: Fact - Cheat, Counting, Other Player Info, Units

Syntax: `(cc-players-unit-count <PlayerNumber> <compareOp> <Value>)`

A cheating version of players-unit-count. This command works even if cheats are disabled. For use in scenarios only. This fact checks the given player's unit count. Only trained units are included and fog is ignored. The Fact allows "focus-player", "target-player", and "any"/"every" wildcard parameters for pPlayerNumber. It also allows for scenario-player-# and lobby-player-#, where # is between 1 and 8. scenario-player-# refers to the player color (where red = scenario-player-2), and lobby-player-# refers to the player slot (where the lobby host or human player playing a single player campaign is always lobby-player-1).

[AIRef](https://airef.github.io/commands/commands-details.html#cc-players-unit-count)

Completion insert text:

```text
(cc-players-unit-count ${1:PlayerNumber} ${2:compareOp} ${3:Value})
```

