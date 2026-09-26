# Byzantine Stock-AI Capability Matrix

This is the complete capability contract for the first competent Byzantine player.

It defines **what the player must be capable of**, **when the capability is admissible**, **what priority class it belongs to**, and **what evidence proves that the capability actually became available or was used**.

This is not a build order.

A capability is opened by a real strategic or domain demand. The player does not activate every row merely because the civilization owns the technology.

## Priority model

Use five priority classes.

| Priority | Meaning | Typical examples |
|---|---|---|
| P0 Survival | Prevent immediate economic or military collapse | villagers, houses, minimum defense, emergency wall/gate, emergency repair/recovery |
| P1 Core progression | Maintain the chosen age/economic trajectory | age-up, farms, required dropsites, Castle prerequisites, core production |
| P2 Strategic response | Answer a detected opportunity or threat | counter units, dock/fishing, tower, siege, monastery, transport |
| P3 Conversion | Convert an established advantage into stronger position | extra TCs, production expansion, relic package, siege mass, naval expansion, Keep/Bombard Tower |
| P4 Situational luxury | Useful only when the position specifically pays for it | redundant production, marginal upgrades, excess tower investment, unnecessary water investment |

Priority is **conditional**, not a universal scheduler. A P2 threat can temporarily outrank P1 Castle preparation if failing to answer the threat destroys the Castle trajectory. The strategic owner remains responsible for deciding whether the demand is still worth pursuing.

## Strategic posture matrix

| Posture | Primary objective | Typical P0 | Typical P1 | Typical P2/P3 |
|---|---|---|---|---|
| Develop | Build healthy economy and information | villagers, houses, food continuity | age-up, dropsites, eco tech | small map-specific response |
| Defend | Preserve economy and deny enemy tempo | minimum army, walls/towers, worker safety | production and farms | counter package, siege |
| Castle conversion | Reach and exploit Castle | defense floor | Castle resources, infrastructure | TC, siege, Monastery, premium unit |
| Boom | Expand economic capacity | worker continuity | farms, TC, production | relics, siege, map control |
| Pressure | Convert military tempo | replenishment | production + economy | siege, forward infrastructure |
| Water | Control/exploit water | shoreline safety | dock/fishing/transport baseline | naval mass, upgrades, land support |
| Recovery | Restore lost capability | defense + villagers | rebuilding economy/infrastructure | cancelled/replaced plans |
| Imperial conversion | Convert mature economy to decisive power | army floor + worker continuity | production/upgrades | siege, Trebuchets, Bombard Towers, naval/artillery |

## Capability matrix: economy and core infrastructure

| Capability | Age | Demand trigger | Priority | Required capability path | Release / cancellation |
|---|---|---|---|---|---|
| Villager continuity | All | TC can produce and food is available | P0 | TC + food + production feasibility | Never permanently releases while alive; pauses only when intentionally unavoidable |
| House/population | All | Population headroom risks stopping production | P0 | Builder + wood + placement | Release when sufficient headroom exists |
| Resource dropsite | Dark onward | Resource source requires efficient drop-off | P1 | Appropriate camp/mill/mining building | Release when source is exhausted/obsolete |
| Farms | Dark onward | Food demand exceeds safe natural-source throughput | P0/P1 | Mill + wood + farmer capacity | Continue/reopen as food economy requires |
| Horse Collar / Heavy Plow / Crop Rotation | F/C/I | Farming is material to current food plan | P1/P3 | Mill + affordability + opportunity cost | Skip/defer when food source or investment does not justify it |
| Lumber techs | F/C/I | Wood throughput is binding | P1/P3 | Lumber Camp + resources | Defer if wood is temporarily secondary |
| Mining techs | F/C/I | Relevant resource throughput is binding | P1/P3 | Mining Camp + resources | Defer when resource is not strategically collected |
| Wheelbarrow / Hand Cart | F/C | Worker throughput or carrying efficiency is strategically useful | P1/P3 | TC + resources | Research according to economy state |
| Market | Feudal onward | Resource imbalance, age transition, trade, recovery | P1/P2 | required prerequisite + wood | Retain as capability; repeated demand unnecessary |
| Blacksmith | Feudal onward | Military or age transition requires upgrades / Siege Workshop path | P1/P2 | prerequisite + wood | Retain as provider; avoid duplicate demand |
| Town Center expansion | Castle onward | Economy can sustain additional TC and its opportunity cost | P2/P3 | Castle Age + 275w + placement + safe-enough site | Cancel/defer when pressure or resource scarcity makes expansion dangerous |
| Imperial Age | Castle onward | Mature economy and military position justify conversion | P1/P3 | TC + resources + required prerequisites | Persistent objective until completed or strategically cancelled |

## Capability matrix: land military

| Capability | Age | Demand trigger | Priority | Preferred role | Release / reassessment |
|---|---|---|---|---|---|
| Spearman | Feudal | Cavalry pressure | P0/P2 | minimum anti-cavalry floor | Deficit clears; demand can reopen |
| Pikeman | Castle | Sustained cavalry/camel threat | P1/P2 | efficient anti-mounted core | Scale to observed threat |
| Halberdier | Imperial | Heavy sustained mounted threat | P1/P2 | late anti-cavalry | Replace lower-tier standing defense as appropriate |
| Skirmisher | Feudal | Archer/ranged pressure | P1/P2 | cheap ranged counter | Scale to actual ranged threat |
| Elite Skirmisher | Castle | Sustained ranged pressure | P1/P2 | scalable anti-ranged | Upgrade/produce while threat persists |
| Archer | Feudal | Chosen ranged pressure | P2 | early ranged support | Only if strategic posture uses ranged pressure |
| Crossbowman | Castle | Ranged Castle package justified | P2 | ranged damage/support | Reassess against armor/composition |
| Arbalester | Imperial | Ranged composition remains relevant | P2/P3 | late ranged backbone | Reassess against missing upgrades |
| Hand Cannoneer | Imperial | Heavy infantry/armored target problem | P2/P3 | gunpowder ranged counter | Scale only with target justification |
| Scout/Light/Hussar | F/C/I | Map control, raiding, vision, mobility | P2/P3 | mobile utility | Avoid becoming food sink without purpose |
| Knight/Cavalier/Paladin | Castle/I | Mobile heavy cavalry strategy is justified | P2/P3 | mobility, raid, shock | Byzantine lacks Bloodlines, so include explicit opportunity-cost check |
| Camel/Heavy Camel | Castle/I | Enemy mounted army or mobility requirement | P2 | anti-mounted / mobility | Strongly threat-driven because it competes for gold |
| Cataphract / Elite Cataphract | Castle/I | Infantry-heavy target set or decisive premium cavalry plan | P2/P3 | anti-infantry shock | Premium demand; requires Castle and sustainable gold |
| Long Swords / 2H / Champion | Castle/I | Infantry pressure or composition demands melee core | P2/P3 | anti-building/general melee | Do not mass without battlefield reason |
| Halberdier + ranged support | I | Mixed mounted threat | P1/P2 | stable late defensive package | Reassess composition |
| Petards | Castle | Building/wall breach opportunity | P2 | tactical demolition | Small controlled quantity |
| Unique/post-patch premium infantry package | Imperial | Current Byzantine tech/roster justifies it | P2/P3 | late conversion | Check current patch data before implementation |

Current Byzantines have access to Cataphracts/Elite Cataphracts, Heavy Camel Riders, full Halberdier, Arbalester, Hand Cannoneer and multiple land counter lines; the September 2026 update also added Varangian Guards to Byzantines and changed Logistica to give trample to both Cataphracts and Varangian Guards.

The compiler must treat the exact contemporary unit/tech roster as data, not hard-coded doctrine. The matrix defines capability families; current identifiers belong in the repository's Byzantine reference data.

## Capability matrix: siege

| Capability | Age | Demand trigger | Priority | Use | Required evidence |
|---|---|---|---|---|---|
| Siege Workshop | Castle | Buildings, ranged mass, fortified position, or siege composition | P2 | capability provider | Workshop exists |
| Battering Ram | Castle | Enemy buildings/walls are a meaningful objective | P2 | anti-building | Actual ram count |
| Capped/Siege Ram | Imperial | Continued building pressure | P2/P3 | sustained siege | Actual unit + relevant upgrade |
| Mangonel | Castle | Ranged mass / positional area damage | P2 | anti-ranged / area damage | Actual unit count |
| Onager | Imperial | Continued area-damage requirement | P2/P3 | mass ranged counter | Actual unit + upgrade |
| Scorpion | Castle | Dense low-armor formations / support | P2 | line damage | Actual production |
| Heavy Scorpion | Imperial if available | Composition warrants it | P3 | late support | Tech + unit witness |
| Siege Tower | Castle | Walls/terrain make transport-by-siege tactically useful | P4/P2 | situational bypass | Actual siege tower |
| Bombard Cannon | Imperial | Buildings, siege, heavy positional targets | P2/P3 | long-range siege | Actual unit count |
| Trebuchet | Imperial | Castle/TC/fortification destruction | P2/P3 | strategic building siege | Castle + actual treb |
| Siege Engineers | Imperial if available | Siege investment is sustained enough to justify | P3 | siege conversion | Tech completion |
| Chemistry | Imperial | Gunpowder/siege/naval breakpoint | P2/P3 | prerequisite/upgrade capability | Tech completion |

The current Byzantine tree includes Battering Ram/Capped Ram/Siege Ram, Mangonel/Onager, Scorpion, Siege Tower, Bombard Cannon and Castle-produced Trebuchets. The current published tree also lists Siege Engineers as unavailable to Byzantines, so the implementation must not assume that generic siege doctrine applies unchanged.

## Capability matrix: water

### Water posture states

| State | Definition | Strategy |
|---|---|---|
| Dry/irrelevant | No economically useful or strategically important water | Ignore dock investment |
| Opportunistic | Fish or shoreline resource materially improves economy | P2 dock/fishing |
| Competitive water | Water control affects economy or enemy access | P1/P2 dock + naval |
| Full water | Water is the primary economy/army route | P1 water economy + naval |
| Transport critical | Land access is blocked or island separation matters | P1/P2 transport capability |
| Water lost | Naval investment no longer pays | Release naval expansion, preserve useful survivors, rebalance land |

### Water capability matrix

| Capability | Age | Trigger | Priority | Typical provider | Release/reassessment |
|---|---|---|---|---|---|
| Dock | Dark/Feudal depending map rules | Meaningful fish, naval threat, transport, trade-water opportunity | P1/P2 | Builder + shoreline placement | Skip on irrelevant water |
| Fishing Ship | Dark onward | Fish economy is economically superior/useful | P1/P2 | Dock + food/wood | Stop scaling when fish/value falls |
| Fish Trap | Feudal onward | Sustained fish economy and safe enough water | P2/P3 | Mill/Dock economy + wood | Use when water economy persists |
| Fire Galley | Feudal | Early naval control / anti-galley requirement | P2 | Dock + wood/gold | Threat-driven |
| Galley | Feudal | General naval presence or water map economy | P2 | Dock | Scale to water threat |
| Demolition Ship | Castle onward | Burst against clustered ships | P2 | Dock + resources | Tactical |
| War Galley / Galleon | Castle/I | Sustained water combat | P2/P3 | Dock + upgrade | Scale with control requirement |
| Fire Ship / Fast Fire Ship | Castle/I | Continued combat vs ships | P2 | Dock + upgrades | Scale with naval composition |
| Hulk line | Feudal onward | Current naval ruleset makes regional ship line available | P2 | Dock | Follow current tech data |
| Transport Ship | Dark onward | Water crossing required | P1/P2 | Dock + transport demand | Release after transport objective completes unless reusable transport need remains |
| Trade Cog | Feudal | Trade route is strategically useful | P3 | Dock + allied trade route | Only with sustained trade economy |
| Cannon Galleon | Imperial if available | Shoreline building pressure | P2/P3 | Dock + Chemistry/prerequisites | Use only if current Byzantine tree permits |
| Dromon | Imperial | Anti-building/long-range naval siege demand | P2/P3 | Dock + Imperial + current prerequisites | Actual fleet purpose |
| Careening | Castle | Ship survivability matters | P2/P3 | Dock/University | Upgrade with water commitment |
| Dry Dock | Imperial | High-value naval commitment | P3 | University | Only sustained navy |
| Shipwright | Imperial if available | Sustained ship production or transport | P3 | University | Research when fleet value justifies |
| Greek Fire | Castle | Fire Ship/Dromon package is strategically useful | P2/P3 | Castle/tech chain | Only with naval commitment |

The current Byzantine tree lists Fishing Ship, Transport Ship, Fire Galley → Fire Ship → Fast Fire Ship, Galley → War Galley → Galleon, Hulk → War Hulk → Carrack, Demolition Raft → Demolition Ship → Heavy Demo Ship, Trade Cog, Cannon Galleon/Elite Cannon Galleon and Dromon, alongside water technologies including Fishing Lines, Gillnets, Careening, Dry Dock and Greek Fire-related infrastructure.

The naval rules are current enough that the matrix should remain data-driven. February 2026 introduced a substantial naval overhaul, and June/2026 changed dock/tower anti-ship values.

## Capability matrix: Monks and relics

| Capability | Age | Trigger | Priority | Purpose | Release/reassessment |
|---|---|---|---|---|---|
| Monastery | Castle | Relic, healing, conversion or Monk support is strategically useful | P2 | capability provider | Retain while useful |
| Monk | Castle | Relic access, healing, conversion | P2 | utility/support | Replace losses while demand persists |
| Relic collection | Castle | Safe/value-positive relic opportunity | P2/P3 | long-term eco/value | Cancel when route is too costly/unsafe |
| Relic denial | Castle | Enemy relic objective threatens meaningful advantage | P2 | deny opponent | Release when contest is no longer worthwhile |
| Healing | Castle | Army has persistent wounded value worth preserving | P2 | sustain army | Scale with army composition |
| Conversion pressure | Castle/I | Enemy premium units vulnerable to conversion | P2 | tactical counter | Demand driven by actual target |
| Redemption | Castle | Enemy siege/building conversion opportunity | P3 | specialist Monk utility | Only where target density exists |
| Atonement | Castle | Enemy Monks are relevant | P3 | Monk counter | Conditional |
| Sanctity/Fervor/etc. | Castle/I | Monk investment is sustained | P3 | Monk durability/mobility | Upgrade according to actual Monk value |
| Theocracy | Imperial | Multiple Monks and successful conversion matter | P3 | Monk micro efficiency | Conditional |
| Block Printing | Imperial | Monk range is strategically valuable | P3 | conversion/healing reach | Conditional |
| Heresy/Faith | Castle/I | Enemy conversion threat or Monk survival | P3 | anti-conversion | Conditional |

Current Byzantine Monastery access includes Monks, Devotion/Faith, Redemption, Atonement, Herbal Medicine, Heresy, Sanctity, Fervor, Illumination, Block Printing and Theocracy according to the published current tech tree. Byzantines also have the civilization/team context that makes Monk use strategically relevant.

Relics are a strategic opportunity, not an automatic Castle checklist.

## Capability matrix: fortifications

| Capability | Age | Trigger | Priority | Purpose | Opportunity-cost guard |
|---|---|---|---|---|---|
| Palisade Wall | Dark | Choke, raid path, villager safety, map shaping | P0/P1 | delay/shape movement | Wood must not destroy age-up/production |
| Palisade Gate | Dark | Controlled access | P1 | close/open route | Avoid maze-building |
| Outpost | Dark/Feudal | Vision, exposed resource warning, emergency defense | P1/P2 | warning/limited defense | Avoid tower spam |
| Watch Tower | Feudal | Known attack route or exposed economy | P1/P2 | garrison + defense | Compare vs mobile military/TC |
| Stone Wall | Feudal | Choke/closed base/large attack delay requirement | P1/P2 | strategic denial | Stone competes directly with Castle |
| Stone Gate | Feudal | Controlled strategic passage | P1/P2 | access control | Same stone guard |
| Guard Tower | Castle | Persistent pressure on an exposed point | P2 | stronger defense | Requires University/upgrade path |
| Fortified Wall | Castle | Long-term defensive position | P2/P3 | durable closure | Don't consume Castle economy |
| Keep | Imperial | Critical position requires heavy static defense | P2/P3 | stronghold | High stone cost |
| Bombard Tower | Imperial | Late artillery defense solves a concrete positional problem | P2/P3 | anti-army/building/shore defense | Requires Chemistry + appropriate University path; enormous opportunity cost |
| Castle | Castle | Strategic base anchor, UU access, Trebuchet production, map denial | P1/P2 | multifunctional fortification | Stone reserve must be protected |

Official AoE2 guidance explicitly treats walls and towers as defensive tools whose value depends on the threat and opportunity cost, noting that towers compete with Castle-age stone investment; Castles provide both defense and civilization-specific unit/technology capability.

The current Byzantine tree lists Guard Tower → Keep, Fortified Wall, Bombard Tower and associated University technologies.

## Capability matrix: production and infrastructure scaling

| Capability | Trigger | Priority | Rule |
|---|---|---|---|
| Additional Barracks | Standing infantry/halberdier demand exceeds one-production capacity | P2/P3 | Build only when replacement demand supports it |
| Additional Range | Ranged demand exceeds current capacity | P2/P3 | Queue-aware |
| Additional Stable | Mounted demand is persistent | P2/P3 | Avoid gold sink |
| Additional Siege Workshop | Siege demand exceeds one workshop capacity | P2/P3 | Demand from actual siege pressure |
| Additional Dock | Multiple naval production queues are justified | P2/P3 | Water posture must still be active |
| Additional Monastery | Monk production/relic objective requires capacity | P3 | Do not spam |
| Additional Castle | Forward anchor/UU/trebuchet/defense need justifies stone | P3 | Very high capital opportunity cost |
| Additional TC | Economy can sustain it | P2/P3 | Worker throughput is the witness of value |
| University | Defensive/late-tech capability is justified | P2/P3 | Do not treat as mandatory Castle clutter |

## Map-conditioned priority matrix

| Map/position | First-order priorities | Conditional priorities | Usually defer |
|---|---|---|---|
| Open land / Arabia-like | scouting, food continuity, houses, minimum military, age progression | walls, towers, Castle, siege, Monk/relic | docks unless genuine fish/water value |
| Closed land / Arena-like | eco, safe Castle, relic information, siege | Monastery, relics, walls, extra TC, siege | heavy Feudal pressure unless opportunity appears |
| Black Forest/chokepoint | food/wood, map control, wall/choke, siege | towers, Castle, Monks, extra TC | expensive exposed cavalry |
| Hybrid | normal land economy + water assessment | dock, fishing, transport, naval | full naval commitment if water is strategically secondary |
| Full water | dock/fishing, naval production, shoreline safety | transport, trade, land landing, late naval siege | land-only greedy Castle plan |
| Nomad/start displaced | immediate settlement, dropsite, food, scouting | dock, fish, emergency walls, rebuild | rigid opening sequence |
| Resource-exposed position | defense of specific economic node | wall/tower/forward TC/Castle | generic base-wide fortification |
| Island/transport map | transport, dock, naval protection, safe landing | naval siege, trade, Monk landing | land-only assumptions |
| Late fortified position | army floor, siege, production, economy | Keep/Bombard Tower/Castle/Monk support | adding static defense instead of siege |

## Capability arbitration

When several demands compete for the same resource, do not rank the building names.

Evaluate the consequence chain.

### Example: Castle vs Feudal defense

    Castle demand
       requires stone + food/gold/wood opportunity

    enemy cavalry pressure
       requires defensive army floor

If buying the minimum defensive army preserves the Castle trajectory, defense temporarily wins the resource claim.

If the threat is large enough that the Castle will be lost or the economy destroyed without stronger defense, Strategy must reassess the Castle demand itself.

The correct behavior is not “Castle has priority 1 and Spears have priority 2.”

The correct behavior is:

    strategic intent
      -> current threat
      -> minimum required response
      -> protected remaining intent
      -> reassess

### Example: Dock vs Castle

If water provides substantial food or transport value, dock may become P1/P2.

If water is incidental and Castle timing is the dominant strategic conversion, dock remains closed.

### Example: Monastery vs Siege

If relic value is high and enemy composition makes a Monk investment safe, Monastery can coexist with early siege.

If siege is required immediately to break a fortified position, Monastery remains secondary.

## Matrix implementation rule

Every matrix row eventually becomes one of:

    STRATEGIC DEMAND
      -> CAPABILITY
      -> FEASIBILITY
      -> ACTION
      -> WITNESS
      -> RELEASE / INVALIDATE

or an **observed capability** that never becomes an automatic demand.

The compiler should validate the lifecycle.

The Strategy module decides admissibility.

The domain module owns the execution path.

The Engine module supplies native predicates/actions.

Information supplies the facts that make map-conditioned demand admissible.

## Hard invariants

1. A building existing does not prove its strategic purpose was fulfilled.
2. A capability being available does not imply it should be used.
3. A can-* predicate proves feasibility at evaluation time, not completion.
4. Pending/queued state is not completion.
5. A dock must have a reason to exist.
6. Naval investment must have an exit path when water loses value.
7. Siege production must be tied to an actual battlefield or structural problem.
8. Monk investment must have an actual utility, relic, or conversion reason.
9. Relic collection must include an opportunity-cost and safety test.
10. Towers and walls must solve a positional problem, not consume resources because the building is legal.
11. Bombard Towers are late-game conditional infrastructure, never a generic Imperial checklist.
12. Transport capability must be available when map geometry requires it.
13. Additional production capacity requires demonstrable demand.
14. Defensive military has a floor separate from attack reserve.
15. Every persistent demand must have cancellation/invalidation logic.
16. Every execution lifecycle must have a world-state witness.
17. Temporary failure preserves strategic intent unless Strategy explicitly invalidates it.
18. Map context can open or close capability demand without becoming a giant map-specific state machine.
19. Byzantine-specific missing technologies/capabilities are part of the strategy data and must be checked before opening a demand.
20. The capability matrix is a coverage contract, not a build order.

## Current Byzantine reference

Reference sources:

- https://www.aoe2counterhub.com/civs/byzantines.html
- https://aoe2techtree.net/?lng=en
- https://www.ageofempires.com/news/age-of-empires-ii-definitive-edition-update-185872/
- https://www.ageofempires.com/news/age-of-empires-ii-definitive-edition-update-169123/
- https://www.ageofempires.com/news/age-of-empires-ii-definitive-edition-update-177723/

The current published Byzantine tech tree includes the core land, siege, Castle, dock, Monastery, University and defensive structures described above. The current September 2026 update also changed Byzantine access by adding Varangian Guards and changed the Logistica effect, so implementation must consume current repository data rather than fossilized civ assumptions.

The current AoE2DE update stream also includes substantial naval and AI behavior changes, reinforcing the requirement that water and transport logic remain current-data-driven rather than encoded as permanent old-game assumptions.
