# `gate-count`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-gate-count"></a>

## `gate-count`

- Kind: `command`
- Detail: Fact - Buildings, Counting

Syntax: `(gate-count <Perimeter> <compareOp> <Value>)`

Checks for the number of gates that are either being built or are completed at the given perimeter. Perimeter 1 is usually between 10 and 20 tiles from the starting Town Center. Perimeter 2 is usually between 18 and 30 tiles from the starting Town Center. This command likely only counts stone gates, but it is possible that you can count only palisade gates instead by setting snGateTypeForWall to 1 before using gate-count.

[AIRef](https://airef.github.io/commands/commands-details.html#gate-count)

Completion insert text:

```text
(gate-count ${1:Perimeter} ${2:compareOp} ${3:Value})
```

