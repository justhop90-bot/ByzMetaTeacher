# `chat-to-player-using-id`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-chat-to-player-using-id"></a>

## `chat-to-player-using-id`

- Kind: `command`
- Detail: Action - Chat

Syntax: `(chat-to-player-using-id <PlayerNumber> <LanguageId>)`

sends a string, defined by a string id, as a chat message to a given player. For more info on String ids, see the description of the pLanguageId parameter. For example, string id 22322 in English is "No wonder thou wert victorious! I shalt abdicate." The action allows "my-player-number", "focus-player", "target-player", and "any"/"every" wildcard parameters for pPlayerNumber. It also allows for scenario-player-# and lobby-player-#, where # is between 1 and 8. scenario-player-# refers to the player color (where red = scenario-player-2), and lobby-player-# refers to the player slot (where the lobby host or human player playing a single player campaign is always lobby-player-1). It also allows the use of rule variables for pPlayerNumber, such as "this-any-ally" or "this-any-enemy".

[AIRef](https://airef.github.io/commands/commands-details.html#chat-to-player-using-id)

Completion insert text:

```text
(chat-to-player-using-id ${1:PlayerNumber} ${2:LanguageId})
```

