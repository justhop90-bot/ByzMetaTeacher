# `can-build-wall`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-can-build-wall"></a>

## `can-build-wall`

- Kind: `command`
- Detail: Fact - Buildings, Can Do, Walls & Gates

Syntax: `(can-build-wall <Perimeter> <WallId>)`

Checks whether a given wall type can be built at the given perimeter without escrowed resources. Perimeter 1 is usually between 10 and 20 tiles from the starting Town Center. Perimeter 2 is usually between 18 and 30 tiles from the starting Town Center. If wall placement is enabled at a particular perimeter with enable-wall-placement, the AI engine will attempt to plan a roughly circular wall pattern within the given perimeter distances and construct the wall according to this pattern when the build-wall command is issued. In particular, can-build-wall checks:The wall type is available to the computer player's civ.Tech tree prerequisites are met.There is a location to build a wall.Required resources are available, not counting escrow amounts.This fact checks that there is enough stone for at least 5 wall pieces, whereas can-afford-complete-wall checks if there is enough stone for the entire wall. The fact allows the use of wall line wildcard parameters for pWallId. The only available wall line wildcard parameter is stone-wall-line. Note you are allowed to enable wall placement at both perimeters.

[AIRef](https://airef.github.io/commands/commands-details.html#can-build-wall)

Completion insert text:

```text
(can-build-wall ${1:Perimeter} ${2:WallId})
```

