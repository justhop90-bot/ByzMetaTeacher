# `build-wall`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-build-wall"></a>

## `build-wall`

- Kind: `command`
- Detail: Action - Buildings, Walls & Gates

Syntax: `(build-wall <Perimeter> <WallId>)`

Builds a wall line of the given wall type at the given perimeter if the wall type is available to the player and the wall can be constructed without escrowed resources. The given perimeter must first be enabled with enable-wall-placement. The Action allows the use of wall line wildcard parameters for pWallId. The only wall line wildcard parameter is stone-wall-line. Perimeter 1 is usually between 10 and 20 tiles from the starting Town Center. Perimeter 2 is usually between 18 and 30 tiles from the starting Town Center. If wall placement is enabled at a particular perimeter with enable-wall-placement, the AI engine will attempt to plan a roughly circular wall pattern within the given perimeter distances and construct the wall according to this pattern. This command cannot be used to rebuild parts of wall segments that existed at the start of the game, such as the starting walls in Arena or Fortress.

[AIRef](https://airef.github.io/commands/commands-details.html#build-wall)

Completion insert text:

```text
(build-wall ${1:Perimeter} ${2:WallId})
```

