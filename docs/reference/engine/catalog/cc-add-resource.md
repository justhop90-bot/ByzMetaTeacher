# `cc-add-resource`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-cc-add-resource"></a>

## `cc-add-resource`

- Kind: `command`
- Detail: Action - Cheat, Economy

Syntax: `(cc-add-resource <Resource> <Value>)`

A cheating action that adds the given resource amount to the computer player. This command works even if cheats are disabled. It is to be used in scenarios to avoid late game oddities such as computer player villagers going all over the map while looking for the last pile of gold. Negative amounts can be used to remove resources from the computer player's stockpile.

[AIRef](https://airef.github.io/commands/commands-details.html#cc-add-resource)

Completion insert text:

```text
(cc-add-resource ${1:Resource} ${2:Value})
```

