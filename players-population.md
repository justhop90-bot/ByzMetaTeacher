# `players-population`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-players-population"></a>

## `players-population`

- Kind: `command`
- Detail: Fact - Counting, Other Player Info

Syntax: `(players-population <PlayerNumber> <compareOp> <Value>)`

Checks the given player's population. This fact includes seen and unseen units for the given player. This command counts Karambit Warriors as 1 population, rather than 0.5 population. The CPSB notes that this is equivalent to a human player checking the timeline, which was possible in-game in AoE1, and it was probably also possible during AoE2 development when the CPSB was written, hence why this isn't regarded as a cc- cheating command. However, since this command includes unseen units, some consider this command to be cheating when it's used to check enemy population, but the AI scripting community permits this command in AI tournaments for historical reasons. When checking for the population of an enemy player, consider using players-unit-count. players-unit-count can overestimate enemy unit counts, but it doesn't count unseen units. The fact allows "focus-player", "target-player", and "any"/"every" wildcard parameters for pPlayerNumber. It also allows for scenario-player-# and lobby-player-#, where # is between 1 and 8. scenario-player-# refers to the player color (where red = scenario-player-2), and lobby-player-# refers to the player slot (where the lobby host or human player playing a single player campaign is always lobby-player-1).

[AIRef](https://airef.github.io/commands/commands-details.html#players-population)

Completion insert text:

```text
(players-population ${1:PlayerNumber} ${2:compareOp} ${3:Value})
```

