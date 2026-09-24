# `chat-local-to-self`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-chat-local-to-self"></a>

## `chat-local-to-self`

- Kind: `command`
- Detail: Action - Chat, Debugging

Syntax: `(chat-local-to-self <String>)`

Displays a given string (a message in quotation marks) as local chat message. The message is displayed only if the user is the same player as the computer player sending the message. For debugging purposes only. Local chat messages display chat messages in white rather than with the AI's player color, making this command strictly inferior to chat-to-player with my-player-number as the player Id. If the chat message string starts with numerals, that number will be sent as a taunt to self and the starting numerals will be removed from the message. For example, "1 TC" will send taunt 1 to self and send the message " TC" to self.

[AIRef](https://airef.github.io/commands/commands-details.html#chat-local-to-self)

Completion insert text:

```text
(chat-local-to-self ${1:String})
```

