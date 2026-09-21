# `#end-if`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-#end-if"></a>

## `#end-if`

- Kind: `command`
- Detail: Other - Other

Syntax: `#end-if`

Ends a conditionally loaded section of code (i.e. a #load-if-defined, #load-if-not-defined, or #else section). Every #load-if-defined or #load-if-not-defined which starts a conditionally loaded section of code must have a matching #end-if that end that section of code, though there may be an #else section before the #end-if. Conditionally loaded sections of code require the use of a pLoadIfSymbol. You can check out the Load-If Symbols page for a complete list of the load-if symbols that you can use.

[AIRef](https://airef.github.io/commands/commands-details.html##end-if)

