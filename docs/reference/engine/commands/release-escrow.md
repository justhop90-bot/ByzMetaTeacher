# `release-escrow`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-release-escrow"></a>

## `release-escrow`

- Kind: `command`
- Detail: Action - Economy

Syntax: `(release-escrow <Resource>)`

Releases the computer player's escrow for a given resource type (transfers all of the given resource type from its escrow stockpile into its normal stockpile, setting the amount stored in that resource's escrow stockpile to 0). AIs can store each of their four resource stockpiles in one of two stockpile types: normal and escrow. Resources in the normal stockpiles are free for the AI to use, while resources in the escrow stockpiles can only be used with up-build, up-train, or up-research if the EscrowGoalId parameter in these commands is a goal set to the value "with-escrow". The user interface shows the sum of both the normal and escrow stockpile resources added together for each resource. By default, all resources are stored in the normal stockpiles. However, set-escrow-percentage and up-modify-escrow can be used to store some or all of the AI's resources in the escrow stockpiles instead. Resources in the escrow stockpiles can transferred back into the normal stockpiles by using release-escrow, up-release-escrow, or up-modify-escrow". Resources are usually placed in escrow stockpiles in order to save up for expensive technologies or important buildings or units, so that it isn't spent on lower priority things." cReleaseEscrow.commandParameters = [ { nameLink: pResource.getLink(), name: "Resource", type: "Const", dir: "in", range: "food, wood, stone, or gold.", note: "The escrow resource stockpile." } ]

[AIRef](https://airef.github.io/commands/commands-details.html#release-escrow)

Completion insert text:

```text
(release-escrow ${1:Resource})
```

