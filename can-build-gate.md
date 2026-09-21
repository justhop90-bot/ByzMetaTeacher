# `can-build-gate`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-can-build-gate"></a>

## `can-build-gate`

- Kind: `command`
- Detail: Fact - Buildings, Can Do, Walls & Gates

Syntax: `(can-build-gate <Perimeter>)`

Checks whether construction of a gate as part of the given perimeter wall can start. In non-DE versions, this command will only check if you can build stone gates. In DE, this command will check if you can build the gate type specified by snGateTypeForWall. Perimeter 1 is usually between 10 and 20 tiles from the starting Town Center. Perimeter 2 is usually between 18 and 30 tiles from the starting Town Center. If wall placement is enabled at a particular perimeter with enable-wall-placement, the AI engine will attempt to plan a roughly circular wall pattern within the given perimeter distances and construct the wall according to this pattern when the build-wall command is issued. Once the AI finds an appropriate location to build a gate within the given perimeter and the build-gate command is issued, the AI will replace four wall segments with a gate foundation. can-build-gate checks:It is available to the computer player's civ.Tech tree prerequisites are met.Required resources are available (not counting escrow resources).There is a location in an existing wall to build it.It will return false if it cannot fit a gate 3 tiles away from existing gates. In the DE version, to check if the AI can build palisade gates, set snGateTypeForWall to 1 before using this command.

[AIRef](https://airef.github.io/commands/commands-details.html#can-build-gate)

Completion insert text:

```text
(can-build-gate ${1:Perimeter})
```

