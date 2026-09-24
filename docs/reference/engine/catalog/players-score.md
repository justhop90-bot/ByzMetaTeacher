# `players-score`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-players-score"></a>

## `players-score`

- Kind: `command`
- Detail: Fact - Other Player Info

Syntax: `(players-score <PlayerNumber> <compareOp> <Value>)`

Checks the given player's current score. The fact allows "focus-player", "target-player", and "any"/"every" wildcard parameters for pPlayerNumber. It also allows for scenario-player-# and lobby-player-#, where # is between 1 and 8. scenario-player-# refers to the player color (where red = scenario-player-2), and lobby-player-# refers to the player slot (where the lobby host or human player playing a single player campaign is always lobby-player-1).

[AIRef](https://airef.github.io/commands/commands-details.html#players-score)

Completion insert text:

```text
(players-score ${1:PlayerNumber} ${2:compareOp} ${3:Value})
```

