# `build-gate`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-build-gate"></a>

## `build-gate`

- Kind: `command`
- Detail: Action - Buildings, Walls & Gates

Syntax: `(build-gate <Perimeter>)`

Builds a gate as part of the given perimeter wall if the gate is available to the player and the gate can be constructed without escrowed resources. The given perimeter must first be enabled with enable-wall-placement. Perimeter 1 is usually between 10 and 20 tiles from the starting Town Center. Perimeter 2 is usually between 18 and 30 tiles from the starting Town Center. If wall placement is enabled at a particular perimeter with enable-wall-placement, the AI engine will attempt to plan a roughly circular wall pattern within the given perimeter distances when the build-wall command is issued. Once the AI finds an appropriate location to build a gate within the given perimeter and the build-gate command is issued, the AI will replace four wall segments with a gate foundation. This command cannot be used to build a gate within wall segments that existed at the start of the game, such as the starting walls in Arena or Fortress. In the DE version you can build palisade gates by setting snGateTypeForWall to 1 before using this command.

[AIRef](https://airef.github.io/commands/commands-details.html#build-gate)

Completion insert text:

```text
(build-gate ${1:Perimeter})
```

