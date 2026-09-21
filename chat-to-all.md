# `chat-to-all`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-chat-to-all"></a>

## `chat-to-all`

- Kind: `command`
- Detail: Action - Chat, Debugging

Syntax: `(chat-to-all <String>)`

Sends a given string (a message in quotation marks) as a chat message to all players. If the chat message string starts with numerals, that number will be sent as a taunt to all players and the starting numerals will be removed from the message. For example, "1 TC" will send taunt 1 to all players and send the message " TC" to all players.

[AIRef](https://airef.github.io/commands/commands-details.html#chat-to-all)

Completion insert text:

```text
(chat-to-all ${1:String})
```

