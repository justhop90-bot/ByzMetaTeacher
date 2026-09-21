# `player-human`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-player-human"></a>

## `player-human`

- Kind: `command`
- Detail: Fact - Other Player Info

Syntax: `(player-human <PlayerNumber>)`

Checks if the given player is a human player. The fact allows "my-player-number", "focus-player", "target-player", and "any"/"every" wildcard parameters for pPlayerNumber. It also allows for scenario-player-# and lobby-player-#, where # is between 1 and 8. scenario-player-# refers to the player color (where red = scenario-player-2), and lobby-player-# refers to the player slot (where the lobby host or human player playing a single player campaign is always lobby-player-1).

[AIRef](https://airef.github.io/commands/commands-details.html#player-human)

Completion insert text:

```text
(player-human ${1:PlayerNumber})
```

