# `#else`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-#else"></a>

## `#else`

- Kind: `command`
- Detail: Other - Other

Syntax: `#else`

Loads the following code if the previous #load-if-defined or #load-if-not-defined isn't true. #else is a conditional loading command that can only be used following a #load-if-defined or #load-if-not-defined command. If #else follows a #load-if-defined, then any rules between the #else and a closing #end-if will only be loaded if the system symbol for the #load-if-defined is not defined. Otherwise, the rules between the #else and a closing #end-if will not be read at any point in the game after the debugger is finished checking the AI for errors. Likewise, if #else follows a #load-if-not-defined, then any rules between the #else and a closing #end-if will only be loaded if the system symbol for the #load-if-not-defined is actually defined. All #else commands must have a closing #end-if.

[AIRef](https://airef.github.io/commands/commands-details.html##else)

