# 03 — DUC performance / cardinality inventory @ `cd923b5a` ([E] only; else UNKNOWN, advisory only)

Policy: performance/cardinality is advisory compiler metadata, never a correctness gate
(`COMMUNITY_PER_PRACTICE_SPEC.md` §6-Layer 6; `native_hygiene.py:352-382` benchmark≠legality;
`AIREF_HYGIENE:44,49,57`). No fake optimizer.

| Operation | Local limit | Remote limit | Search complexity | Cardinality effect | Perf implication | Source@cd923b5a | Version scope |
|---|---|---|---|---|---|---|---|
| `up-find-local` (+status) | 240 | — | SCAN_FRONTIER; same-query reuses runtime cursor, query-change resets (`duc.py:612-650,2246-2277`); exact endpoint runtime-dependent (`:1199-1205`) | append lineage; `total=max→min(cap,prev.max+added)` (`:656-678`); full (min≥cap)→GUARANTEED_EMPTY+BLOCKED_BY_CAPACITY (`:1262-1280`) | MEDIUM, advisory (DUC-015 warning only) | `native_hygiene:754-762`; `native_controller_interactions:590-608`; `duc.py:128-172` | WK+DE sources, DE target; UP→DE transitions (`native_hygiene:775-824`) |
| `up-find-remote` / `up-find-resource` (+status) | — | 40 | same cursor model + focus-player-change resets REMOTE only (`:547-609`, test) | same append math, cap 40 | FAST, advisory | same rows, `:609-627` | same |
| `up-can-search` | — (reads init state) | — | O(1) static: GUARANTEED_FALSE iff `AT_END∨BLOCKED_BY_CAPACITY` else RUNTIME_DEPENDENT (`:1576-1595`) | none (observation) | none stated → UNKNOWN | `duc.py:1517-1596`; contract `native_hygiene:765-772` | UP→DE citation `airef:duc:can-search` |
| `up-clean-search` (SORT vs DEDUPE) | per-list | per-list | UNKNOWN (no cost class in corpus) | SORT preserves cardinality; DEDUPE clears to UNKNOWN (`:841-876`); `index_stable=false` | [C] idiom "limiting sort/search sizes" only; NO compiler sort-size warning → UNKNOWN, MUST REMAIN OPEN | `duc.py:841-876,3092-3099`; `native_hygiene:890-912` | UNKNOWN (citation `airef:duc:clean-search` only) |
| `up-remove-objects` | per-list | per-list | UNKNOWN | REMOVE_MATCHES; cardinality→None | UNKNOWN | `duc.py:909-1003` | UNKNOWN |
| `up-add-object-by-id` | per-list | per-list | UNKNOWN | cardinality→None, fingerprint→None | UNKNOWN | `duc.py:766-832,2945-3073` | UNKNOWN |
| groups `up-create/set/reset` (20 groups, cap 40) | source LOCAL (create) | LOCAL/REMOTE (set) | UNKNOWN (group-reuse benchmarked per hygiene table, no numbers in corpus) | `_group_cardinality:1122-1135` clipped `min(req,max,40)`; set-group reloads dest list + STALEs same-source target | UNKNOWN (advisory "groups reuse" `AIREF_HYGIENE:27`) | `native_hygiene:1002-1081,1105-1139`; `duc.py:1106-1148,1963-2041` | UP (Goal-span scope) → DE target |
| `up-get-search-state` / `up-get-point` / `up-get-cost-delta` / `up-get-object-data` / `up-get-group-size` | — | — | O(1) Goal write | span widths 4/2/4/1/1 | UNKNOWN (no benchmark) | `native_hygiene:688-751,915-951,1002-1081`; `duc.py:2375-2649,2119-2131` | UP→DE |
| Tested benchmark datum | 240 units among 400 → MEDIUM, 80000 loops for 0.5 lag | UNKNOWN | context: WK map, fast speed | — | generalization confidence LOW by construction | `test_native_hygiene:801-827` (harness only, NOT production evidence; no `PerformanceEvidence` instances in compiler source) | "AIRef benchmark" string only → UNKNOWN scope |

Explicit UNKNOWNs (no source): per-search time complexity beyond SCAN_FRONTIER; sort-size threshold;
path-distance cost; movement-queue backlog; building-placement cost; chat cost; `up-find-resource` distinct
cost (inherits remote 40/FAST by contract grouping, no separate benchmark); any loops-for-lag number for
remote/groups; quantitative cost beyond local-MEDIUM/remote-FAST + single 240-unit harness datum.
