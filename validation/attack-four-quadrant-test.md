# Basilisk four-quadrant attack runtime test

Purpose: validate that the building-delta attack result closes every arithmetic/force quadrant and produces the intended cooldown cadence.

## Checklist

- [ ] Start from the same controlled scenario for each isolated quadrant.
- [ ] Record attack start game time and result game time.
- [ ] Record target building count at attack start and result time.
- [ ] Record Basilisk relative force at result time.
- [ ] Verify \`delta = start_buildings - end_buildings\`.
- [ ] Verify expected result is derived, not manually selected:
  - \`delta > 0 -> DAMAGED\`
  - \`delta <= 0 AND relative force < 0 -> STALLED\`
  - \`delta <= 0 AND relative force >= 0 -> REASSESS\`
- [ ] Verify timer state and selected duration:
  - \`DAMAGED -> 120s\`
  - \`REASSESS -> 180s\`
  - \`STALLED -> 300s\`
- [ ] Record the actual next attack time.
- [ ] Verify cadence error is within ±10 seconds.
- [ ] Verify the four rows all pass together.
- [ ] For Q3/Q4, verify \`bt-standing-army-demand-goal = 1\`.
- [ ] Do not count an attack as passed merely because \`attack-now\` fired. The result, timer, and next attack cadence must agree.

## Four required rows

| Test | Delta | Force | Expected result | Expected timer |
|---|---:|---:|---|---:|
| Q1 +delta/parity | > 0 | >= 0 | DAMAGED | 120s |
| Q2 zero-delta/parity | <= 0 | >= 0 | REASSESS | 180s |
| Q3 zero-delta/inferior | <= 0 | < 0 | STALLED | 300s |
| Q4 negative-delta/inferior | <= 0 | < 0 | STALLED | 300s |

## Telemetry validation

Fill \`validation/attack-four-quadrant-telemetry.csv\`, then run:

\`\`\`powershell
node validation/attack-four-quadrant-check.js
\`\`\`

Optional cadence tolerance:

\`\`\`powershell
node validation/attack-four-quadrant-check.js validation/attack-four-quadrant-telemetry.csv 15
\`\`\`

The checker derives result and timer from measured \`delta\` and \`relative_force\`. It rejects mismatched recorded deltas, result goals, timers, missing quadrants, and cadence errors outside tolerance.

Runtime evidence remains separate from static validation. Passing the checker means the captured telemetry is internally consistent; it does not certify that the game itself produced the intended tactical behavior.
