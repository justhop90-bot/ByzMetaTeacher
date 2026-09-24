# `can-research`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-can-research"></a>

## `can-research`

- Kind: `command`
- Detail: Fact - Can Do, Techs

Syntax: `(can-research <TechId>)`

Checks if the given research can start. In particular it checks:The research item is available to the computer player's civ.Tech tree prerequisites are metRequired resources are available (not including escrow stockpiles).The appropriate building has no items in the queue so that it may start the research.Research names, except for ages, my-unique-research, my-second-unique-research, are prefixed with a "ri-" which might stand for "research item". You can also research by the research ID rather than the research name. You can see all technologies and their research IDs in the Technologies table. You can also use my-unique-research, which will usually (always in DE) check the imperial age unique tech for the civilization, and you can also use my-second-unique-research, which will usually (always in DE) check the castle age unique tech for the civilization. In UP and WK, the exceptions are the Britons (in WK only) and Goths, whose my-unique-research and my-second-unique-research are switched.

[AIRef](https://airef.github.io/commands/commands-details.html#can-research)

Completion insert text:

```text
(can-research ${1:TechId})
```

