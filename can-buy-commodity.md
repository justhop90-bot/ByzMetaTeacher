# `can-buy-commodity`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-can-buy-commodity"></a>

## `can-buy-commodity`

- Kind: `command`
- Detail: Fact - Can Do, Economy, Trading

Syntax: `(can-buy-commodity <Commodity>)`

Checks whether the computer player can buy one lot (100 resources) of the given commodity (food, wood, or stone). The fact does not take into account escrowed resources. In other words, this checks if the AI has a market and enough gold at the current buying price for the specified commodity to be able to buy 100 of the specified commodity.

[AIRef](https://airef.github.io/commands/commands-details.html#can-buy-commodity)

Completion insert text:

```text
(can-buy-commodity ${1:Commodity})
```

