# `chat-to-enemies`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-chat-to-enemies"></a>

## `chat-to-enemies`

- Kind: `command`
- Detail: Action - Chat

Syntax: `(chat-to-enemies <String>)`

Sends a given string as a chat message to enemies. If the chat message string starts with numerals, that number will be sent as a taunt to all enemies and the starting numerals will be removed from the message. For example, "1 TC" will send taunt 1 to all enemies and send the message " TC" to all enemies.

[AIRef](https://airef.github.io/commands/commands-details.html#chat-to-enemies)

Completion insert text:

```text
(chat-to-enemies ${1:String})
```

