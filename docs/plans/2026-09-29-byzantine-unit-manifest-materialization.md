# Byzantine unit manifest materialization

This tranche promotes 12 safe Unit nodes from the pinned 185872 aoe2techtree `data.json` subset into the existing GameData graph.

Closed:
- UnitIds 550, 13, 545, 539, 21, 442, 2626, 2627, 1104, 17, 83, and 128.
- Manifest identity, provider building, age, line membership, base cost, and train time are pinned.
- Safe upgrade relations are materialized only where trigger technologies are already modeled: 280→550 via Tech 257; 539→21 via Tech 34; 21→442 via Tech 35; 2626→2627 via Tech 34.
- The 12-unit snapshot subset is immutable and carries ENGINE_DATA provenance.

Remaining:
- Fish Trap building 199.
- Carrack 2628, Demolition Ship 527, and Heavy Demolition Ship 528 remain blocked by unmodeled trigger TechIds 904, 905, and 244 respectively.
- TechIds 54, 408, and 909 remain blocked by source-identity conflicts.

Verification:
- Exact mainline Compiler run #2488: 1,116 tests passed; all native zero-findings gates passed; all nine native-support determinism jobs passed; snapshot comparison passed; aggregate Compiler verification gate passed.
