# `chat-to-player`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-chat-to-player"></a>

## `chat-to-player`

- Kind: `command`
- Detail: Action - Chat, Debugging

Syntax: `(chat-to-player <PlayerNumber> <String>)`

Sends a given string as a chat message to a given player. If the chat message string starts with numerals, that number will be sent as a taunt to the specified player and the starting numerals will be removed from the message. For example, "1 TC" will send taunt 1 to the specified player and send the message " TC" to the specified player. The fact allows "my-player-number", "focus-player", "target-player", and "any"/"every" wildcard parameters for pPlayerNumber. It also allows for scenario-player-# and lobby-player-#, where # is between 1 and 8. scenario-player-# refers to the player color (where red = scenario-player-2), and lobby-player-# refers to the player slot (where the lobby host or human player playing a single player campaign is always lobby-player-1). It also allows the use of rule variables for pPlayerNumber, such as "this-any-ally" or "this-any-enemy".

[AIRef](https://airef.github.io/commands/commands-details.html#chat-to-player)

Completion insert text:

```text
(chat-to-player ${1:PlayerNumber} ${2:String})
```

