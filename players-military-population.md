# `players-military-population`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-players-military-population"></a>

## `players-military-population`

- Kind: `command`
- Detail: Fact - Counting, Other Player Info, Units

Syntax: `(players-military-population <PlayerNumber> <compareOp> <Value>)`

Checks the given player's military population, which includes all units except for villagers, fishing ships, trade units, and kings. This fact includes seen and unseen military units for the given player. This command counts Karambit Warriors as 1 population, rather than 0.5 population. The CPSB notes that this is equivalent to a human player checking the timeline, which was possible in-game in AoE1, and it was probably also possible during AoE2 development when the CPSB was written, hence why this isn't regarded as a cc- cheating command. However, since this command includes unseen military units, some consider this command to be cheating when it's used to check enemy military population, but the AI scripting community permits this command in AI tournaments for historical reasons. The fact allows "focus-player", "target-player", and "any"/"every" wildcard parameters for pPlayerNumber. It also allows for scenario-player-# and lobby-player-#, where # is between 1 and 8. scenario-player-# refers to the player color (where red = scenario-player-2), and lobby-player-# refers to the player slot (where the lobby host or human player playing a single player campaign is always lobby-player-1).

[AIRef](https://airef.github.io/commands/commands-details.html#players-military-population)

Completion insert text:

```text
(players-military-population ${1:PlayerNumber} ${2:compareOp} ${3:Value})
```

