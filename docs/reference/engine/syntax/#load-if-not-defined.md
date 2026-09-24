# `#load-if-not-defined`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-#load-if-not-defined"></a>

## `#load-if-not-defined`

- Kind: `command`
- Detail: Other - Other

Syntax: `#load-if-not-defined <LoadIfSymbol>`

Loads the code following the #load-if-not-defined if the given load-if symbol is NOT defined for the current game. All code following the #load-if-not-defined will be conditionally loaded in this manner until an #else command is used, or an #end-if is used to end the load-if block. Using an #else command after a #load-if-not-defined is optional, but all #load-if-not-defined commands must eventually have a closing #end-if. load-if symbols are case-sensitive. Technically, any text can be used for the pLoadIfSymbol parameter, such as #load-if-not-defined TEST, but since "TEST" is not an available load-if symbol, the code following a #load-if-not-defined TEST will always be loaded. The AI debugger will not generate an error if you accidentally misspelled a load-if symbol. Conditional loading commands like #load-if-not-defined and #load-if-defined can be nested up to 50 levels deep. Nesting conditional loading commands means using a conditional loading command inside of a preexisting conditional loading block. In this case, all of the conditional loading commands must be true for the code within the nested conditional loading command to run. See the examples below for details.

[AIRef](https://airef.github.io/commands/commands-details.html##load-if-not-defined)

Completion insert text:

```text
#load-if-not-defined ${1:LoadIfSymbol}
```

