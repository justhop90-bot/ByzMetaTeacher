# `research`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-research"></a>

## `research`

- Kind: `command`
- Detail: Action - Techs

Syntax: `(research <TechId>)`

Researches the given item if the technology is available to the player and the technology can be researched without escrowed resources. Please use can-research, can-research-with-escrow, or up-can-research in any rule where you use the research command, in order to prevent possible crashes. To prevent cheating, this action will fail if the item currently cannot be researched (i.e. the tech prerequisites are not met, there is no available building, or the player cannot afford the item). Research names, except for ages, my-unique-research, my-second-unique-research, are prefixed with a "ri-" which might stand for "research item". You can also research by the research ID rather than the research name. You can see all technologies and their research IDs in the Technologies table. You can also use my-unique-research, which will usually (always in DE) research the imperial age unique tech for the civilization, and you can also use my-second-unique-research, which will usually (always in DE) research the castle age unique tech for the civilization. In UP and WK, the exceptions are the Britons (in WK only) and Goths, whose my-unique-research and my-second-unique-research are switched.

[AIRef](https://airef.github.io/commands/commands-details.html#research)

Completion insert text:

```text
(research ${1:TechId})
```

