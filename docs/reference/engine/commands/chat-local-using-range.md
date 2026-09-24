# `chat-local-using-range`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-chat-local-using-range"></a>

## `chat-local-using-range`

- Kind: `command`
- Detail: Action - Chat

Syntax: `(chat-local-using-range <LanguageId> <Value>)`

Displays a random string from a given range as a local chat message to all players. The random string is defined by a string id randomly picked out of a given string id range. For more info on String ids, see the description of the pLanguageId parameter. For example, string ids from 22300 through 22321 include all of the possible random excuses the default AI can give for why it lost the game. Local chat messages display chat messages in white rather than with the AI's player color, making this command strictly inferior to chat-to-all-using-range.

[AIRef](https://airef.github.io/commands/commands-details.html#chat-local-using-range)

Completion insert text:

```text
(chat-local-using-range ${1:LanguageId} ${2:Value})
```

