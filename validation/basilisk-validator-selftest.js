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


  function setNumericDefconst(sourceText, name, value) {
    const marker = "(defconst " + name + " ";
    const start = sourceText.indexOf(marker);
    assert.notEqual(
      start,
      -1,
      "[Self-test] missing defconst for " + name,
    );
    const end = sourceText.indexOf(")", start);
    assert.notEqual(end, -1, "[Self-test] malformed defconst for " + name);
    return (
      sourceText.slice(0, start) +
      "(defconst " + name + " " + value + ")" +
      sourceText.slice(end + 1)
    );
  }

  const boundaryPasses = [
    {
      name: "documented-unit-wildcard-count-slot-passes",
      source: baseline.replace(
        "(players-unit-type-count target-player trebuchet-set >= 1)",
        "(players-unit-type-count target-player villager-hunter >= 1)",
      ),
    },
    {
      name: "up-get-point-base-15998-passes",
      source:
        baseline +
        "\n(defconst validator-point-output-goal 15998)\n" +
        "\n(defrule\n    (true)\n=>\n    (up-get-point position-object validator-point-output-goal)\n)\n",
    },
    {
      name: "up-get-search-state-base-15996-passes",
      source:
        baseline +
        "\n(defconst validator-search-state-output-goal 15996)\n" +
        "\n(defrule\n    (true)\n=>\n    (up-get-search-state validator-search-state-output-goal)\n)\n",
    },
    {
      name: "up-get-cost-delta-base-15996-passes",
      source:
        baseline +
        "\n(defconst validator-cost-delta-output-goal 15996)\n" +
        "\n(defrule\n    (true)\n=>\n    (up-get-cost-delta validator-cost-delta-output-goal)\n)\n",
    },
    {
      name: "up-setup-cost-data-base-15996-passes",
      source:
        baseline +
        "\n(defconst validator-setup-cost-output-goal 15996)\n" +
        "\n(defrule\n    (true)\n=>\n    (up-setup-cost-data 1 validator-setup-cost-output-goal)\n)\n",
    },
  ];

  const boundaryFailures = [
    {
      name: "up-get-point-base-15999-fails",
      expected: "command-numeric-range-mismatch",
      source:
        baseline +
        "\n(defconst validator-point-output-goal 15999)\n" +
        "\n(defrule\n    (true)\n=>\n    (up-get-point position-object validator-point-output-goal)\n)\n",
    },
    {
      name: "up-get-search-state-base-15997-fails",
      expected: "command-numeric-range-mismatch",
      source:
        baseline +
        "\n(defconst validator-search-state-output-goal 15997)\n" +
        "\n(defrule\n    (true)\n=>\n    (up-get-search-state validator-search-state-output-goal)\n)\n",
    },
    {
      name: "up-get-cost-delta-base-15997-fails",
      expected: "command-numeric-range-mismatch",
      source:
        baseline +
        "\n(defconst validator-cost-delta-output-goal 15997)\n" +
        "\n(defrule\n    (true)\n=>\n    (up-get-cost-delta validator-cost-delta-output-goal)\n)\n",
    },
    {
      name: "up-setup-cost-data-base-15997-fails",
      expected: "command-numeric-range-mismatch",
      source:
        baseline +
        "\n(defconst validator-setup-cost-output-goal 15997)\n" +
        "\n(defrule\n    (true)\n=>\n    (up-setup-cost-data 1 validator-setup-cost-output-goal)\n)\n",
    },
  ];

  function buildRuleWithElementCount(elementCount) {
    assert.ok(
      elementCount >= 2,
      "[Self-test] element-count fixture requires at least one fact and one action",
    );
    const facts = Array(elementCount - 1)
      .fill("(true)")
      .join("\n    ");
    return (
      baseline +
      "\n(defrule\n    " +
      facts +
      "\n=>\n    (disable-self)\n)\n"
    );
  }

  function buildSingleLineRule(targetLength) {
    const base = "(defrule (true) => (disable-self))";
    assert.ok(
      targetLength >= base.length,
      "[Self-test] single-line fixture target must cover its base syntax",
    );
    return (
      baseline +
      "\n" +
      base.slice(0, base.indexOf("=>")) +
      " ".repeat(targetLength - base.length) +
      base.slice(base.indexOf("=>")) +
      "\n"
    );
  }

  function buildMultilineLongRule() {
    return (
      baseline +
      "\n(defrule\n    (true)\n=>    (disable-self))\n"
    );
  }

  function buildLineLengthFixture(targetLength) {
    const prefix = baseline + "\n;";
    return prefix + " ".repeat(targetLength - 1) + "\n";
  }

  const ruleLengthCases = [
    {
      name: "rule-elements-31-pass",
      expectedStatus: 0,
      source: buildRuleWithElementCount(31),
    },
    {
      name: "rule-elements-32-pass",
      expectedStatus: 0,
      source: buildRuleWithElementCount(32),
    },
    {
      name: "rule-elements-33-fail",
      expectedStatus: 1,
      expected: "[Rule too long]",
      source: buildRuleWithElementCount(33),
    },
    {
      name: "complex-single-line-defrule-150-pass",
      expectedStatus: 0,
      source: buildSingleLineRule(150),
    },
    {
      name: "complex-single-line-defrule-151-fail",
      expectedStatus: 1,
      expected: "[Complex single-line rule]",
      source: buildSingleLineRule(151),
    },
    {
      name: "multiline-long-rule-pass",
      expectedStatus: 0,
      source: buildMultilineLongRule(),
    },
    {
      name: "source-line-255-pass",
      expectedStatus: 0,
      source: buildLineLengthFixture(255),
    },
    {
      name: "source-line-256-fail",
      expectedStatus: 1,
      expected: "[Engine limits]",
      source: buildLineLengthFixture(256),
    },
  ];

  const ruleLengthReports = [];
  for (const testCase of ruleLengthCases) {
    const result = runValidator(testCase.source, testCase.name);
    assert.equal(
      result.status,
      testCase.expectedStatus,
      "[Self-test] unexpected rule-length result: " +
        testCase.name +
        "\n" +
        result.output,
    );
    if (testCase.expected) {
      assert.ok(
        result.output.includes(testCase.expected),
        "[Self-test] rule-length mutation " +
          testCase.name +
          " missed diagnostic " +
          testCase.expected,
      );
    }
    ruleLengthReports.push({
      name: testCase.name,
      status: result.status,
    });
  }

  const mutations = [
    {
      name: "DE-runtime-rejected-arbalester-alias",
      expected: "DE runtime canonical identifier",
      source: baseline.replace(/\barbalest\b/g, "arbalester"),
    },
    {
      name: "scout-total-count-rejected-for-dispatch",
      expected: "[Scout contract]",
      source: baseline.replace(
        "(unit-type-count scout-cavalry-line >= 1)",
        "(unit-type-count-total scout-cavalry-line >= 1)",
      ),
    },
    {
      name: "farm-raw-wood-gate-rejected-with-escrow",
      expected: "[Escrow farm]",
      source: baseline.replace(
        "(can-build-with-escrow farm)",
        "(wood-amount >= bt-farm-build-wood)\n    (can-build-with-escrow farm)",
      ),
    },
    {
      name: "late-threat-state-block-rejected",
      expected: "[State order]",
      source: (() => {
        const start = baseline.indexOf(
          ";================================================================\n; 2A. DERIVED ENEMY THREAT STATE",
        );
        const end = baseline.indexOf(
          ";================================================================\n; MONASTERY / MONK DEMAND",
        );
        const marker = baseline.indexOf(
          ";================================================================\n; 12E. MAP-AWARE OPENING SELECTION",
        );
        assert.notEqual(start, -1, "[Self-test] derived threat-state block start missing");
        assert.notEqual(end, -1, "[Self-test] derived threat-state block end missing");
        assert.notEqual(marker, -1, "[Self-test] map-aware opening marker missing");
        assert.ok(end > start, "[Self-test] derived threat-state block bounds invalid");
        assert.ok(marker > end, "[Self-test] expected late insertion point after early block");
        const block = baseline.slice(start, end);
        const without = baseline.slice(0, start) + baseline.slice(end);
        const lateMarker = without.indexOf(
          ";================================================================\n; 12E. MAP-AWARE OPENING SELECTION",
        );
        assert.notEqual(lateMarker, -1, "[Self-test] late insertion marker missing after extraction");
        return without.slice(0, lateMarker) + block + "\n" + without.slice(lateMarker);
      })(),
    },
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
      name: "unknown-class-wildcard-unit-id-rejected",
      expected: "[AIRef schema]",
      source: baseline.replace(
        "(unit-type-count infantry-class >= bt-siege-tower-payload-min)",
        "(unit-type-count definitely-not-a-real-unit-class >= bt-siege-tower-payload-min)",
      ),
    },
    {
      name: "documented-unit-wildcard-rejected-in-non-count-unit-slot",
      expected: "undocumented AIRef object identifier",
      source:
        baseline +
        "\n(defrule\n    (true)\n=>\n    (up-set-attack-stance trebuchet-set c: stance-aggressive)\n)\n",
    },
    {
      name: "documented-unit-wildcard-rejected-in-garrison-slot",
      expected: "undocumented AIRef object identifier",
      source: baseline.replace(
        "(up-garrison siege-tower c: infantry-class)",
        "(up-garrison villager-hunter c: infantry-class)",
      ),
    },
    {
      name: "object-display-name-rejected-as-runtime-identifier",
      expected: "undocumented AIRef object identifier",
      source: baseline.replace(
        "(up-garrison siege-tower c: infantry-class)",
        "(up-garrison Arbalest c: infantry-class)",
      ),
    },
    {
      name: "bare-siege-tower-object-slot-rejected",
      expected: "[Invalid identifier]",
      source: baseline.replace(
        "(defconst siege-tower 1105)",
        "(defconst siege-tower-invalid-placeholder 1105)",
      ),
    },
    {
      name: "bare-logistica-tech-slot-rejected-without-defconst",
      expected: "site-specific engine identifier",
      source: baseline.replace(
        "(defconst ri-logistica 61)",
        "(defconst ri-logistica-invalid-placeholder 61)",
      ),
    },
    {
      name: "unknown-symbolic-const-value-rejected",
      expected: "undocumented AIRef value",
      source: baseline.replace(
        "(set-goal bt-research-cataphract-package-goal ri-logistica)",
        "(set-goal bt-research-cataphract-package-goal definitely-not-a-const)",
      ),
    },
    {
      name: "double-bit-axe-demand-cannot-be-cleared-by-castle-feasibility",
      expected: "[DBA lifecycle]",
      source: (() => {
        const pendingWitness =
          "(up-research-status c: ri-double-bit-axe >=\nresearch-pending)";
        assert.ok(
          baseline.includes(pendingWitness),
          "[Self-test] DBA pending-state witness missing from baseline",
        );
        return baseline.replace(
          pendingWitness,
          "(or (can-research-with-escrow castle-age) " + pendingWitness + ")",
        );
      })(),
    },
    {
      name: "castle-cataphract-demand-cannot-block-ready-imperial",
      expected: "[Castle-Cataphract/Imperial handoff]",
      source: baseline.replace(
        "    ; Do not create a Castle capability obligation once Imperial is already executable.\n" +
          "    ; Imperial age authority owns the transition when its engine feasibility witness is true.\n" +
          "    (not (can-research-with-escrow imperial-age))\n",
        "",
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
      name: "unknown-airef-command",
      expected: "[AIRef command]",
      source: baseline.replace(
        "(goal strategy-goal bt-strategy-boom)",
        "(definitely-not-an-airef-command strategy-goal bt-strategy-boom)",
      ),
    },
    {
      name: "command-role-mismatch",
      expected: "[AIRef command]",
      source:
        baseline +
        "\n(defrule\n    (disable-self)\n=>\n    (true)\n)\n",
    },
    {
      name: "unsafe-point-output-goal",
      expected: "command-numeric-range-mismatch",
      source: baseline.replace(
        "(up-get-point position-object bt-siege-tower-wall-point-goal)",
        "(up-get-point position-object bt-feudal-villagers)",
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
    {
      name: "command-arity-mismatch",
      expected: "command-arity-mismatch",
      source:
        baseline +
        "\n(defrule\n    (up-compare-goal bt-attack-reserve-goal == 1 2)\n=>\n    (do-nothing)\n)\n",
    },
    {
      name: "command-family-mismatch",
      expected: "command-family-mismatch",
      source:
        baseline +
        "\n(defrule\n    (up-compare-goal sn-resource-control == 1)\n=>\n    (do-nothing)\n)\n",
    },
    {
      name: "command-typed-prefix-mismatch",
      expected: "command-typed-prefix-mismatch",
      source:
        baseline +
        "\n(defrule\n    (true)\n=>\n    (up-build place-normal 0 c:= castle)\n)\n",
    },
    {
      name: "command-typed-operand-mismatch",
      expected: "command-typed-operand-mismatch",
      source:
        baseline +
        "\n(defrule\n    (up-compare-goal bt-attack-reserve-goal g:== sn-resource-control)\n=>\n    (do-nothing)\n)\n",
    },
    {
      name: "strict-enum-value-mismatch",
      expected: "command-argument-mismatch",
      source:
        baseline +
        "\n(defrule\n    (true)\n=>\n    (up-build place-norml 0 c: castle)\n)\n",
    },
    {
      name: "unsafe-set-target-object",
      expected: "unsafe-set-target-object",
      source:
        baseline +
        "\n(defrule\n    (true)\n=>\n    (up-full-reset-search)\n    (up-set-target-object search-remote c: 0)\n)\n",
    },
    {
      name: "unscoped-duc-target",
      expected: "unscoped-duc-target",
      source:
        baseline +
        "\n(defrule\n    (true)\n=>\n    (up-full-reset-search)\n    (up-target-objects 0 action-default -1 -1)\n)\n",
    },
    {
      name: "command-numeric-range-mismatch",
      expected: "command-numeric-range-mismatch",
      source:
        baseline +
        "\n(defrule\n    (true)\n=>\n    (up-find-local c: castle c: 241)\n)\n",
    },
    {
      name: "split-typed-comparison",
      expected: "split-typed-comparison",
      source:
        baseline +
        "\n(defrule\n    (up-compare-goal bt-attack-reserve-goal < g: 1)\n=>\n    (do-nothing)\n)\n",
    },
  ];


  const boundaryPassReports = [];
  for (const boundary of boundaryPasses) {
    const result = runValidator(boundary.source, boundary.name);
    assert.equal(
      result.status,
      0,
      "[Self-test] legal AIRef output boundary unexpectedly failed: " +
        boundary.name +
        "\n" +
        result.output,
    );
    boundaryPassReports.push({
      name: boundary.name,
      status: result.status,
    });
  }

  const boundaryFailureReports = [];
  for (const boundary of boundaryFailures) {
    const result = runValidator(boundary.source, boundary.name);
    assert.notEqual(
      result.status,
      0,
      "[Self-test] illegal AIRef output boundary unexpectedly passed: " +
        boundary.name,
    );
    assert.ok(
      result.output.includes(boundary.expected),
      "[Self-test] illegal boundary " +
        boundary.name +
        " failed without the expected diagnostic " +
        boundary.expected,
    );
    boundaryFailureReports.push({
      name: boundary.name,
      status: result.status,
      diagnostic: boundary.expected,
    });
  }

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
        boundaryPasses: boundaryPassReports,
        boundaryFailures: boundaryFailureReports,
        ruleLengthCases: ruleLengthReports,
        ruleSizeCases: ruleLengthReports,
        semanticRegressionClasses: [
          "scout-total-count-rejected-for-dispatch",
          "farm-raw-wood-gate-rejected-with-escrow",
          "late-threat-state-block-rejected",
          "castle-cataphract-demand-cannot-block-ready-imperial",
          "double-bit-axe-demand-cannot-be-cleared-by-castle-feasibility",
        ],
        schemaMismatchClasses: [
          "command-arity-mismatch",
          "command-family-mismatch",
          "command-typed-prefix-mismatch",
          "command-typed-operand-mismatch",
        "strict-enum-value-mismatch",
        "unsafe-set-target-object",
        "unscoped-duc-target",
        ],
      },
      null,
      2,
    ),
  );
} finally {
  fs.rmSync(tempRoot, { recursive: true, force: true });
}
