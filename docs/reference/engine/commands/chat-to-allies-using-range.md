# `chat-to-allies-using-range`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-chat-to-allies-using-range"></a>

## `chat-to-allies-using-range`

- Kind: `command`
- Detail: Action - Chat

Syntax: `(chat-to-allies-using-range <LanguageId> <Value>)`

Sends a random string from a given range as a chat message to allies. The random string is defined by a string id randomly picked out of a given string id range. For more info on String ids, see the description of the pLanguageId parameter. For example, string ids from 22300 through 22321 include all of the possible random excuses the default AI can give for why it lost the game.

[AIRef](https://airef.github.io/commands/commands-details.html#chat-to-allies-using-range)

Completion insert text:

```text
(chat-to-allies-using-range ${1:LanguageId} ${2:Value})
```

