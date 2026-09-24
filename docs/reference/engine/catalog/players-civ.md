# `players-civ`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-players-civ"></a>

## `players-civ`

- Kind: `command`
- Detail: Fact - Other Player Info

Syntax: `(players-civ <PlayerNumber> <Civ>)`

Checks the given player's civilization. Note that the civilization names used with this command for pre-DE civs are usually different than the civ's display name. They are like the pLoadIfSymbol civ names where they often use the adjective form of the civ name, not the plural name. See pCiv for a list of correct civ names to use with this command. The fact allows "focus-player", "target-player", and "any"/"every" wildcard parameters for pPlayerNumber. It also allows for scenario-player-# and lobby-player-#, where # is between 1 and 8. scenario-player-# refers to the player color (where red = scenario-player-2), and lobby-player-# refers to the player slot (where the lobby host or human player playing a single player campaign is always lobby-player-1). You can use "my-civ" for the Civ parameter, which will automatically detect the civilization the AI is playing as.

[AIRef](https://airef.github.io/commands/commands-details.html#players-civ)

Completion insert text:

```text
(players-civ ${1:PlayerNumber} ${2:Civ})
```

