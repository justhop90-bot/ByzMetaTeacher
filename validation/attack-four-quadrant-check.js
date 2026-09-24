#!/usr/bin/env node
"use strict";

const fs = require("fs");

const inputPath = process.argv[2] || "validation/attack-four-quadrant-telemetry.csv";
const toleranceSeconds = Number(process.argv[3] || 10);

function fail(message) {
  console.error(message);
  process.exitCode = 1;
}

function parseCsv(text) {
  const lines = text.split(/\r?\n/).filter((line) => line.trim().length > 0);
  if (lines.length < 2) return [];
  const header = lines[0].split(",").map((value) => value.trim());
  return lines.slice(1).map((line) => {
    const values = line.split(",").map((value) => value.trim());
    return Object.fromEntries(header.map((key, index) => [key, values[index] ?? ""]));
  });
}

function expectedResult(delta, relativeForce) {
  if (delta > 0) return "DAMAGED";
  if (relativeForce < 0) return "STALLED";
  return "REASSESS";
}

function expectedTimer(result) {
  return { DAMAGED: 120, REASSESS: 180, STALLED: 300 }[result];
}

if (!fs.existsSync(inputPath)) {
  fail("[Attack test] telemetry file not found: " + inputPath);
  process.exit(1);
}

const rows = parseCsv(fs.readFileSync(inputPath, "utf8"));
const expectedQuadrants = [
  { name: "Q1 +delta/parity", deltaPositive: true, forceInferior: false, standingArmy: 0 },
  { name: "Q2 zero-delta/parity", deltaPositive: false, forceInferior: false, standingArmy: 0 },
  { name: "Q3 zero-delta/inferior", deltaPositive: false, forceInferior: true, standingArmy: 1 },
  { name: "Q4 negative-delta/inferior", deltaPositive: false, forceInferior: true, standingArmy: 1 },
];

const required = [
  "test",
  "start_time",
  "result_time",
  "next_attack_due",
  "start_buildings",
  "end_buildings",
  "delta",
  "relative_force",
  "result_goal",
  "attack_timer_enabled",
  "attack_timer_seconds",
  "next_attack_actual",
  "standing_army_demand",
];

const failures = [];
const seen = new Set();

for (const quadrant of expectedQuadrants) {
  const row = rows.find((candidate) => candidate.test === quadrant.name);
  if (row) seen.add(quadrant.name);
}

for (const key of required) {
  if (!(rows[0] && Object.prototype.hasOwnProperty.call(rows[0], key))) {
    failures.push("missing column: " + key);
  }
}

if (rows.length !== 4) {
  failures.push("expected exactly 4 populated test rows, found " + rows.length);
}

for (const quadrant of expectedQuadrants) {
  if (!seen.has(quadrant.name)) failures.push("missing quadrant row: " + quadrant.name);
}

for (const row of rows) {
  const quadrant = expectedQuadrants.find((candidate) => candidate.name === row.test);
  if (!quadrant) {
    failures.push("unexpected quadrant row: " + row.test);
    continue;
  }

  const startBuildings = Number(row.start_buildings);
  const endBuildings = Number(row.end_buildings);
  const recordedDelta = Number(row.delta);
  const relativeForce = Number(row.relative_force);
  const resultGoal = row.result_goal;
  const timerEnabled = String(row.attack_timer_enabled).toLowerCase();
  const timerSeconds = Number(row.attack_timer_seconds);
  const due = Number(row.next_attack_due);
  const actual = Number(row.next_attack_actual);
  const standingArmy = Number(row.standing_army_demand);
  const resultTime = Number(row.result_time);
  const startTime = Number(row.start_time);

  const requiredNumericFields = {
    start_time: row.start_time,
    result_time: row.result_time,
    next_attack_due: row.next_attack_due,
    start_buildings: row.start_buildings,
    end_buildings: row.end_buildings,
    delta: row.delta,
    relative_force: row.relative_force,
    attack_timer_seconds: row.attack_timer_seconds,
    next_attack_actual: row.next_attack_actual,
    standing_army_demand: row.standing_army_demand,
  };
  const blankFields = Object.entries(requiredNumericFields)
    .filter(([, value]) => String(value).trim() === "")
    .map(([key]) => key);

  if (blankFields.length > 0) {
    failures.push(row.test + ": missing telemetry fields: " + blankFields.join(", "));
    continue;
  }

  if (![startBuildings, endBuildings, recordedDelta, relativeForce, timerSeconds, due, actual, standingArmy, startTime, resultTime].every(Number.isFinite)) {
    failures.push(row.test + ": non-numeric telemetry field");
    continue;
  }

  const computedDelta = startBuildings - endBuildings;
  if (computedDelta !== recordedDelta) {
    failures.push(
      row.test + ": delta mismatch; expected " + computedDelta + ", recorded " + recordedDelta
    );
  }

  const actualDeltaClassPass = quadrant.deltaPositive ? computedDelta > 0 : computedDelta <= 0;
  if (!actualDeltaClassPass) {
    failures.push(
      row.test + ": delta quadrant mismatch; measured delta=" + computedDelta
    );
  }

  const actualForceClassPass = quadrant.forceInferior ? relativeForce < 0 : relativeForce >= 0;
  if (!actualForceClassPass) {
    failures.push(
      row.test + ": force quadrant mismatch; measured relative force=" + relativeForce
    );
  }

  if (standingArmy !== quadrant.standingArmy) {
    failures.push(
      row.test + ": standing-army demand mismatch; expected " + quadrant.standingArmy +
      ", recorded " + standingArmy
    );
  }

  if (resultTime < Number(row.start_time)) {
    failures.push(row.test + ": result_time precedes start_time");
  }

  const expected = expectedResult(computedDelta, relativeForce);
  if (resultGoal !== expected) {
    failures.push(
      row.test + ": result mismatch; expected " + expected + ", recorded " + resultGoal
    );
  }

  const expectedSeconds = expectedTimer(expected);
  if (timerEnabled !== "true" || timerSeconds !== expectedSeconds) {
    failures.push(
      row.test + ": timer mismatch; expected enabled/" + expectedSeconds + "s, recorded " +
      timerEnabled + "/" + timerSeconds + "s"
    );
  }

  const expectedDue = resultTime + expectedSeconds;
  const dueError = due - expectedDue;
  if (Math.abs(dueError) > toleranceSeconds) {
    failures.push(
      row.test + ": timer due-time error " + dueError + "s exceeds ±" + toleranceSeconds + "s"
    );
  }

  const cadenceError = actual - due;
  if (Math.abs(cadenceError) > toleranceSeconds) {
    failures.push(
      row.test + ": cadence error " + cadenceError + "s exceeds ±" + toleranceSeconds + "s"
    );
  }

  const expectedForceClass = relativeForce < 0 ? "INFERIOR" : "PARITY";
  const expectedDeltaClass = computedDelta > 0 ? "POSITIVE" : "NON-POSITIVE";
  console.log(
    row.test + ": " + expectedDeltaClass + " + " + expectedForceClass +
    " -> " + expected + "; timer=" + expectedSeconds +
    "s; dueError=" + dueError + "s; cadenceError=" + cadenceError + "s"
  );
}

if (failures.length > 0) {
  console.error("\nFAIL");
  for (const failure of failures) console.error("- " + failure);
  process.exitCode = 1;
} else {
  console.log(
    "\nPASS: four-quadrant attack telemetry is internally consistent (tolerance ±" +
    toleranceSeconds + "s)."
  );
}
