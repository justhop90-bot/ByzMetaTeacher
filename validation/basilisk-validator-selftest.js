#!/usr/bin/env node

import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const repoRoot = path.resolve(import.meta.dirname, "..");
const validatorPath = path.join(repoRoot, "validation", "basilisk-validator.js");
const controllerPath = path.join(repoRoot, "Basilisk", "Basilisk.per");
const baseline = fs.readFileSync(controllerPath, "utf8");

function runValidator(sourceText, name) {
  const tempPath = path.join(tempRoot, name + ".per");
  fs.writeFileSync(tempPath, sourceText, "utf8");
  const result = spawnSync(
    process.execPath,
    [validatorPath, tempPath],
    { cwd: repoRoot, encoding: "utf8" },
  );
  return {
    ...result,
    output: (result.stdout ?? "") + "\n" + (result.stderr ?? ""),
    path: tempPath,
  };
}

const tempRoot = fs.mkdtempSync(
  path.join(os.tmpdir(), "basilisk-validator-selftest-"),
);

try {
  const baselineResult = runValidator(baseline, "baseline");
  assert.equal(
    baselineResult.status,
    0,
    "[Self-test] baseline controller did not pass the real validator",
  );

  const stringSafeController =
    baseline +
    '\n(defrule\n    (true)\n=>\n    (chat-local-to-self "validator literal (paren) ; semicolon")\n)\n';
  const stringSafeResult = runValidator(stringSafeController, "string-safe");
  assert.equal(
    stringSafeResult.status,
    0,
    "[Self-test] strings containing parentheses/semicolons were misparsed",
  );

  const onagerRule = baseline.match(
    /\(defrule[\s\S]*?\(train onager\)[\s\S]*?\n\)/,
  )?.[0];
  assert.ok(onagerRule, "[Self-test] onager train rule signature missing");

  const castleRule = baseline.match(
    /\(defrule[\s\S]*?\(build castle\)[\s\S]*?\n\)/,
  )?.[0];
  assert.ok(castleRule, "[Self-test] castle build rule signature missing");

  const ducSearch = baseline.match(
    /\(up-find-local c: [A-Za-z][A-Za-z0-9_-]* c: \d+\)/,
  )?.[0];
  assert.ok(ducSearch, "[Self-test] DUC search signature missing");

  const timerEnable = baseline.match(
    /\(enable-timer [A-Za-z][A-Za-z0-9_-]* [A-Za-z][A-Za-z0-9_-]*\)/,
  )?.[0];
  assert.ok(timerEnable, "[Self-test] timer signature missing");

  const mutations = [
    {
      name: "unknown-duc-identifier",
      expected: "constant-operand",
      source: baseline.replace(
        ducSearch,
        ducSearch.replace(
          /c: [A-Za-z][A-Za-z0-9_-]*/,
          "c: definitely-not-a-real-class",
        ),
      ),
    },
    {
      name: "unknown-timer",
      expected: "[Timer]",
      source: baseline.replace(
        timerEnable,
        timerEnable.replace(
          /\(enable-timer [^ ]+/,
          "(enable-timer definitely-not-a-timer",
        ),
      ),
    },
    {
      name: "missing-rule-arrow",
      expected: "[Rule structure]",
      source: baseline.replace(
        "=>\n    (set-strategic-number sn-resource-control 0)",
        "REMOVED\n    (set-strategic-number sn-resource-control 0)",
      ),
    },
    {
      name: "stray-top-level-form",
      expected: "[Top-level syntax]",
      source: baseline + "\n(garbage-command garbage-value)\n",
    },
    {
      name: "unrelated-train-witness",
      expected: "[Queue witness]",
      source: baseline.replace(
        onagerRule,
        onagerRule.replace(
          "(unit-type-count-total mangonel-line",
          "(unit-type-count-total villager",
        ),
      ),
    },
    {
      name: "unrelated-build-witness",
      expected: "[Foundation witness]",
      source: baseline.replace(
        castleRule,
        castleRule
          .replace(
            /\(building-type-count-total castle/g,
            "(building-type-count-total university",
          )
          .replace(
            /\(up-pending-objects c: castle/g,
            "(up-pending-objects c: university",
          ),
      ),
    },
    {
      name: "duplicate-defconst",
      expected: "[Defconst]",
      source: baseline + "\n(defconst bt-feudal-villagers 999)\n",
    },
    {
      name: "defconst-range",
      expected: "[Defconst]",
      source: baseline + "\n(defconst validator-too-large 40000)\n",
    },
    {
      name: "bad-goal-operand",
      expected: "goal-operand",
      source: baseline.replace(
        "(up-modify-goal bt-attack-reserve-goal g:- bt-standing-army-floor-goal)",
        "(up-modify-goal bt-attack-reserve-goal g:- definitely-not-a-goal)",
      ),
    },
    {
      name: "bad-strategic-number-operand",
      expected: "strategic-number-operand",
      source: baseline.replace(
        "(up-modify-sn sn-focus-player-number g:= bt-scout-target-player-goal)",
        "(up-modify-sn sn-focus-player-number s:= definitely-not-a-strategic-number)",
      ),
    },
  ];

  const reports = [];
  for (const mutation of mutations) {
    const result = runValidator(mutation.source, mutation.name);
    assert.notEqual(
      result.status,
      0,
      "[Self-test] mutation unexpectedly passed: " + mutation.name,
    );
    assert.ok(
      result.output.includes(mutation.expected),
      "[Self-test] mutation " +
        mutation.name +
        " failed without the expected diagnostic " +
        mutation.expected,
    );
    reports.push({
      name: mutation.name,
      status: result.status,
      diagnostic: mutation.expected,
    });
  }

  console.log(
    JSON.stringify(
      {
        status: "PASS",
        baseline: "PASS",
        stringSafety: "PASS",
        mutationFailures: reports,
      },
      null,
      2,
    ),
  );
} finally {
  fs.rmSync(tempRoot, { recursive: true, force: true });
}
