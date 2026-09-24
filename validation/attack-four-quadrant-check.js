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
  return;
}

const rows = parseCsv(fs.readFileSync(inputPath, "utf8"));
const expectedQuadrants = [
  "Q1 +delta/parity",
  "Q2 zero-delta/parity",
  "Q3 zero-delta/inferior",
  "Q4 negative-delta/inferior",
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
];

const failures = [];
const seen = new Set();

for (const key of expectedQuadrants) {
  const row = rows.find((candidate) => candidate.test === key);
  if (row) seen.add(key);
}

for (const key of required) {
  if (!(rows[0] && Object.prototype.hasOwnProperty.call(rows[0], key))) {
    failures.push("missing column: " + key);
  }
}

if (rows.length !== 4) {
  failures.push("expected exactly 4 populated test rows, found " + rows.length);
}

for (const key of expectedQuadrants) {
  if (!seen.has(key)) failures.push("missing quadrant row: " + key);
}

for (const row of rows) {
  const startBuildings = Number(row.start_buildings);
  const endBuildings = Number(row.end_buildings);
  const recordedDelta = Number(row.delta);
  const relativeForce = Number(row.relative_force);
  const resultGoal = row.result_goal;
  const timerEnabled = String(row.attack_timer_enabled).toLowerCase();
  const timerSeconds = Number(row.attack_timer_seconds);
  const due = Number(row.next_attack_due);
  const actual = Number(row.next_attack_actual);

  if (![startBuildings, endBuildings, recordedDelta, relativeForce, timerSeconds, due, actual].every(Number.isFinite)) {
    failures.push(row.test + ": non-numeric telemetry field");
    continue;
  }

  const computedDelta = startBuildings - endBuildings;
  if (computedDelta !== recordedDelta) {
    failures.push(
      row.test + ": delta mismatch; expected " + computedDelta + ", recorded " + recordedDelta
    );
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
    "s; cadenceError=" + cadenceError + "s"
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
