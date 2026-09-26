#!/usr/bin/env node

import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const repoRoot = path.resolve(import.meta.dirname, "..");
const validatorPath = path.join(repoRoot, "validation", "basilisk-validator.js");
const controllerPath = path.join(repoRoot, "Basilisk", "Basilisk.per");

function run(args) {
  return spawnSync(process.execPath, [validatorPath, ...args, "--contract-only"], {
    cwd: repoRoot,
    encoding: "utf8",
  });
}

function output(result) {
  return String(result.stdout ?? "") + "\n" + String(result.stderr ?? "");
}

function writeFixture(sourceText, suffix) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "basilisk-profile-selftest-"));
  const file = path.join(dir, "Basilisk-" + suffix + ".per");
  fs.writeFileSync(file, sourceText, "utf8");
  return { dir, file };
}

const validatorSource = fs.readFileSync(validatorPath, "utf8");
const controllerSource = fs.readFileSync(controllerPath, "utf8");

assert.match(
  validatorSource,
  /const engineLimitReport = validateEngineLimits\(source, rules\);/,
  "[Profile self-test] rule-length validation must remain unconditional across profiles",
);
assert.match(
  validatorSource,
  /validateLifecycleAnchors\(source, rules, validatorProfile\);/,
  "[Profile self-test] lifecycle validation must remain active for profile selection",
);
assert.match(
  validatorSource,
  /if \(validatorProfile\.requireRushStallLifecycle\) \{/,
  "[Profile self-test] modern-only RUSH stall lifecycle gate is not profile-scoped",
);

const goalProfileSource = controllerSource.replace(
  "(defconst bt-rush-stall-latch-goal 775)",
  "",
);
assert.notEqual(
  goalProfileSource,
  controllerSource,
  "[Profile self-test] GoalId 775 profile fixture could not remove the modern-only requirement",
);
const goalProfileFixture = writeFixture(goalProfileSource, "goal-profile");
try {
  const legacyProfile = run(["--profile=8596a45", goalProfileFixture.file]);
  assert.ok(
    !output(legacyProfile).includes("[Goal namespace] reserved high-range GoalId 775 is missing"),
    "[Profile self-test] 8596a45 profile must bypass the post-baseline GoalId 775 requirement",
  );

  const modernProfile = run([goalProfileFixture.file]);
  assert.match(
    output(modernProfile),
    /\[Goal namespace\] reserved high-range GoalId 775 is missing/,
    "[Profile self-test] default profile must enforce the modern GoalId requirement",
  );
} finally {
  fs.rmSync(goalProfileFixture.dir, { recursive: true, force: true });
}

const parserFixture = writeFixture(
  controllerSource +
    "\n(defrule\n    (true)\n=>\n)\n",
  "parser",
);
try {
  const result = run(["--profile=8596a45", parserFixture.file]);
  assert.notEqual(
    result.status,
    0,
    "[Profile self-test] malformed parser fixture must be rejected",
  );
  assert.match(
    output(result),
    /\[Rule structure\].*empty actions section|\[Rule too long\]/,
    "[Profile self-test] 8596a45 profile must still enforce parser/rule-length validation",
  );
} finally {
  fs.rmSync(parserFixture.dir, { recursive: true, force: true });
}

const duplicateFixture = writeFixture(
  controllerSource +
    "\n(defconst bt-profile-selftest-duplicate 1)\n(defconst bt-profile-selftest-duplicate 1)\n",
  "duplicate",
);
try {
  const result = run(["--profile=8596a45", duplicateFixture.file]);
  assert.notEqual(
    result.status,
    0,
    "[Profile self-test] duplicate defconst fixture must be rejected",
  );
  assert.match(
    output(result),
    /\[Defconst\] duplicate definition\(s\): bt-profile-selftest-duplicate/,
    "[Profile self-test] duplicate defconst diagnostics are missing",
  );
} finally {
  fs.rmSync(duplicateFixture.dir, { recursive: true, force: true });
}

const unknown = run(["--profile=not-a-profile"]);
const unknownOutput = output(unknown);
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
  assertions: [
    "post-baseline GoalId requirements are profile-scoped",
    "DE parser/rule validation remains enforced by the legacy profile",
    "default profile remains strict",
    "duplicate defconst ownership diagnostics remain enforced",
    "unknown profiles are rejected",
  ],
}, null, 2));
