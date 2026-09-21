# `chat-to-allies`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-chat-to-allies"></a>

## `chat-to-allies`

- Kind: `command`
- Detail: Action - Chat

Syntax: `(chat-to-allies <String>)`

Sends a given string as a chat message to allies. If the chat message string starts with numerals, that number will be sent as a taunt to all allies and the starting numerals will be removed from the message. For example, "1 TC" will send taunt 1 to all allies and send the message " TC" to all allies.

[AIRef](https://airef.github.io/commands/commands-details.html#chat-to-allies)

Completion insert text:

```text
(chat-to-allies ${1:String})
```

