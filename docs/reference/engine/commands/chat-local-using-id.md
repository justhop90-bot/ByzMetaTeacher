# `chat-local-using-id`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-chat-local-using-id"></a>

## `chat-local-using-id`

- Kind: `command`
- Detail: Action - Chat

Syntax: `(chat-local-using-id <LanguageId>)`

Displays a string, defined by a string id, as a local chat message to all players. For more info on String ids, see the description of the pLanguageId parameter. For example, string id 22322 in English is "No wonder thou wert victorious! I shalt abdicate." Local chat messages display chat messages in white rather than with the AI's player color, making this command strictly inferior to chat-to-all-using-id.

[AIRef](https://airef.github.io/commands/commands-details.html#chat-local-using-id)

Completion insert text:

```text
(chat-local-using-id ${1:LanguageId})
```

