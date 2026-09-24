# `player-valid`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-player-valid"></a>

## `player-valid`

- Kind: `command`
- Detail: Fact - Other Player Info

Syntax: `(player-valid <PlayerNumber>)`

Checks if the given player is a valid player, meaning the player slot was used during the game. In games with more than 2 players, players that lost before the game is over are still considered to be valid players. This is because although the player is not in the game, their units/buildings can still be in the game. To check whether the given player is still in the game use the player-in-game fact. The fact allows "focus-player", "target-player", and "any"/"every" wildcard parameters for pPlayerNumber. It also allows for scenario-player-# and lobby-player-#, where # is between 1 and 8. scenario-player-# refers to the player color (where red = scenario-player-2), and lobby-player-# refers to the player slot (where the lobby host or human player playing a single player campaign is always lobby-player-1).

[AIRef](https://airef.github.io/commands/commands-details.html#player-valid)

Completion insert text:

```text
(player-valid ${1:PlayerNumber})
```

