# `#load-if-defined`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-#load-if-defined"></a>

## `#load-if-defined`

- Kind: `command`
- Detail: Other - Other

Syntax: `#load-if-defined <LoadIfSymbol>`

Loads the code following the #load-if-defined if the given load-if symbol is defined for the current game. All code following the #load-if-defined will be conditionally loaded in this manner until an #else command is used, or an #end-if is used to end the load-if block. Using an #else command after a #load-if-defined is optional, but all #load-if-defined commands must eventually have a closing #end-if. load-if symbols are case-sensitive. Technically, any text can be used for the pLoadIfSymbol parameter, such as #load-if-defined TEST, but since "TEST" is not an available load-if symbol, the code following a #load-if-defined TEST will never be loaded. The AI debugger will not generate an error if you accidentally misspelled a load-if symbol. However, you can use this feature intentionally as a way to essentially comment out an entire block of code. Conditional loading commands like #load-if-defined and #load-if-not-defined can be nested up to 50 levels deep. Nesting conditional loading commands means using a conditional loading command inside of a preexisting conditional loading block. In this case, all of the conditional loading commands must be true for the code within the nested conditional loading command to run. See the examples below for details.

[AIRef](https://airef.github.io/commands/commands-details.html##load-if-defined)

Completion insert text:

```text
#load-if-defined ${1:LoadIfSymbol}
```

