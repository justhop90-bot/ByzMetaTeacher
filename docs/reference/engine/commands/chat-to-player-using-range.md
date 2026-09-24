# `chat-to-player-using-range`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-chat-to-player-using-range"></a>

## `chat-to-player-using-range`

- Kind: `command`
- Detail: Action - Chat

Syntax: `(chat-to-player-using-range <PlayerNumber> <LanguageId> <Value>)`

Sends a random string from a given range as a chat message to a given player. The random string is defined by a string id randomly picked out of a given string id range. For more info on String ids, see the description of the pLanguageId parameter. For example, string ids from 22300 through 22321 include all of the possible random excuses the default AI can give for why it lost the game. The Action allows "my-player-number", "focus-player", "target-player", and "any"/"every" wildcard parameters for pPlayerNumber. It also allows the use of rule variables for pPlayerNumber, such as "this-any-ally" or "this-any-enemy". It also allows for scenario-player-# and lobby-player-#, where # is between 1 and 8. scenario-player-# refers to the player color (where red = scenario-player-2), and lobby-player-# refers to the player slot (where the lobby host or human player playing a single player campaign is always lobby-player-1).

[AIRef](https://airef.github.io/commands/commands-details.html#chat-to-player-using-range)

Completion insert text:

```text
(chat-to-player-using-range ${1:PlayerNumber} ${2:LanguageId} ${3:Value})
```

