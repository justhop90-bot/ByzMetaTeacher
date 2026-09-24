# `player-resigned`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-player-resigned"></a>

## `player-resigned`

- Kind: `command`
- Detail: Fact - Other Player Info

Syntax: `(player-resigned <PlayerNumber>)`

Checks if the given player has lost by resigning. Note that a player can lose without resigning, so this fact should not be used to check whether a player has lost a game. To check whether a player has lost a game (such as player 3) use:(not (player-in-game 3))The fact allows "focus-player", "target-player", and "any"/"every" wildcard parameters for pPlayerNumber. It also allows for scenario-player-# and lobby-player-#, where # is between 1 and 8. scenario-player-# refers to the player color (where red = scenario-player-2), and lobby-player-# refers to the player slot (where the lobby host or human player playing a single player campaign is always lobby-player-1).

[AIRef](https://airef.github.io/commands/commands-details.html#player-resigned)

Completion insert text:

```text
(player-resigned ${1:PlayerNumber})
```

