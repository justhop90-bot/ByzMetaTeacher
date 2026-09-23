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


  function injectPredicateIntoResearchRule(sourceText, tech, predicate) {
    const action = "(research " + tech + ")";
    const actionIndex = sourceText.indexOf(action);
    assert.notEqual(
      actionIndex,
      -1,
      "[Self-test] research action missing for " + tech,
    );
    const ruleStart = sourceText.lastIndexOf("(defrule", actionIndex);
    const ruleEnd = sourceText.indexOf("\n(defrule", actionIndex);
    const end = ruleEnd === -1 ? sourceText.length : ruleEnd;
    assert.ok(
      ruleStart >= 0 && ruleStart < end,
      "[Self-test] research rule bounds missing for " + tech,
    );
    const rule = sourceText.slice(ruleStart, end);
    const arrow = rule.indexOf("=>");
    assert.notEqual(
      arrow,
      -1,
      "[Self-test] research rule action boundary missing for " + tech,
    );
    const patched =
      rule.slice(0, arrow) +
      "    " + predicate + "\n" +
      rule.slice(arrow);
    return sourceText.slice(0, ruleStart) + patched + sourceText.slice(end);
  }

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
      name: "missing-closing-parenthesis",
      expected: "[Missing closing parenthesis]",
      source: baseline.replace(
        "(players-unit-type-count any-enemy scout-cavalry-line >= 1)",
        "(players-unit-type-count any-enemy scout-cavalry-line >= 1",
      ),
    },
    {
      name: "unexpected-closing-parenthesis",
      expected: "[Missing opening parenthesis]",
      source: baseline + "\n)\n",
    },
    {
      name: "empty-facts-section",
      expected: "empty facts section",
      source: baseline + "\n(defrule\n=>\n    (true)\n)\n",
    },
    {
      name: "empty-actions-section",
      expected: "empty actions section",
      source: baseline + "\n(defrule\n    (true)\n=>\n)\n",
    },
    {
      name: "logical-operator-requires-fact-expressions",
      expected: "must contain only fact expressions as operands",
      source: baseline + "\n(defrule\n    (or true (true))\n=>\n    (do-nothing)\n)\n",
    },
    {
      name: "nested-command-expression-rejected",
      expected: "contains a nested expression argument",
      source: baseline + "\n(defrule\n    (true)\n=>\n    (up-build place-normal 0 c: (castle))\n)\n",
    },
    {
      name: "unterminated-string",
      expected: "unterminated quoted string",
      source: baseline + '\n(defrule\n    (true)\n=>\n    (chat-local-to-self "unterminated)\n)\n',
    },
    {
      name: "malformed-defconst",
      expected: "requires exactly a name and one value",
      source: baseline + "\n(defconst broken)\n",
    },
    {
      name: "nested-defrule-rejected",
      expected: "is nested inside defrule",
      source: baseline + "\n(defrule\n    (defrule (true) => (do-nothing))\n=>\n    (do-nothing)\n)\n",
    },
    {
      name: "defconst-alias-cycle",
      expected: "alias cycle",
      source:
        baseline +
        "\n(defconst validator-alias-a validator-alias-b)\n" +
        "(defconst validator-alias-b validator-alias-a)\n",
    },
    {
      name: "unexpected-preprocessor-else",
      expected: "unexpected #else",
      source: baseline + "\n#else\n",
    },
    {
      name: "duplicate-preprocessor-else",
      expected: "duplicate #else",
      source:
        baseline +
        "\n#load-if-defined VALIDATOR_TEST\n#else\n#else\n#end-if\n",
    },
    {
      name: "unexpected-preprocessor-end-if",
      expected: "unexpected #end-if",
      source: baseline + "\n#end-if\n",
    },
    {
      name: "unterminated-preprocessor-conditional",
      expected: "unterminated conditional block",
      source: baseline + "\n#load-if-defined VALIDATOR_TEST\n",
    },
    {
      name: "malformed-preprocessor-conditional",
      expected: "malformed conditional directive",
      source: baseline + "\n#load-if-defined\n#end-if\n",
    },
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
      name: "heavy-plow-demand-writer-regression",
      expected: "[Castle eco]",
      source: baseline.replace(
        "    (set-goal bt-heavy-plow-demand-goal 1)",
        "    (set-goal bt-heavy-plow-demand-goal 0)",
      ),
    },
    ...[
      ["ri-heavy-plow", "heavy-plow"],
      ["ri-gold-mining", "gold-mining"],
      ["ri-wheel-barrow", "wheelbarrow"],
      ["ri-hand-cart", "hand-cart"],
      ["ri-bow-saw", "bow-saw"],
      ["ri-gold-shaft-mining", "gold-shaft-mining"],
    ].map(([tech, label]) => ({
      name: label + "-executor-package-veto-regression",
      expected: "[Castle eco]",
      source: injectPredicateIntoResearchRule(
        baseline,
        tech,
        "(goal bt-research-ranged-counter-package-goal 0)",
      ),
    })),
    {
      name: "dropsite-update-deferral-regression",
      expected: "[Villager hygiene]",
      source: baseline.replace(
        "(set-strategic-number sn-defer-dropsite-update 1)",
        "(set-strategic-number sn-defer-dropsite-update 0)",
      ),
    },
    {
      name: "villager-hygiene-house-headroom-regression",
      expected: "[Villager hygiene]",
      source: baseline.replace(
        "(housing-headroom <= 5)",
        "(housing-headroom <= 4)",
      ),
    },
    {
      name: "villager-hygiene-lumber-local-house-placement-regression",
      expected: "[Villager hygiene]",
      source: baseline.replace(
        "    (up-set-placement-data my-player-number lumber-camp c: 6)\n",
        "",
      ),
    },
    {
      name: "villager-hygiene-wood-dropsite-regression",
      expected: "[Villager hygiene]",
      source: baseline.replace(
        "    (dropsite-min-distance wood > 8)\n",
        "",
      ),
    },
    {
      name: "villager-hygiene-gold-dropsite-regression",
      expected: "[Villager hygiene]",
      source: baseline.replace(
        "    (dropsite-min-distance gold > 8)\n",
        "",
      ),
    },
    {
      name: "villager-hygiene-stone-dropsite-regression",
      expected: "[Villager hygiene]",
      source: baseline.replace(
        "    (dropsite-min-distance stone > 8)\n",
        "",
      ),
    },
    {
      name: "villager-hygiene-scout-defense-regression",
      expected: "[Villager hygiene]",
      source: baseline.replace(
        "    (up-target-objects 0 action-default -1 stance-defensive)\n",
        "    (up-target-objects 0 action-move -1 stance-defensive)\n",
      ),
    },
    {
      name: "horse-collar-demand-writer-regression",
      expected: "[Feudal eco]",
      source: (() => {
        const needle = "(set-goal bt-horse-collar-demand-goal 1)";
        const index = baseline.indexOf(needle);
        assert.ok(index >= 0, "[Self-test] Horse Collar demand writer missing");
        return baseline.slice(0, index) + baseline.slice(index).replace(needle, "(set-goal bt-horse-collar-demand-goal 0)");
      })(),
    },
    {
      name: "horse-collar-executor-package-veto-regression",
      expected: "[Feudal eco]",
      source: (() => {
        const needle = "(research ri-horse-collar)";
        const index = baseline.indexOf(needle);
        const ruleStart = baseline.lastIndexOf("(defrule", index);
        const ruleEnd = baseline.indexOf("\n)", index) + 2;
        assert.ok(ruleStart >= 0 && ruleEnd > ruleStart, "[Self-test] Horse Collar executor missing");
        const rule = baseline.slice(ruleStart, ruleEnd);
        const arrow = rule.indexOf("=>");
        assert.ok(arrow >= 0, "[Self-test] Horse Collar executor arrow missing");
        return baseline.slice(0, ruleStart) +
          rule.slice(0, arrow) +
          "    (goal bt-research-ranged-counter-package-goal 0)\n" +
          rule.slice(arrow) +
          baseline.slice(ruleEnd);
      })(),
    },
    {
      name: "double-bit-axe-executor-package-veto-regression",
      expected: "[Feudal eco]",
      source: (() => {
        const needle = "(research ri-double-bit-axe)";
        const index = baseline.indexOf(needle);
        const ruleStart = baseline.lastIndexOf("(defrule", index);
        const ruleEnd = baseline.indexOf("\n)", index) + 2;
        assert.ok(ruleStart >= 0 && ruleEnd > ruleStart, "[Self-test] Double-Bit Axe executor missing");
        const rule = baseline.slice(ruleStart, ruleEnd);
        const arrow = rule.indexOf("=>");
        assert.ok(arrow >= 0, "[Self-test] Double-Bit Axe executor arrow missing");
        return baseline.slice(0, ruleStart) +
          rule.slice(0, arrow) +
          "    (goal bt-research-cavalry-counter-package-goal 0)\n" +
          rule.slice(arrow) +
          baseline.slice(ruleEnd);
      })(),
    },
    {
      name: "horse-collar-hold-package-veto-regression",
      expected: "[Feudal eco]",
      source: (() => {
        const needle = "(set-goal bt-feudal-eco-hold-goal 1)";
        const index = baseline.indexOf(needle);
        const ruleStart = baseline.lastIndexOf("(defrule", index);
        const ruleEnd = baseline.indexOf("\n)", index) + 2;
        assert.ok(ruleStart >= 0 && ruleEnd > ruleStart, "[Self-test] Horse Collar hold missing");
        const rule = baseline.slice(ruleStart, ruleEnd);
        assert.ok(rule.includes("(goal bt-horse-collar-demand-goal 1)"), "[Self-test] Horse Collar hold demand witness missing");
        const arrow = rule.indexOf("=>");
        assert.ok(arrow >= 0, "[Self-test] Horse Collar hold arrow missing");
        return baseline.slice(0, ruleStart) +
          rule.slice(0, arrow) +
          "    (goal bt-research-siege-package-goal 0)\n" +
          rule.slice(arrow) +
          baseline.slice(ruleEnd);
      })(),
    },
    {
      name: "feudal-eco-hold-must-yield-at-castle-threshold",
      expected: "[Feudal eco]",
      source: (() => {
        const needle = "    (unit-type-count villager < bt-castle-villagers)\n";
        const index = baseline.indexOf(needle);
        assert.ok(index >= 0, "[Self-test] Feudal eco hold threshold witness is missing");
        return baseline.slice(0, index) + baseline.slice(index + needle.length);
      })(),
    },
    {
      name: "cataphract-demand-must-yield-to-imperial-feasibility",
      expected: "[Imperial transition]",
      source: (() => {
        const marker = "(defrule\n    (goal bt-castle-cataphract-demand-goal 1)";
        const start = baseline.indexOf(marker);
        assert.ok(start >= 0, "[Self-test] Cataphract withdrawal rule missing");
        const end = baseline.indexOf("\n=>", start);
        assert.ok(end > start, "[Self-test] Cataphract withdrawal arrow missing");
        const rule = baseline.slice(start, baseline.indexOf("\n)", end) + 2);
        const needle = "        (can-research-with-escrow imperial-age)\n";
        const mutated = rule.replace(needle, "");
        assert.notEqual(mutated, rule, "[Self-test] Cataphract Imperial-feasibility witness missing");
        return baseline.replace(rule, mutated);
      })(),
    },
    {
      name: "castle-eco-thresholds-must-be-early",
      expected: "[Castle eco]",
      source: baseline.replace("(defconst bt-hand-cart-villagers 36)", "(defconst bt-hand-cart-villagers 45)"),
    },
    {
      name: "double-bit-axe-must-yield-to-castle-commitment",
      expected: "[Feudal eco]",
      source: (() => {
        const needle = "    (not (goal bt-castle-commitment-goal 1))\n";
        const searchFrom = baseline.indexOf("(research ri-double-bit-axe)");
        const index = baseline.indexOf(needle, searchFrom);
        assert.ok(index >= 0, "[Self-test] Double-Bit Axe Castle-commitment witness is missing");
        return baseline.slice(0, index) + baseline.slice(index + needle.length);
      })(),
    },
    {
      name: "double-bit-axe-hold-package-veto-regression",
      expected: "[Feudal eco]",
      source: (() => {
        const needle = "(goal bt-double-bit-axe-demand-goal 1)";
        const index = baseline.indexOf(needle);
        const ruleStart = baseline.lastIndexOf("(defrule", index);
        const ruleEnd = baseline.indexOf("\n)", index) + 2;
        assert.ok(ruleStart >= 0 && ruleEnd > ruleStart, "[Self-test] Double-Bit Axe hold missing");
        const rule = baseline.slice(ruleStart, ruleEnd);
        const arrow = rule.indexOf("=>");
        assert.ok(arrow >= 0, "[Self-test] Double-Bit Axe hold arrow missing");
        return baseline.slice(0, ruleStart) +
          rule.slice(0, arrow) +
          "    (goal bt-research-monk-package-goal 0)\n" +
          rule.slice(arrow) +
          baseline.slice(ruleEnd);
      })(),
    },
    {
      name: "castle-bank-must-override-resource-mode",
      expected: "[Age banking]",
      source: (() => {
        const witness =
          "    (current-age == feudal-age)\n" +
          "    (goal bt-castle-cataphract-demand-goal 0)\n" +
          "    (goal bt-castle-commitment-goal 0)\n" +
          "    (goal bt-feudal-eco-hold-goal 0)\n" +
          "    (unit-type-count villager >= bt-castle-villagers)\n" +
          "=>\n" +
          "    (set-goal bt-resource-mode-goal bt-resource-mode-castle-bank)";
        const replacement =
          "    (goal bt-resource-mode-goal 0)\n" + witness;
        const index = baseline.indexOf(witness);
        assert.ok(index >= 0, "[Self-test] Castle bank priority witness is missing");
        return baseline.slice(0, index) +
          baseline.slice(index).replace(witness, replacement);
      })(),
    },
    {
      name: "castle-bank-must-directly-stop-villagers",
      expected: "[Age banking]",
      source: (() => {
        const needle = "    (set-goal train-civ-goal -1)\n";
        const searchFrom = baseline.indexOf("(set-goal bt-castle-commitment-goal 1)");
        const index = baseline.indexOf(needle, searchFrom);
        assert.ok(index >= 0, "[Self-test] Castle bank direct villager-stop witness is missing");
        return baseline.slice(0, index) + baseline.slice(index + needle.length);
      })(),
    },
    {
      name: "castle-bank-must-not-depend-on-feudal-eco-hold",
      expected: "[Age banking]",
      source: (() => {
        const marker = "(defrule\n    ; HARD CASTLE OWNERSHIP BOUNDARY.";
        const start = baseline.indexOf(marker);
        assert.ok(start >= 0, "[Self-test] hard Castle bank rule missing");
        const ruleEnd = baseline.indexOf("\n)", start) + 2;
        const rule = baseline.slice(start, ruleEnd);
        return baseline.slice(0, start) +
          rule.replace(
            "    (current-age == feudal-age)\n",
            "    (current-age == feudal-age)\n    (goal bt-feudal-eco-hold-goal 0)\n",
          ) +
          baseline.slice(ruleEnd);
      })(),
    },
    {
      name: "castle-villager-stop-must-not-require-research-queue",
      expected: "[Age transition]",
      source: (() => {
        const witness =
          "    (strategic-number sn-resource-control == 0)\n=>\n    ; Castle commitment owns the TC bank.";
        const replacement =
          "    (strategic-number sn-resource-control == 0)\n    (can-research-with-escrow castle-age)\n=>\n    ; Castle commitment owns the TC bank.";
        const index = baseline.indexOf(witness);
        assert.ok(index >= 0, "[Self-test] Castle stop-gate witness is missing");
        return baseline.slice(0, index) + baseline.slice(index).replace(witness, replacement);
      })(),
    },
    {
      name: "castle-commitment-must-pause-spear-production",
      expected: "[Age transition]",
      source: (() => {
        const witness =
          "    (goal bt-standing-army-demand-goal 1)\n" +
          "    (goal bt-castle-commitment-goal 0)\n" +
          "    (strategic-number sn-resource-control == 0)\n" +
          "    (building-type-count-total barracks >= 1)";
        const replacement =
          "    (goal bt-standing-army-demand-goal 1)\n" +
          "    (strategic-number sn-resource-control == 0)\n" +
          "    (building-type-count-total barracks >= 1)";
        const index = baseline.indexOf(witness);
        assert.ok(index >= 0, "[Self-test] Spear Castle-commitment gate witness is missing");
        return baseline.slice(0, index) + baseline.slice(index).replace(witness, replacement);
      })(),
    },
    {
      name: "castle-commitment-must-pause-skirmisher-production",
      expected: "[Age transition]",
      source: (() => {
        const witness =
          "    (goal bt-standing-army-demand-goal 1)\n" +
          "    (goal bt-castle-commitment-goal 0)\n" +
          "    (strategic-number sn-resource-control == 0)\n" +
          "    (building-type-count archery-range >= 1)\n" +
          "    (unit-type-count-total skirmisher-line < bt-standing-skirm-target-goal)";
        const replacement =
          "    (goal bt-standing-army-demand-goal 1)\n" +
          "    (strategic-number sn-resource-control == 0)\n" +
          "    (building-type-count archery-range >= 1)\n" +
          "    (unit-type-count-total skirmisher-line < bt-standing-skirm-target-goal)";
        const index = baseline.indexOf(witness);
        assert.ok(index >= 0, "[Self-test] Skirmisher Castle-commitment gate witness is missing");
        return baseline.slice(0, index) + baseline.slice(index).replace(witness, replacement);
      })(),
    },
    {
      name: "castle-commitment-must-pause-standing-archer-production",
      expected: "[Age transition]",
      source: (() => {
        const witness =
          "    (goal bt-standing-army-demand-goal 1)\n" +
          "    (goal bt-castle-commitment-goal 0)\n" +
          "    (strategic-number sn-resource-control == 0)\n" +
          "    (building-type-count archery-range >= 1)\n" +
          "    (unit-type-count-total archer-line < bt-standing-archer-target-goal)";
        const replacement =
          "    (goal bt-standing-army-demand-goal 1)\n" +
          "    (strategic-number sn-resource-control == 0)\n" +
          "    (building-type-count archery-range >= 1)\n" +
          "    (unit-type-count-total archer-line < bt-standing-archer-target-goal)";
        const index = baseline.indexOf(witness);
        assert.ok(index >= 0, "[Self-test] Standing Archer Castle-commitment gate witness is missing");
        return baseline.slice(0, index) + baseline.slice(index).replace(witness, replacement);
      })(),
    },
    {
      name: "castle-commitment-must-pause-rush-archer-production",
      expected: "[Age transition]",
      source: (() => {
        const witness =
          "    (goal strategy-goal bt-strategy-rush)\n" +
          "    (goal unit-goal archer-line)\n" +
          "    (goal bt-castle-commitment-goal 0)\n" +
          "    (strategic-number sn-resource-control == 0)";
        const replacement =
          "    (goal strategy-goal bt-strategy-rush)\n" +
          "    (goal unit-goal archer-line)\n" +
          "    (strategic-number sn-resource-control == 0)";
        const index = baseline.indexOf(witness);
        assert.ok(index >= 0, "[Self-test] RUSH Archer Castle-commitment gate witness is missing");
        return baseline.slice(0, index) + baseline.slice(index).replace(witness, replacement);
      })(),
    },
    {
      name: "imperial-villager-stop-must-not-require-research-queue",
      expected: "[Age transition]",
      source: (() => {
        const witness =
          "    (goal bt-castle-cataphract-demand-goal 0)\n=>\n    ; Imperial bank ownership stops civilian queue growth";
        const replacement =
          "    (goal bt-castle-cataphract-demand-goal 0)\n    (can-research-with-escrow imperial-age)\n=>\n    ; Imperial bank ownership stops civilian queue growth";
        const index = baseline.indexOf(witness);
        assert.ok(index >= 0, "[Self-test] Imperial stop-gate witness is missing");
        return baseline.slice(0, index) + baseline.slice(index).replace(witness, replacement);
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
      name: "scouting-first-pulse-not-30-rejected",
      expected: "[Scouting lifecycle]",
      source: baseline.replace(
        "(defconst bt-scout-first-pulse 30)",
        "(defconst bt-scout-first-pulse 120)",
      ),
    },
    {
      name: "scouting-home-pulse-too-slow-rejected",
      expected: "[Scouting lifecycle]",
      source: baseline.replace(
        "(defconst bt-scout-home-pulse 60)",
        "(defconst bt-scout-home-pulse 120)",
      ),
    },
    {
      name: "scouting-home-loop-without-target-fallback-rejected",
      expected: "[Scouting lifecycle]",
      source: (() => {
        const witness =
          "        (players-building-count target-player <= 0)\n";
        const ruleNeedle =
          "(up-send-scout bt-land-explore-group scout-flank)";
        const ruleStart = baseline.lastIndexOf("(defrule", baseline.indexOf(ruleNeedle));
        const ruleEnd = baseline.indexOf("\n)", baseline.indexOf(ruleNeedle)) + 2;
        assert.ok(ruleStart >= 0 && ruleEnd > ruleStart, "[Self-test] home scouting rule missing");
        const rule = baseline.slice(ruleStart, ruleEnd);
        assert.ok(rule.includes(witness), "[Self-test] home scouting target fallback witness missing");
        return baseline.slice(0, ruleStart) + rule.replace(witness, "") + baseline.slice(ruleEnd);
      })(),
    },
    {
      name: "scouting-enemy-loop-without-home-grace-rejected",
      expected: "[Scouting lifecycle]",
      source: (() => {
        const witness = "    (game-time >= bt-scout-home-grace)\n";
        const ruleNeedle =
          "(up-send-scout bt-land-explore-group scout-enemy)";
        const ruleStart = baseline.lastIndexOf("(defrule", baseline.indexOf(ruleNeedle));
        const ruleEnd = baseline.indexOf("\n)", baseline.indexOf(ruleNeedle)) + 2;
        assert.ok(ruleStart >= 0 && ruleEnd > ruleStart, "[Self-test] enemy scouting rule missing");
        const rule = baseline.slice(ruleStart, ruleEnd);
        assert.ok(rule.includes(witness), "[Self-test] enemy scouting home-grace witness missing");
        return baseline.slice(0, ruleStart) + rule.replace(witness, "    (game-time >= 120)\n") + baseline.slice(ruleEnd);
      })(),
    },
    {
      name: "crop-rotation-without-mature-farm-base-rejected",
      expected: "[Late-eco lifecycle]",
      source: baseline.replace(
        "    (building-type-count farm >= bt-crop-rotation-farm-threshold)\n",
        "",
      ),
    },
    {
      name: "two-man-saw-demand-without-villager-maturity-rejected",
      expected: "[Late-eco lifecycle]",
      source: baseline.replace(
        "    (unit-type-count villager >= bt-two-man-saw-villagers)\n",
        "",
      ),
    },
    {
      name: "two-man-saw-demand-without-lumberjack-maturity-rejected",
      expected: "[Late-eco lifecycle]",
      source: (() => {
        const witness =
          "    (unit-type-count villager-wood >= bt-two-man-saw-lumberjacks)\n";
        const index = baseline.indexOf(witness);
        assert.ok(index >= 0, "[Self-test] Two-Man Saw demand lumberjack witness is missing");
        return baseline.slice(0, index) + baseline.slice(index + witness.length);
      })(),
    },
    {
      name: "two-man-saw-executor-without-lumberjack-maturity-rejected",
      expected: "[Late-eco lifecycle]",
      source: (() => {
        const witness =
          "    (unit-type-count villager-wood >= bt-two-man-saw-lumberjacks)\n";
        const first = baseline.indexOf(witness);
        const second = baseline.indexOf(witness, first + witness.length);
        assert.ok(
          first >= 0 && second >= 0,
          "[Self-test] Two-Man Saw lumberjack witnesses are missing from baseline",
        );
        return (
          baseline.slice(0, second) +
          baseline.slice(second + witness.length)
        );
      })(),
    },
    {
      name: "two-man-saw-executor-without-villager-maturity-rejected",
      expected: "[Late-eco lifecycle]",
      source: (() => {
        const maturityWitness =
          "    (unit-type-count villager >= bt-two-man-saw-villagers)\n";
        const first = baseline.indexOf(maturityWitness);
        const second = baseline.indexOf(maturityWitness, first + maturityWitness.length);
        assert.ok(
          first >= 0 && second >= 0,
          "[Self-test] Two-Man Saw maturity witnesses are missing from baseline",
        );
        return (
          baseline.slice(0, second) +
          baseline.slice(second + maturityWitness.length)
        );
      })(),
    }
    {
      name: "narration-verbosity-gate-regression",
      expected: "[Narration]",
      source: (() => {
        const needle = "    (up-compare-goal bt-debug-verbosity-goal >= 1)\n    (goal strategy-goal bt-strategy-flush)";
        const index = baseline.indexOf(needle);
        assert.ok(index >= 0, "[Self-test] strategy narration gate witness is missing");
        return baseline.slice(0, index) + baseline.slice(index).replace(
          "    (up-compare-goal bt-debug-verbosity-goal >= 1)\n",
          "",
        );
      })(),
    },
    {
      name: "narration-edge-trigger-regression",
      expected: "[Narration]",
      source: (() => {
        const needle =
          "    (up-compare-goal bt-debug-last-strategy-goal != bt-strategy-flush)\n";
        const index = baseline.indexOf(needle);
        assert.ok(index >= 0, "[Self-test] strategy narration latch witness is missing");
        return baseline.slice(0, index) + baseline.slice(index + needle.length);
      })(),
    },
    {
      name: "narration-strategic-write-regression",
      expected: "[Narration]",
      source: baseline.replace(
        "(set-goal bt-debug-last-strategy-goal bt-strategy-flush)",
        "(set-goal strategy-goal bt-strategy-rush)",
      ),
    },
    {
      name: "narration-canonical-message-regression",
      expected: "[Narration]",
      source: baseline.replace(
        'BASILISK | STRATEGY | CASTLE-POWER: pressure survives the age-up.',
        "BASILISK | STRATEGY | CASTLE-POWER: removed.",
      ),
    },
    {
      name: "narration-castle-block-regression",
      expected: "[Narration]",
      source: baseline.replace(
        'BASILISK | AGE | Castle blocked: engine feasibility.',
        'BASILISK | AGE | Castle blocked: missing.',
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
      name: "goal-fact-comparison",
      expected: "[Goal syntax]",
      source:
        baseline +
        "\n(defrule\n    (goal bt-attack-reserve-goal > 0)\n=>\n    (true)\n)\n",
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
      name: "standalone-typed-prefix-in-player-number",
      expected: "command-arity-mismatch",
      source:
        baseline +
        "\n(defrule\n    (players-unit-type-count g: bt-villager-defense-raider-player-goal scout-cavalry-line >= 1)\n=>\n    (true)\n)\n",
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
          "scouting-first-pulse-not-30-rejected",
          "scouting-home-pulse-too-slow-rejected",
          "villager-hygiene-house-headroom-regression",
          "villager-hygiene-lumber-local-house-placement-regression",
          "villager-hygiene-wood-dropsite-regression",
          "villager-hygiene-gold-dropsite-regression",
          "villager-hygiene-stone-dropsite-regression",
          "villager-hygiene-scout-defense-regression",
          "double-bit-axe-demand-cannot-be-cleared-by-castle-feasibility",
          "crop-rotation-maturity-witness",
          "two-man-saw-demand-maturity-witness",
          "two-man-saw-executor-maturity-witness",
          "scouting-home-loop-without-target-fallback",
          "scouting-enemy-loop-without-home-grace",
          "two-man-saw-demand-lumberjack-maturity-witness",
          "two-man-saw-executor-lumberjack-maturity-witness",
        ],
        parserSyntaxClasses: [
          "missing-closing-parenthesis",
          "unexpected-closing-parenthesis",
          "empty-facts-section",
          "empty-actions-section",
          "logical-operator-requires-fact-expressions",
          "nested-command-expression-rejected",
          "unterminated-string",
          "malformed-defconst",
          "nested-defrule-rejected",
          "defconst-alias-cycle",
          "unexpected-preprocessor-else",
          "duplicate-preprocessor-else",
          "unexpected-preprocessor-end-if",
          "unterminated-preprocessor-conditional",
          "malformed-preprocessor-conditional",
        ],
        schemaMismatchClasses: [
          "command-arity-mismatch",
          "command-family-mismatch",
          "command-typed-prefix-mismatch",
          "command-typed-operand-mismatch",
          "command-nested-expression-mismatch",
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
