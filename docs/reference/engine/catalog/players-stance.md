# `players-stance`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-players-stance"></a>

## `players-stance`

- Kind: `command`
- Detail: Fact - Diplomacy, Other Player Info

Syntax: `(players-stance <PlayerNumber> <PlayerStance>)`

Checks if the given player's diplomatic stance toward the computer player matches the give stance, either ally, neutral, or enemy. To check our stance toward another player, use stance-toward. The fact allows "focus-player", "target-player", and "any"/"every" wildcard parameters for pPlayerNumber. It also allows for scenario-player-# and lobby-player-#, where # is between 1 and 8. scenario-player-# refers to the player color (where red = scenario-player-2), and lobby-player-# refers to the player slot (where the lobby host or human player playing a single player campaign is always lobby-player-1).

[AIRef](https://airef.github.io/commands/commands-details.html#players-stance)

Completion insert text:

```text
(players-stance ${1:PlayerNumber} ${2:PlayerStance})
```

