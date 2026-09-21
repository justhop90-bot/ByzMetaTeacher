# `can-afford-unit`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-can-afford-unit"></a>

## `can-afford-unit`

- Kind: `command`
- Detail: Fact - Units, Can Do

Syntax: `(can-afford-unit <UnitId>)`

Checks whether the computer player has enough resources to train the given unit. Does not check anything else. The fact does not take into account escrowed resources. The fact allows the use of unit line wildcard parameters for pUnitId. These wildcard parameters allow you to specify a unit line rather than an individual unit in the unit line. You cannot use unit classes with this command. my-unique-unit, my-elite-unique-unit, and my-unique-unit-line can also be used, which will automatically get the UnitId of the unique unit, elite unique unit, or unique unit line that the AI's civ can train from the castle.

[AIRef](https://airef.github.io/commands/commands-details.html#can-afford-unit)

Completion insert text:

```text
(can-afford-unit ${1:UnitId})
```

