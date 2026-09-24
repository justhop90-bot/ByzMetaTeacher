# `building-count-total`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-building-count-total"></a>

## `building-count-total`

- Kind: `command`
- Detail: Fact - Buildings, Counting

Syntax: `(building-count-total <compareOp> <Value>)`

Checks the computer player's total building count, either existing buildings or buildings under construction. Buildings that existed from the start of the game, such as the starting town center, are not included. Also, farms are included, but walls and gates are not included. To check for the building-count of other players, including buildings under construction, use players-building-count.

[AIRef](https://airef.github.io/commands/commands-details.html#building-count-total)

Completion insert text:

```text
(building-count-total ${1:compareOp} ${2:Value})
```

