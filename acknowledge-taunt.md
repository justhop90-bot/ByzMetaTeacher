# `acknowledge-taunt`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-acknowledge-taunt"></a>

## `acknowledge-taunt`

- Kind: `command`
- Detail: Action - Chat, Debugging, Other Player Info

Syntax: `(acknowledge-taunt <PlayerNumber> <TauntId>)`

Acknowledges the taunt (resets the flag). Like other event systems in the AI, taunt detection requests explicit acknowledgement. In simple terms, whenever an AI receives a taunt message, taunt-detected will remain true for the given taunt until the taunt is acknowledged. If the taunt is not acknowledged, your AI's response to the taunt will happen repeatedly. The action allows "focus-player", "target-player", and "any"/"every" wildcard parameters for pPlayerNumber. It also allows the use of rule variables for pPlayerNumber, such as "this-any-ally" or "this-any-enemy". It also allows for scenario-player-# and lobby-player-#, where # is between 1 and 8. scenario-player-# refers to the player color (where red = scenario-player-2), and lobby-player-# refers to the player slot (where the lobby host or human player playing a single player campaign is always lobby-player-1).

[AIRef](https://airef.github.io/commands/commands-details.html#acknowledge-taunt)

Completion insert text:

```text
(acknowledge-taunt ${1:PlayerNumber} ${2:TauntId})
```

