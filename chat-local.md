# `chat-local`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-chat-local"></a>

## `chat-local`

- Kind: `command`
- Detail: Action - Chat, Debugging

Syntax: `(chat-local <String>)`

Displays the given string (a message in quotation marks) as a local chat message to all players. Local chat messages display chat messages in white rather than with the AI's player color, making this command strictly inferior to chat-to-all. If the chat message string starts with numerals, that number will be sent as a taunt to all players and the starting numerals will be removed from the message. For example, "1 TC" will send taunt 1 to all players and send the message " TC" to all players.

[AIRef](https://airef.github.io/commands/commands-details.html#chat-local)

Completion insert text:

```text
(chat-local ${1:String})
```

