# `can-afford-complete-wall`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-can-afford-complete-wall"></a>

## `can-afford-complete-wall`

- Kind: `command`
- Detail: Fact - Walls & Gates, Can Do

Syntax: `(can-afford-complete-wall <Perimeter> <WallId>)`

Checks whether the computer player has enough resources to finish the given wall type at the pPerimeter. Perimeter 1 is usually between 10 and 20 tiles from the starting Town Center. Perimeter 2 is usually between 18 and 30 tiles from the starting Town Center. If wall placement is enabled at a particular perimeter with enable-wall-placement, the AI engine will attempt to plan a roughly circular wall pattern within the given perimeter distances and construct the wall according to this pattern when the build-wall command is issued. In particular, can-afford-complete-wall checks:The wall type is available to the computer player's civ.The tech tree prerequisites are met.Required resources are available.It does not take into account escrowed resources. It does not check if wall area is explored or if enable-wall-placement has been used. pPerimeter is either: '1' for a 10-20 tile radius aroung home TC or '2' for an 18-30 tile radius.

[AIRef](https://airef.github.io/commands/commands-details.html#can-afford-complete-wall)

Completion insert text:

```text
(can-afford-complete-wall ${1:Perimeter} ${2:WallId})
```

