#!/usr/bin/env node

import assert from "node:assert/strict";
import path from "node:path";
import { spawnSync } from "node:child_process";

const repoRoot = path.resolve(import.meta.dirname, "..");
const validatorPath = path.join(repoRoot, "validation", "basilisk-validator.js");

function run(args) {
  return spawnSync(process.execPath, [validatorPath, ...args, "--contract-only"], {
    cwd: repoRoot,
    encoding: "utf8",
  });
}

const baseline = run(["--profile=8596a45"]);
const baselineOutput = String(baseline.stdout ?? "") + "\n" + String(baseline.stderr ?? "");

assert.notEqual(
  baseline.status,
  0,
  "[Profile self-test] 8596a45 baseline should currently stop on a real engine-limit violation",
);
assert.ok(
  !baselineOutput.includes("[Goal namespace] reserved high-range GoalId 775 is missing"),
  "[Profile self-test] 8596a45 profile must bypass the post-baseline GoalId 775 requirement",
);
assert.match(
  baselineOutput,
  /\[Rule too long\]/,
  "[Profile self-test] 8596a45 profile must still enforce the DE rule-element ceiling",
);

const modern = run([]);
const modernOutput = String(modern.stdout ?? "") + "\n" + String(modern.stderr ?? "");
assert.notEqual(
  modern.status,
  0,
  "[Profile self-test] default profile should reject the restored 8596a45 controller",
);
assert.match(
  modernOutput,
  /\[Goal namespace\] reserved high-range GoalId 775 is missing/,
  "[Profile self-test] default profile must retain the modern GoalId requirement",
);

const unknown = run(["--profile=not-a-profile"]);
const unknownOutput = String(unknown.stdout ?? "") + "\n" + String(unknown.stderr ?? "");
assert.notEqual(
  unknown.status,
  0,
  "[Profile self-test] unknown validator profiles must be rejected",
);
assert.match(
  unknownOutput,
  /\[Profile\].*unknown|Unknown validator profile/,
  "[Profile self-test] unknown profile diagnostic is missing",
);

console.log(JSON.stringify({
  status: "PASS",
  profile: "8596a45",
  assertions: [
    "post-baseline GoalId requirements are profile-scoped",
    "DE rule-element limit remains enforced",
    "default profile remains strict",
    "unknown profiles are rejected",
  ],
}, null, 2));
