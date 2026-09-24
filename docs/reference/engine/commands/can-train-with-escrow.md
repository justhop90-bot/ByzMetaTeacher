# `can-train-with-escrow`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-can-train-with-escrow"></a>

## `can-train-with-escrow`

- Kind: `command`
- Detail: Fact - Can Do, Units

Syntax: `(can-train-with-escrow <UnitId>)`

Checks that the training of a given unit can start. You cannot use unit classes with this command. my-unique-unit, my-elite-unique-unit, and my-unique-unit-line can also be used, which will automatically get the UnitId of the unique unit, elite unique unit, or unique unit line that the AI's civ can train from the castle. In particular it checks:The unit is available to the computer player's civ.Tech tree prerequisites are met.Required resources are available including escrow stockpiles.There is enough housing headroom for the unit.There is an appropriate building that is not busy and is ready to start training the unit.The fact allows the use of unit line wildcard parameters for pUnitId, which means that you can use (can-train-with-escrow spearman-line), instead of (can-train-with-escrow spearman). Interestingly, you can safely use the base unit of a unit line with this command instead of the unit line version, and it will work regardless of any upgrades that have been researched. For example, you can safely use (can-train-with-escrow archer) even if Crossbowman has been researched. This capability is important if you are scripting for WololoKingdoms (WK) or any other mod where some unit lines aren't defined in the AI engine. Unique units can be trained dynamically by using my-unique-unit or my-unique-unit-line as long as your aren't scripting for a Userpatch modpack like WK. You can also train by the unit ID rather than the unit name. You can see all units and their unit IDs in the Objects table. In WK, there are two units that use a separate placeholder unit ID for training purposes, and you must use it for all can-train, can-train-with-escrow, train, up-can-train, and up-train commands. These units are the condottiero and genitour. Use ID 184 for condottiero-placeholder and use ID 732 for genitour-placeholder. You cannot check for the ability to train units with unit classes (like infantry-class) or with sets (like huskarl-set, which includes castle huskarls and barracks huskarls). To check for units like huskarls or tarkans that can be trained at multiple buildings, you must each each unit type separately, such as (or (can-train-with-escrow huskarl) (can-train-with-escrow barracks-huskarl)). To check if mercenary kipchaks (elite kipchaks that allies can train after Cuman Mercenaries is researched) can be trained, use "mercenary-kipchak" rather than kipchak-line. This fact will return false if the setting of snDockTrainingFilter currently restricts the training of ships.

[AIRef](https://airef.github.io/commands/commands-details.html#can-train-with-escrow)

Completion insert text:

```text
(can-train-with-escrow ${1:UnitId})
```

