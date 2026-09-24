# `resource-found`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-resource-found"></a>

## `resource-found`

- Kind: `command`
- Detail: Fact - Economy

Syntax: `(resource-found <Resource>)`

Checks whether the computer player has found the given resource. For food, gold, and stone (not wood), the given resource must be within the dropsite's max distance for this command to be true (snMillMaxDistance for food and snMiningCampMaxDistance or snCampMaxDistance for gold and stone). The fact should be used at the beginning period of the game. Once it becomes true for a certain resource it stays true for that resource. Only forests, not straggler trees, will make resource-found true for wood. Also, only forage bushes will make resource-found true for food. Using up-gaia-type-count, up-gaia-type-count-total, or dropsite-min-distance are often better commands to use than resource-found because they can count how many of the given resource have been found or determine how far away the resources are.

[AIRef](https://airef.github.io/commands/commands-details.html#resource-found)

Completion insert text:

```text
(resource-found ${1:Resource})
```

