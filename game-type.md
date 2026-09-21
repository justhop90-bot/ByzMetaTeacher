# `game-type`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-game-type"></a>

## `game-type`

- Kind: `command`
- Detail: Fact - Game Info

Syntax: `(game-type <compareOp> <GameType>)`

Checks the game type. Game types include settings like random-map, regicide, king-of-the-hill, or turbo-random-map. See pGameType for the list of game types. Game types are not defined, so you must defconst them before using them.

[AIRef](https://airef.github.io/commands/commands-details.html#game-type)

Completion insert text:

```text
(game-type ${1:compareOp} ${2:GameType})
```

