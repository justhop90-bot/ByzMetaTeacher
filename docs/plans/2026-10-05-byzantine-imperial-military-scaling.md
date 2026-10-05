# Byzantine Imperial Military Scaling Implementation Plan

Goal: implement the agreed Imperial standing floors, four hysteresis bands, upgrade package, production scaling, and attack-readiness reconciliation through the existing Byzantine strategy/control plane.

Architecture: add a pure ImperialBand resolver for deterministic policy tests, then lower the same policy through the existing NativeControlPlan Goal/Timer path. Community strategy demands consume the resulting band state; existing production-depth and endgame attack systems remain the execution owners.

Global constraints: preserve the existing lifecycle boundaries; timers are cadence only; floor loss is the highest-priority override; fortified escalation is valid only with the complete resource/siege package; no second scheduler; no unavailable Byzantine techs.

## Task 1: Imperial band policy and native controller
Files: create LearnerAI/Compiler/ir/imperial_resolver.py; modify LearnerAI/Compiler/ir/strategy.py and the native observation registries; tests in test_imperial_resolver_properties.py, test_strategy_compiler_integration.py, and test_fact_registry.py.
Behavior: states 0 standing, 1 open, 2 fortified, 3 gold-starved; exact floors 18/18/12; entry banks Open 2400F/2000W/2000G, Fortified 2400F/2400W/2600G plus 2 siege, Trash <=800G with 2400F/2200W; exits Open F<1800 or W<1500, Trash G>=1800; dwell 30/20/60/15/45/20/30/90/30 seconds as previously defined; cooldowns Open/Fortified 30s and Trash 45s; precedence FLOOR_BREAK > FORTIFIED_ESCALATION > ECONOMIC_COLLAPSE > NORMAL_EXIT > HOLD.
Tests: threshold values at N-1/N/N+1, timer T-1/T/T+1, cooldown T-1/T/T+1, floor-break precedence, live-guard recheck.

## Task 2: Standing Imperial military and upgrade package
Files: modify LearnerAI/Compiler/ir/community_strategy_packs.py; tests test_community_strategy_packs.py and test_strategy_production_vertical.py.
Behavior: persistent 18 Halberdiers, 18 Elite Skirmishers, 12 Hussars; Castle Pikeman and Elite Skirmisher upgrades from established 6-unit triggers; Husbandry from 6 Scout/Light Cav; Imperial Halberdier from 6 Pikemen; Hussar upgrade in Imperial; verified Forging, Iron Casting, Bracer support; never Blast Furnace or Bloodlines.

## Task 3: Band-specific scaling and provider depth
Files: modify community_strategy_packs.py; tests community strategy and strategy compiler integration.
Behavior: Open 24/24/16, pressure 30/30/20, severe 36 on the affected trash line; Fortified 24/20/10 with 6+ siege; Gold-starved 30/30/18 and 36/36/24 under high food/wood. Demands must be mutually exclusive per line. Existing Barracks/Range/Stable/Siege depth remains 2/3/4 tied to 6/12/18 and 2/4/6 standing demand thresholds, with replacement observations updated for the new trash backbone.

## Task 4: Attack readiness and canonical artifact
Files: modify strategy.py and endgame tests; regenerate Byzantine.per/manifest from tools/build_byzantine_bot.py.
Behavior: endgame push admission requires the Imperial military band to be above STANDING_FLOOR plus the 18/18/12 floor and existing siege/objective witnesses; remove the obsolete 4-Cataphract-or-6-unit shortcut without touching objective ownership or the 20-second attack pulse.
Verification: focused tests, canonical build, native zero-findings on generated and checked-in artifacts, full unittest suite, then authoritative Compiler CI before merging to main. The implementation audit also closes the verified native `players-military-population` inventory gap and requires offensive-objective ownership for Open Field/Trash recovery.