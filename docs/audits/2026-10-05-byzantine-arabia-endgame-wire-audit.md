# Byzantine Arabia Endgame Wire Audit

Scope: canonical Byzantine stock path used by build_byzantine_strategy() on standard land/Arabia, with emphasis on Imperial production, research bootstrap, siege conversion, attack readiness, objective admission, and attack-group execution.

Authoritative baseline: main at aa6e560453d98f3038a7d5b3313b0d0a5dac7ce6.

## Executive diagnosis

The runtime failure is upstream of the final attack pulse. The endgame controller exists, but several required edges were dangling or mutually blocking.

1. Research gates required seed units that normal Arabia did not persistently produce.
2. Endgame admission required an exact 18 Halberdier / 18 Elite Skirmisher / 12 Hussar snapshot even when a strong gold army existed.
3. Siege admission ignored the ram-line.
4. Capped Ram and Siege Ram had no persistent strategic research demands in the community pack.
5. byzantine-army-attack-ready was declared and consumed, but no writer established it at 1.
6. byzantine-siege-approach=normal was consumed by objective admission, but no writer established it.
7. Exact trash-floor recovery rules reasserted the same unreachable snapshot after the admission gate was relaxed.

## Professional schematic

```text
CANONICAL PATH

build_byzantine_strategy()
        |
        v
build_byzantine_stock_strategy()
        |
        +----------------------+--------------------------+
        |                      |                          |
        v                      v                          v
opening selector          military demands           endgame plan
Arabia/no pressure       production/research              |
-> DEFENSIVE_STANDARD            |                        v
        |                         |                 Imperial band
        |                         |                        |
        |                         v                        v
        |                  seed -> upgrade          push state 1
        |                         |                        |
        |                 [W1 BROKEN]                    |
        |                         |                        v
        |                  no seed units          attack package
        |                                                  |
        |                                      [W2 EXACT FLOOR DEADLOCK]
        |                                                  |
        |                                                  v
        |                                            siege package
        |                                                  |
        |                                      [W3 RAM NOT COUNTED]
        |                                                  |
        |                                       [W4 RAM UPGRADE MISSING]
        |                                                  |
        |                                                  v
        |                                     attack-ready writer
        |                                                  |
        |                                      [W5 DISCONNECTED]
        |                                                  v
        |                                     siege-approach writer
        |                                                  |
        |                                      [W6 DISCONNECTED]
        |                                                  v
        |                                      objective admission
        |                                                  |
        |                                                  v
        |                                      role/group formation
        |                                                  |
        |                                                  v
        |                                         DUC target control
        |                                                  |
        +-------------------------------------------> push pulse
                                                           |
                                                           v
                                                  live witness/frontier
```

## Broken wires

| ID | Component | Broken or loose edge | Source | Gameplay symptom |
|---|---|---|---|---|
| W1 | Research bootstrap | Castle age -> seed unit -> upgrade research | community_strategy_packs.py around 1245 and 1264 | Pikeman/Elite Skirmisher/Husbandry/Hussar research can remain inadmissible |
| W2 | Imperial admission | mature army -> push admission | strategy.py endgame push controller | Strong gold army can never qualify because 18/18/12 is an exact gate |
| W3 | Siege witness | ram-line -> push siege readiness | strategy.py standard_siege_ready | Five existing Rams still do not count as qualifying siege |
| W4 | Ram upgrades | ram stock -> Capped Ram -> Siege Ram research | community_strategy_packs.py research pack | Food/wood bank does not create the ram-upgrade project |
| W5 | Attack readiness | push state -> attack-ready=1 | strategy.py endgame controller and objective controller | Objective admission can never see attack-ready |
| W6 | Siege approach | mature push -> siege-approach=normal | strategy.py and role_separation.py | Objective admission can remain inadmissible even with a usable army |
| W7 | Recovery | failed exact trash floor -> recovery | strategy.py exact-floor recovery rules | Relaxing admission alone would still loop back into 18/18/12 |

## Evidence anchors

- Canonical entry point: strategy.py line 5699.
- Endgame push lowering: strategy.py line 2922.
- Endgame objective admission: strategy.py line 2681.
- New attack-readiness writer: strategy.py line 3063.
- New push admission: strategy.py line 3100.
- Castle seed demands: community_strategy_packs.py line 1245.
- Capped Ram research pack: community_strategy_packs.py line 484.
- Capped Ram/Siege Ram gates: community_strategy_packs.py line 1327.
- Imperial Halberdier persistent floor: community_strategy_packs.py line 1356.
- Imperial ram sustain: community_strategy_packs.py line 1763.
- Stock profile attachment of endgame plan: community_strategy_packs.py line 2251.
- Opening selector: opening.py lines 56, 97, 107.
- Verified unit lines: civ_profile.py lines 1092-1105.
- Current game-data unit transitions: civ_profile.py lines 1170-1188.
- Existing role formation: role_separation.py line 344; role thresholds at lines 1012-1014.

## Repair contract

1. Keep the 18/18/12 production floors as standing policy.
2. Add exactly three six-unit Castle seed demands for Spear, Skirmisher, and Scout Cavalry.
3. Add persistent Capped Ram and Siege Ram research demands on the existing ram-line.
4. Define attack readiness as a mature force: military-population >= 15, plus at least 8 of a valid primary combat line, plus qualifying siege.
5. Qualifying siege includes Trebuchet, Bombard Cannon, Mangonel-line, or Battering/Capped/Siege Rams.
6. Write attack-ready and normal siege-approach from the mature package.
7. Recover on package loss or siege loss, not on exact 18/18/12 loss.
8. Preserve the existing objective, role, DUC, witness, frontier, and 20-second push lifecycle.

## Community cross-reference

Public AoE2 AI examples repeatedly separate standing production from attack execution, use military-population thresholds for engagement decisions, and use explicit attack-group size / percentage Strategic Numbers for the attack pulse. The repair follows that pattern without copying a community bot.

The repository's own B-community_per_idiom_catalog.csv records the military-population superiority staircase as a convergent community idiom. The project also already uses military-population in defensive/overmatch logic, so this is a style-compatible reuse rather than a new subsystem.

The important community lesson is not 'attack earlier'. It is: make the production demand reachable, let the army mature, then hand control to the attack-group lifecycle.