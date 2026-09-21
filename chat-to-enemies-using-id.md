# `chat-to-enemies-using-id`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-chat-to-enemies-using-id"></a>

## `chat-to-enemies-using-id`

- Kind: `command`
- Detail: Action - Chat

Syntax: `(chat-to-enemies-using-id <LanguageId>)`

sends a string, defined by a string id, as a chat message to enemy players. For more info on String ids, see the description of the pLanguageId parameter. For example, string id 22322 in English is "No wonder thou wert victorious! I shalt abdicate."

[AIRef](https://airef.github.io/commands/commands-details.html#chat-to-enemies-using-id)

Completion insert text:

```text
(chat-to-enemies-using-id ${1:LanguageId})
```

