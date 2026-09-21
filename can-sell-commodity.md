# `can-sell-commodity`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-can-sell-commodity"></a>

## `can-sell-commodity`

- Kind: `command`
- Detail: Fact - Can Do, Economy, Trading

Syntax: `(can-sell-commodity <Commodity>)`

Checks whether the computer player can sell one lot (100 resources) of the given commodity (food, wood, or stone). The fact does not take into account escrowed resources. In other words, this checks if the AI has a market and has at least 100 of the specified commodity that it can sell for gold.

[AIRef](https://airef.github.io/commands/commands-details.html#can-sell-commodity)

Completion insert text:

```text
(can-sell-commodity ${1:Commodity})
```

