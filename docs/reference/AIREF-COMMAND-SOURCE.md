# AIRef Command Source and Validator Contract

## Purpose
This project-local source snapshot records the AIRef command vocabulary used by Basilisk's validator. It is derived from AIRef's current master js/commands.js and is not a replacement for the live AIRef reference.

## Authoritative source
AIRef command index: https://airef.github.io/commands/commands-index.html
Machine source: AIRef master branch js/commands.js
Source repository: https://github.com/airef/airef.github.io
Source blob SHA: e2fc2c9b6a6b23f63d0743524dc94252eacfc2af
Snapshot date: 2026-09-23

AIRef defines 385 commands in this snapshot. Basilisk uses 88 distinct commands. All Basilisk command names resolve against the AIRef vocabulary and all observed Fact/Action placements agree with AIRef's declared command type. AIRef classifies the seven logical operators as Other; Basilisk permits those only on the fact side.

## External contracts enforced

| Contract | AIRef source | Validator treatment |
| --- | --- | --- |
| Seven logical operators; not is unary and the other six are binary | https://airef.github.io/resources/articles/logical-operators.html | Exact arity validation |
| DE rule limit: 10,000 | https://airef.github.io/resources/articles/data-limits.html | Hard limit |
| DE rule element limit: 32 | https://airef.github.io/resources/articles/data-limits.html | Hard limit |
| Source line limit: 255 characters | https://airef.github.io/resources/articles/data-limits.html | Hard limit |
| Timer IDs: 1 through 50 | https://airef.github.io/resources/articles/data-limits.html | Named and literal timer validation |
| Point/cost/search-state commands write consecutive goal blocks | https://airef.github.io/resources/articles/data-limits.html | Basilisk-used output blocks are range-checked |
| DUC local search list: 240 | https://airef.github.io/resources/articles/data-limits.html | Numeric up-find-local bound check |
| DUC remote search list: 40 | https://airef.github.io/resources/articles/data-limits.html | Numeric up-find-remote bound check |
| Command vocabulary and Fact/Action role | https://airef.github.io/commands/commands-index.html | Exhaustive command-name and role validation |

can-* feasibility contracts, queue/completion witnesses, persistent demand, source-order gates, and lifecycle ownership are Basilisk project doctrine, not AIRef language rules.

## Basilisk commands by AIRef version family

### AoC/base

| Command | AIRef type | Version | Uses |
| --- | --- | --- | --- |
| `acknowledge-event` | Action | AoC | 1 |
| `and` | Other / logical | AoC | 283 |
| `attack-now` | Action | AoC | 1 |
| `attack-soldier-count` | Fact | AoC | 2 |
| `build` | Action | AoC | 39 |
| `building-available` | Fact | AoC | 1 |
| `building-type-count` | Fact | AoC | 145 |
| `building-type-count-total` | Fact | AoC | 110 |
| `can-afford-building` | Fact | AoC | 2 |
| `can-build` | Fact | AoC | 28 |
| `can-build-with-escrow` | Fact | AoC | 16 |
| `can-research-with-escrow` | Fact | AoC | 149 |
| `can-train` | Fact | AoC | 14 |
| `can-train-with-escrow` | Fact | AoC | 5 |
| `civilian-population` | Fact | AoC | 41 |
| `current-age` | Fact | AoC | 326 |
| `disable-self` | Action | AoC | 17 |
| `disable-timer` | Action | AoC | 232 |
| `dropsite-min-distance` | Fact | AoC | 22 |
| `enable-timer` | Action | AoC | 127 |
| `event-detected` | Fact | AoC | 1 |
| `food-amount` | Fact | AoC | 16 |
| `game-time` | Fact | AoC | 20 |
| `goal` | Fact | AoC | 1501 |
| `gold-amount` | Fact | AoC | 3 |
| `housing-headroom` | Fact | AoC | 1 |
| `idle-farm-count` | Fact | AoC | 9 |
| `map-type` | Fact | AoC | 4 |
| `military-population` | Fact | AoC | 3 |
| `nor` | Other / logical | AoC | 1 |
| `not` | Other / logical | AoC | 419 |
| `or` | Other / logical | AoC | 534 |
| `player-in-game` | Fact | AoC | 14 |
| `players-building-count` | Fact | AoC | 52 |
| `players-building-type-count` | Fact | AoC | 21 |
| `players-current-age` | Fact | AoC | 3 |
| `players-military-population` | Fact | AoC | 4 |
| `players-unit-type-count` | Fact | AoC | 191 |
| `population-headroom` | Fact | AoC | 1 |
| `release-escrow` | Action | AoC | 154 |
| `research` | Action | AoC | 70 |
| `research-available` | Fact | AoC | 20 |
| `set-escrow-percentage` | Action | AoC | 4 |
| `set-goal` | Action | AoC | 1015 |
| `set-strategic-number` | Action | AoC | 341 |
| `sheep-and-forage-too-far` | Fact | AoC | 4 |
| `stone-amount` | Fact | AoC | 10 |
| `strategic-number` | Fact | AoC | 324 |
| `timer-triggered` | Fact | AoC | 76 |
| `town-under-attack` | Fact | AoC | 56 |
| `train` | Action | AoC | 19 |
| `true` | Fact | AoC | 34 |
| `unit-type-count` | Fact | AoC | 75 |
| `unit-type-count-total` | Fact | AoC | 178 |
| `wood-amount` | Fact | AoC | 13 |

### UserPatch

| Command | AIRef type | Version | Uses |
| --- | --- | --- | --- |
| `up-add-research-cost` | Action | UP | 12 |
| `up-assign-builders` | Action | UP | 17 |
| `up-build` | Action | UP | 2 |
| `up-compare-goal` | Fact | UP | 449 |
| `up-filter-distance` | Action | UP | 3 |
| `up-filter-garrison` | Action | UP | 2 |
| `up-find-local` | Fact/Action | UP | 6 |
| `up-find-player` | Action | UP | 1 |
| `up-find-remote` | Fact/Action | UP | 4 |
| `up-full-reset-search` | Action | UP | 7 |
| `up-garrison` | Action | UP | 1 |
| `up-get-cost-delta` | Action | UP | 6 |
| `up-get-fact` | Fact/Action | UP | 10 |
| `up-get-point` | Action | UP | 3 |
| `up-get-search-state` | Action | UP | 7 |
| `up-get-target-fact` | Fact/Action | UP | 1 |
| `up-modify-goal` | Fact/Action | UP | 31 |
| `up-modify-sn` | Fact/Action | UP | 5 |
| `up-pending-objects` | Fact | UP | 50 |
| `up-pending-placement` | Fact | UP | 8 |
| `up-remaining-boar-amount` | Fact | UP | 1 |
| `up-request-hunters` | Action | UP | 3 |
| `up-research-status` | Fact | UP | 331 |
| `up-reset-attack-now` | Action | UP | 3 |
| `up-reset-placement` | Action | UP | 4 |
| `up-retreat-now` | Action | UP | 1 |
| `up-send-scout` | Action | UP | 2 |
| `up-set-placement-data` | Action | UP | 2 |
| `up-set-target-object` | Fact/Action | UP | 3 |
| `up-set-target-point` | Action | UP | 3 |
| `up-setup-cost-data` | Action | UP | 6 |
| `up-target-objects` | Action | UP | 3 |
| `up-ungarrison` | Action | UP | 19 |

### Definitive Edition

| Command | AIRef type | Version | Uses |
| --- | --- | --- | --- |


## Refresh procedure
When AIRef's command definitions change, regenerate extracted/inventories/airef-command-inventory.json from the current AIRef master js/commands.js definitions, update its source blob SHA/date, then run the front-door validator and self-test.
Do not add commands manually merely to make Basilisk pass. An unknown command should stop validation.

## Sign-off boundary
This layer closes the validator gap around command vocabulary and command-side role misuse without attempting to infer undocumented runtime semantics from names. AIRef remains the external language reference; the game remains the final behavioral debugger.
