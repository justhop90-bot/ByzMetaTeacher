# `can-afford-research`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-can-afford-research"></a>

## `can-afford-research`

- Kind: `command`
- Detail: Fact - Techs, Can Do

Syntax: `(can-afford-research <TechId>)`

Checks whether the computer player has enough resources to perform the given research. Also checks that the research is available for the civ, that its not already researched and that the computer player has reached the required age. Does not check if the required building is built. The fact does not take into account escrowed resources. You can also use my-unique-research, which will usually check the imperial age unique tech for the civilization, and you can also use my-second-unique-research, which will usually check the castle age unique tech for the civilization. The excepts are the Britons, Franks, Goths, and Saracens, whose my-unique-research and my-second-unique-research are switched.

[AIRef](https://airef.github.io/commands/commands-details.html#can-afford-research)

Completion insert text:

```text
(can-afford-research ${1:TechId})
```

