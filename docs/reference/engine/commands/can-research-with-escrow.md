# `can-research-with-escrow`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-can-research-with-escrow"></a>

## `can-research-with-escrow`

- Kind: `command`
- Detail: Fact - Can Do, Techs

Syntax: `(can-research-with-escrow <TechId>)`

Checks if the given research can start. In particular it checks:The research item is available to the computer player's civ.Tech tree prerequisites are met.Required resources are available, including escrow stockpiles.The appropriate building has no items in the queue so that it may start the research.Research names, except for ages, my-unique-research, my-second-unique-research, are prefixed with a "ri-" which might stand for "research item". You can also research by the research ID rather than the research name. You can see all technologies and their research IDs in the Technologies table. You can also use my-unique-research, which will usually check the imperial age unique tech for the civilization, and you can also use my-second-unique-research, which will usually check the castle age unique tech for the civilization. The excepts are the Britons, Franks, Goths, and Saracens, whose my-unique-research and my-second-unique-research are switched.

[AIRef](https://airef.github.io/commands/commands-details.html#can-research-with-escrow)

Completion insert text:

```text
(can-research-with-escrow ${1:TechId})
```

