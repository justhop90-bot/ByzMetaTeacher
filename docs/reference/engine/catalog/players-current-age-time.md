# `players-current-age-time`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-players-current-age-time"></a>

## `players-current-age-time`

- Kind: `command`
- Detail: Fact - Other Player Info

Syntax: `(players-current-age-time <PlayerNumber> <compareOp> <Value>)`

Checks the given player's current age time -- time spent in the current age. The CPSB notes that this is equivalent to a human player checking the timeline, which was possible in-game in AoE1, and it was probably also possible during AoE2 development when the CPSB was written. Of course, this information could be calculated in-game even without using the timeline. The fact allows "focus-player", "target-player", and "any"/"every" wildcard parameters for pPlayerNumber. It also allows for scenario-player-# and lobby-player-#, where # is between 1 and 8. scenario-player-# refers to the player color (where red = scenario-player-2), and lobby-player-# refers to the player slot (where the lobby host or human player playing a single player campaign is always lobby-player-1).

[AIRef](https://airef.github.io/commands/commands-details.html#players-current-age-time)

Completion insert text:

```text
(players-current-age-time ${1:PlayerNumber} ${2:compareOp} ${3:Value})
```

