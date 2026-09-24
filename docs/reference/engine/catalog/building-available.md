# `building-available`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-building-available"></a>

## `building-available`

- Kind: `command`
- Detail: Fact - Buildings, Can Do

Syntax: `(building-available <BuildingId>)`

Checks that the building is available to the computer player's civ and that the tech tree prerequisites are met. It does not check that there are enough resources to build the building. It allows the use of building line wildcard parameters for pBuildingId. The only wildcard parameter available is watch-tower-line. However, it is better to use watch-tower instead of watch-tower-line, even after Guard Tower or Keep upgrades due to some bugs with watch-tower-line. Simply using (building-available watch-tower) will work regardless of tower upgrades. You cannot use building classes with this command. When the AI checks the tech tree prerequisites, this includes checking whether the prerequisite age has been researched. There isn't a way at the beginning of the game to check if the building will be available for the civilization in future ages.

[AIRef](https://airef.github.io/commands/commands-details.html#building-available)

Completion insert text:

```text
(building-available ${1:BuildingId})
```

