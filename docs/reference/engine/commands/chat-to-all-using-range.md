# `chat-to-all-using-range`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-chat-to-all-using-range"></a>

## `chat-to-all-using-range`

- Kind: `command`
- Detail: Action - Chat

Syntax: `(chat-to-all-using-range <LanguageId> <Value>)`

Sends a random string from a given range as a chat message to all players. The random string is defined by a string id randomly picked out of a given string id range. For more info on String ids, see the description of the pLanguageId parameter. For example, string ids from 22300 through 22321 include all of the possible random excuses the default AI can give for why it lost the game.

[AIRef](https://airef.github.io/commands/commands-details.html#chat-to-all-using-range)

Completion insert text:

```text
(chat-to-all-using-range ${1:LanguageId} ${2:Value})
```

