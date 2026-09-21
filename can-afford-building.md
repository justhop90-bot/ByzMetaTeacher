# `can-afford-building`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-can-afford-building"></a>

## `can-afford-building`

- Kind: `command`
- Detail: Fact - Buildings, Can Do

Syntax: `(can-afford-building <BuildingId>)`

Checks whether the computer player has enough resources to build the given building. It does not take into account resources in the escrow stockpiles. It does not check that the tech tree prerequisites are met or if the building is allowed for the civ. It allows the use of building line wildcard parameters for pBuildingId. The only wildcard parameter available is watch-tower-line. However, it is better to use watch-tower instead of watch-tower-line, even after Guard Tower or Keep upgrades due to some bugs with watch-tower-line. Simply using (can-afford-building watch-tower) will work regardless of tower upgrades. You cannot use building classes with this command.

[AIRef](https://airef.github.io/commands/commands-details.html#can-afford-building)

Completion insert text:

```text
(can-afford-building ${1:BuildingId})
```

