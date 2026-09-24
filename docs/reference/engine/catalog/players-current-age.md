# `players-current-age`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-players-current-age"></a>

## `players-current-age`

- Kind: `command`
- Detail: Fact - Other Player Info

Syntax: `(players-current-age <PlayerNumber> <compareOp> <Age>)`

Checks the given player's current age. The CPSB notes that this is equivalent to a human player checking the timeline, which was possible in-game in AoE1, and it was probably also possible during AoE2 development when the CPSB was written. Of course, this information is available to all players in-game, even without the timeline. The fact allows "focus-player", "target-player", and "any"/"every" wildcard parameters for pPlayerNumber. It also allows for scenario-player-# and lobby-player-#, where # is between 1 and 8. scenario-player-# refers to the player color (where red = scenario-player-2), and lobby-player-# refers to the player slot (where the lobby host or human player playing a single player campaign is always lobby-player-1).

[AIRef](https://airef.github.io/commands/commands-details.html#players-current-age)

Completion insert text:

```text
(players-current-age ${1:PlayerNumber} ${2:compareOp} ${3:Age})
```

