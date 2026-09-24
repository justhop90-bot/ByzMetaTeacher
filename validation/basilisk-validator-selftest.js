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

function runValidator(sourceText, name, extraArgs = []) {
  const tempPath = path.join(tempRoot, name + ".per");
  fs.writeFileSync(tempPath, sourceText, "utf8");
  const result = spawnSync(
    process.execPath,
    [validatorPath, tempPath, ...extraArgs],
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

  const semanticPath = path.join(tempRoot, "semantic-rules.json");
  const semanticResult = spawnSync(
    process.execPath,
    [validatorPath, controllerPath, "--dump-semantic-rules", semanticPath],
    { cwd: repoRoot, encoding: "utf8" },
  );
  assert.equal(
    semanticResult.status,
    0,
    "[Self-test] semantic rule dump failed",
  );
  assert.equal(
    semanticResult.error,
    undefined,
    "[Self-test] semantic rule dump process failed to start",
  );
  assert.ok(
    fs.existsSync(semanticPath),
    "[Self-test] semantic rule dump file was not created",
  );
  const semanticRules = JSON.parse(
    fs.readFileSync(semanticPath, "utf8"),
  );

  const findSemanticRule = (label, predicate) => {
    const matches = semanticRules.filter(predicate);
    assert.equal(
      matches.length,
      1,
      "[Semantic self-test] " + label + " expected exactly one matching rule; found " + matches.length,
    );
    return matches[0];
  };

  const ruleSection = (rule, side) => {
    const arrow = rule.args.findIndex(
      (arg) => arg.kind === "atom" && arg.value === "=>",
    );
    assert.ok(arrow >= 0, "[Semantic self-test] rule has no => separator");
    return side === "actions"
      ? rule.args.slice(arrow + 1)
      : rule.args.slice(0, arrow);
  };

  const containsExpression = (expressions, head, values = []) => {
    const visit = (expr) => {
      if (!expr || expr.kind !== "expression") return false;
      if (
        expr.head === head &&
        expr.args.length === values.length &&
        values.every(
          (value, index) =>
            expr.args[index]?.kind === "atom" &&
            expr.args[index].value === value,
        )
      ) {
        return true;
      }
      return expr.args.some((child) => visit(child));
    };
    return expressions.some((expr) => visit(expr));
  };

  const hasFact = (rule, head, values = []) =>
    ruleSection(rule, "facts").some((expr) =>
      containsExpression([expr], head, values),
    );
  const hasAction = (rule, head, values = []) =>
    ruleSection(rule, "actions").some((expr) =>
      containsExpression([expr], head, values),
    );

  const scalePackage = findSemanticRule(
    "Scale Mail package writer",
    (rule) =>
      hasFact(rule, "goal", [
        "bt-research-cavalry-counter-package-goal",
        "0",
      ]) &&
      hasAction(rule, "set-goal", [
        "bt-research-cavalry-counter-package-goal",
        "ri-scale-mail",
      ]),
  );
  assert.ok(
    hasFact(scalePackage, "up-compare-goal", [
      "bt-standing-spear-target-goal",
      ">=",
      "bt-spear-target-1",
    ]) &&
      hasFact(scalePackage, "unit-type-count-total", [
        "spearman-line",
        ">=",
        "bt-spear-target-1",
      ]),
    "[Semantic self-test] Scale Mail writer and executor capability witnesses are disconnected",
  );

  const scaleExecutors = semanticRules.filter((rule) =>
    hasAction(rule, "research", ["ri-scale-mail"]),
  );
  assert.ok(
    scaleExecutors.length > 0,
    "[Semantic self-test] Scale Mail has no research executor",
  );
  for (const rule of scaleExecutors) {
    assert.ok(
      hasFact(rule, "up-compare-goal", [
        "bt-standing-spear-target-goal",
        ">=",
        "bt-spear-target-1",
      ]) &&
        hasFact(rule, "unit-type-count-total", [
          "spearman-line",
          ">=",
          "bt-spear-target-1",
        ]),
      "[Semantic self-test] Scale Mail executor lacks its writer capability witness",
    );
  }

  const caFletching = findSemanticRule(
    "Feudal Cavalry-Archer Fletching executor",
    (rule) =>
      hasFact(rule, "current-age", ["==", "feudal-age"]) &&
      hasFact(rule, "unit-type-count-total", [
        "cavalry-archer-line",
        ">=",
        "3",
      ]) &&
      hasFact(rule, "goal", [
        "bt-research-ranged-counter-package-goal",
        "ri-fletching",
      ]) &&
      hasAction(rule, "research", ["ri-fletching"]),
  );
  assert.ok(
    hasFact(caFletching, "can-research-with-escrow", ["ri-fletching"]),
    "[Semantic self-test] CA Fletching executor lacks escrow feasibility",
  );

  findSemanticRule(
    "CA Fletching -> Bodkin bridge",
    (rule) =>
      hasFact(rule, "goal", [
        "bt-research-ranged-counter-package-goal",
        "ri-fletching",
      ]) &&
      hasFact(rule, "up-research-status", [
        "c:",
        "ri-fletching",
        "==",
        "research-complete",
      ]) &&
      hasFact(rule, "current-age", [">=", "castle-age"]) &&
      hasFact(rule, "unit-type-count-total", [
        "cavalry-archer-line",
        ">=",
        "3",
      ]) &&
      hasAction(rule, "set-goal", [
        "bt-research-ranged-counter-package-goal",
        "ri-bodkin-arrow",
      ]),
  );

  findSemanticRule(
    "Fletching terminal package release",
    (rule) =>
      hasFact(rule, "goal", [
        "bt-research-ranged-counter-package-goal",
        "ri-fletching",
      ]) &&
      hasFact(rule, "up-research-status", [
        "c:",
        "ri-fletching",
        "==",
        "research-complete",
      ]) &&
      hasFact(rule, "up-research-status", [
        "c:",
        "ri-bodkin-arrow",
        "==",
        "research-complete",
      ]) &&
      hasAction(rule, "set-goal", [
        "bt-research-ranged-counter-package-goal",
        "0",
      ]),
  );

  findSemanticRule(
    "completed Pike package release",
    (rule) =>
      hasFact(rule, "goal", [
        "bt-research-cavalry-counter-package-goal",
        "ri-pikeman",
      ]) &&
      hasFact(rule, "up-research-status", [
        "c:",
        "ri-pikeman",
        "==",
        "research-complete",
      ]) &&
      hasFact(rule, "goal", ["bt-halberdier-demand-goal", "0"]) &&
      hasAction(rule, "set-goal", [
        "bt-research-cavalry-counter-package-goal",
        "0",
      ]),
  );

  findSemanticRule(
    "completed Halberdier package release",
    (rule) =>
      hasFact(rule, "goal", [
        "bt-research-cavalry-counter-package-goal",
        "ri-halberdier",
      ]) &&
      hasFact(rule, "up-research-status", [
        "c:",
        "ri-halberdier",
        "==",
        "research-complete",
      ]) &&
      hasAction(rule, "set-goal", [
        "bt-research-cavalry-counter-package-goal",
        "0",
      ]),
  );

  findSemanticRule(
    "hard Castle bank",
    (rule) =>
      hasFact(rule, "current-age", ["==", "feudal-age"]) &&
      hasFact(rule, "unit-type-count", [
        "villager",
        ">=",
        "bt-castle-villagers",
      ]) &&
      hasFact(rule, "goal", ["bt-resource-mode-goal", "0"]) &&
      hasAction(rule, "set-goal", [
        "bt-resource-mode-goal",
        "bt-resource-mode-castle-bank",
      ]) &&
      hasAction(rule, "set-goal", [
        "bt-castle-commitment-goal",
        "1",
      ]),
  );

  findSemanticRule(
    "hard Imperial bank",
    (rule) =>
      hasFact(rule, "current-age", ["==", "castle-age"]) &&
      hasFact(rule, "unit-type-count", [
        "villager",
        ">=",
        "bt-imperial-villagers",
      ]) &&
      hasFact(rule, "goal", ["bt-resource-mode-goal", "0"]) &&
      hasAction(rule, "set-goal", [
        "bt-resource-mode-goal",
        "bt-resource-mode-imperial-bank-prep",
      ]) &&
      hasAction(rule, "set-goal", [
        "bt-imperial-commitment-goal",
        "1",
      ]),
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

  function mutateRuleContaining(sourceText, requiredFragments, mutate, label) {
    const starts = [];
    let offset = 0;
    while (true) {
      const start = sourceText.indexOf("(defrule", offset);
      if (start === -1) break;
      const end = sourceText.indexOf("\n(defrule", start);
      const ruleEnd = end === -1 ? sourceText.length : end;
      const rule = sourceText.slice(start, ruleEnd);
      if (requiredFragments.every((fragment) => rule.includes(fragment))) {
        starts.push([start, ruleEnd, rule]);
      }
      offset = ruleEnd;
    }
    assert.equal(starts.length, 1, "[Self-test] expected one matching rule: " + label);
    const [start, end, rule] = starts[0];
    const mutated = mutate(rule);
    assert.notEqual(mutated, rule, "[Self-test] mutation made no change: " + label);
    return sourceText.slice(0, start) + mutated + sourceText.slice(end);
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
    const result = runValidator(testCase.source, testCase.name, ["--contract-only"]);
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
      name: "logical-operator-arity-rejected",
      expected: "has 3 operands; expected exactly 2",
      source:
        baseline +
        "\n(defrule\n    (or (true) (true) (true))\n=>\n    (do-nothing)\n)\n",
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
      name: "duplicate-goal-id-rejected",
      expected: "[Goal namespace] duplicate GoalId 768",
      source:
        baseline +
        "\n(defconst validator-duplicate-goal 768)\n",
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
      name: "resource-mode-override-without-p0-exclusion-rejected",
      expected: "mode-0 exception",
      source: (() => {
        return mutateRuleContaining(
          baseline,
          [
            "(goal bt-imperial-prereq-demand-goal 1)",
            "(set-goal bt-resource-mode-goal bt-resource-mode-imperial-prereq)",
          ],
          (rule) =>
            rule.replace(
              "    (not (goal bt-resource-mode-goal bt-resource-mode-wood-crisis))\n",
              "",
            ),
          "Imperial prerequisite resource-mode override",
        );
      })(),
    },
    {
      name: "attack-negative-result-bucket-rejected",
      expected: "[Attack result]",
      source: (() => {
        const needle =
          "    (up-compare-goal bt-attack-buildings-destroyed-goal <= 0)\n";
        const index = baseline.indexOf(needle);
        assert.ok(
          index >= 0,
          "[Self-test] attack non-positive result witness is missing",
        );
        return (
          baseline.slice(0, index) +
          baseline.slice(index).replace(
            needle,
            "    (up-compare-goal bt-attack-buildings-destroyed-goal == 0)\n",
          )
        );
      })(),
    },
    {
      name: "attack-feudal-allocation-missing-rejected",
      expected: "[Attack allocation]",
      source: (() => {
        const start = baseline.indexOf(
          "(defrule (up-compare-goal bt-standing-army-floor-goal == 4)",
        );
        assert.ok(
          start >= 0,
          "[Self-test] Feudal attack allocation rule is missing",
        );
        const end = baseline.indexOf("))", start);
        assert.ok(
          end > start,
          "[Self-test] Feudal attack allocation rule bounds are missing",
        );
        return baseline.slice(0, start) + baseline.slice(end + 2);
      })(),
    },
    {
      name: "feudal-castle-threshold-regression-rejected",
      expected: "[Feudal economy]",
      source: baseline.replace(
        "(defconst bt-castle-villagers 28)",
        "(defconst bt-castle-villagers 30)",
      ),
    },
    {
      name: "feudal-boom-floor-regression-rejected",
      expected: "[Feudal economy]",
      source: mutateRuleContaining(
        baseline,
        [
          "(current-age == feudal-age)",
          "(goal strategy-goal bt-strategy-boom)",
          "(set-goal bt-standing-army-floor-goal bt-feudal-boom-army-floor)",
        ],
        (rule) =>
          rule.replace(
            "    (set-goal bt-standing-army-floor-goal bt-feudal-boom-army-floor)\n",
            "",
          ),
        "Feudal BOOM floor normalization",
      ),
    },
    {
      name: "feudal-farm-budget-floor-regression-rejected",
      expected: "[Feudal farm budget]",
      source: baseline.replace(
        "(defconst bt-feudal-farm-wood-floor 385)",
        "(defconst bt-feudal-farm-wood-floor 330)",
      ),
    },
    {
      name: "feudal-farm-budget-hold-regression-rejected",
      expected: "[Feudal farm budget]",
      source: mutateRuleContaining(
        baseline,
        [
          "(current-age == feudal-age)",
          "(goal strategy-goal bt-strategy-boom)",
          "(set-goal bt-feudal-farm-wood-hold-goal 1)",
        ],
        (rule) =>
          rule.replace(
            "    (wood-amount < bt-feudal-farm-wood-floor)\n",
            "",
          ),
        "Feudal BOOM farm-budget writer",
      ),
    },
    {
      name: "feudal-farm-budget-emergency-escape-regression-rejected",
      expected: "[Feudal farm budget]",
      source: mutateRuleContaining(
        baseline,
        [
          "(current-age == feudal-age)",
          "(goal strategy-goal bt-strategy-boom)",
          "(set-goal bt-feudal-farm-wood-hold-goal 1)",
        ],
        (rule) =>
          rule.replace(
            "    (food-amount >= 350)\n",
            "",
          ),
        "Feudal BOOM farm-budget emergency escape",
      ),
    },
    {
      name: "feudal-farm-budget-executor-regression-rejected",
      expected: "[Feudal farm budget]",
      source: mutateRuleContaining(
        baseline,
        [
          "(current-age == feudal-age)",
          "(can-build-with-escrow farm)",
          "(build farm)",
          "(building-type-count-total farm < bt-farm-feudal-cap)",
        ],
        (rule) =>
          rule.replace(
            "    (goal bt-feudal-farm-wood-hold-goal 0)\n",
            "",
          ),
        "Feudal farm executor hold",
      ),
    },
    {
      name: "feudal-farm-budget-bypass-executor-regression-rejected",
      expected: "[Feudal farm budget]",
      source:
        baseline +
        "\n(defrule\n" +
        "    (current-age == feudal-age)\n" +
        "    (can-build-with-escrow farm)\n" +
        "    (building-type-count-total farm < bt-farm-feudal-cap)\n" +
        "    (up-pending-objects c: farm == 0)\n" +
        "=>\n" +
        "    (build farm)\n" +
        ")\n",
    },
    {
      name: "feudal-attack-castle-bank-regression-rejected",
      expected: "[Feudal economy]",
      source: mutateRuleContaining(
        baseline,
        [
          "(timer-triggered bt-attack-timer)",
          "(goal attack-goal 0)",
          "(attack-now)",
          "(goal bt-castle-commitment-goal 0)",
        ],
        (rule) =>
          rule.replace(
            "    (goal bt-castle-commitment-goal 0)\n",
            "",
          ),
        "Feudal attack Castle commitment gate",
      ),
    },
    {
      name: "siege-abort-cancels-independent-demand-rejected",
      expected: "[Imperial siege]",
      source: (() => {
        return mutateRuleContaining(
          baseline,
          [
            "(military-population < bt-imperial-siege-abort-army-floor)",
            "(set-goal bt-standing-army-demand-goal 1)",
          ],
          (rule) =>
            rule.replace(
              "    (set-goal bt-standing-army-demand-goal 1)\n",
              "    (set-goal bt-standing-army-demand-goal 1)\n    (set-goal bt-mangonel-demand-goal 0)\n",
            ),
          "Imperial siege abort generic-demand ownership",
        );
      })(),
    },
    {
      name: "backoff-expiry-owner-missing-rejected",
      expected: "[Retry fairness]",
      source: (() => {
        const start = baseline.indexOf(
          "(defrule\n    (timer-triggered bt-research-blacksmith-failure-backoff-timer)",
        );
        assert.ok(
          start >= 0,
          "[Self-test] Blacksmith backoff expiry owner is missing",
        );
        const end = baseline.indexOf("\n(defrule", start + 8);
        assert.ok(
          end > start,
          "[Self-test] Blacksmith backoff expiry owner bounds are missing",
        );
        return baseline.slice(0, start) + baseline.slice(end);
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
      name: "elite-varangian-local-tech-id-required",
      expected: "site-specific engine identifier 'ri-elite-varangian-guard'",
      source: baseline.replace(
        "(defconst ri-elite-varangian-guard 1454)",
        "(defconst ri-elite-varangian-guard-invalid-placeholder 1454)",
      ),
    },
    {
      name: "elite-varangian-barracks-authority-required",
      expected: "[Elite Varangian] Imperial upgrade must use a Barracks capability witness",
      source: (() => {
        const action = "(research ri-elite-varangian-guard)";
        const actionIndex = baseline.indexOf(action);
        assert.notEqual(actionIndex, -1, "[Self-test] Elite Varangian research action missing");
        const start = baseline.lastIndexOf("(defrule", actionIndex);
        const end = baseline.indexOf("\n(defrule", actionIndex);
        const ruleEnd = end === -1 ? baseline.length : end;
        assert.ok(start >= 0 && start < ruleEnd, "[Self-test] Elite Varangian research rule bounds missing");
        const rule = baseline.slice(start, ruleEnd);
        const mutated = rule
          .replace("(building-type-count-total barracks >= 1)", "(building-type-count-total castle >= 1)")
          .replace("(goal bt-research-barracks-claim-goal 0)", "(goal bt-research-castle-claim-goal 0)");
        return baseline.slice(0, start) + mutated + baseline.slice(ruleEnd);
      })(),
    },
    {
      name: "blacksmith-feasibility-veto-regression",
      expected: "[Blacksmith] ri-fletching executor cannot use Imperial feasibility as a discretionary-tech veto",
      source: mutateRuleContaining(
        baseline,
        [
          "(current-age >= castle-age)",
          "(building-type-count blacksmith >= 1)",
          "(research ri-fletching)",
          "(goal bt-research-ranged-counter-package-goal ri-fletching)",
          "(or (current-age > castle-age) (not (goal bt-imperial-commitment-goal 1)))",
        ],
        (rule) => {
          const needle = "(not (goal bt-imperial-commitment-goal 1))";
          const mutated = rule.replace(needle, "(not (can-research-with-escrow imperial-age))");
          assert.notEqual(mutated, rule, "[Self-test] Fletching Imperial gate mutation made no change");
          return mutated;
        },
        "Castle/Imperial Fletching feasibility gate",
      ),
    },
    {
      name: "blacksmith-ranged-threat-loss-cancellation-regression",
      expected: "[Blacksmith] ranged package must survive threat loss while friendly ranged mass remains",
      source: baseline.replace(
        "    (goal bt-ranged-threat-goal 0)\n    (goal bt-blacksmith-ranged-army-goal 0)",
        "    (goal bt-ranged-threat-goal 0)",
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
      source: mutateRuleContaining(
        baseline,
        [
          "(set-goal bt-housing-demand-goal 1)",
          "(housing-headroom <= bt-housing-headroom-trigger)",
        ],
        (rule) =>
          rule.replace(
            "(housing-headroom <= bt-housing-headroom-trigger)",
            "(housing-headroom <= 4)",
          ),
        "housing headroom trigger",
      ),
    },
    {
      name: "villager-hygiene-house-emergency-headroom-regression",
      expected: "[Villager hygiene]",
      source: mutateRuleContaining(
        baseline,
        [
          "(set-goal bt-housing-demand-goal 1)",
          "(population-headroom <= 0)",
        ],
        (rule) =>
          rule.replace("(population-headroom <= 0)", ""),
        "housing emergency population trigger",
      ),
    },
    {
      name: "villager-hygiene-first-house-builder-regression",
      expected: "[Villager hygiene]",
      source: mutateRuleContaining(
        baseline,
        [
          "(building-type-count-total house == 0)",
          "(up-assign-builders c: house c: 2)",
        ],
        (rule) =>
          rule.replace("    (up-assign-builders c: house c: 2)\n", ""),
        "first house two-builder handling",
      ),
    },
    {
      name: "villager-hygiene-house-pending-cap-regression",
      expected: "[Villager hygiene]",
      source: mutateRuleContaining(
        baseline,
        [
          "(goal bt-housing-demand-goal 1)",
          "(up-pending-objects c: house < bt-housing-pending-cap)",
        ],
        (rule) =>
          rule.replace(
            "(up-pending-objects c: house < bt-housing-pending-cap)",
            "(up-pending-objects c: house < 1)",
          ),
        "bounded pending house cap",
      ),
    },
    {
      name: "villager-hygiene-house-builder-reset-regression",
      expected: "[Villager hygiene]",
      source: mutateRuleContaining(
        baseline,
        [
          "(building-type-count house >= 1)",
          "(up-assign-builders c: house c: 1)",
        ],
        (rule) =>
          rule.replace("    (up-assign-builders c: house c: 1)\n", ""),
        "normal house builder reset",
      ),
    },
    {
      name: "villager-hygiene-house-fallback-can-build-regression",
      expected: "[Villager hygiene]",
      source: mutateRuleContaining(
        baseline,
        [
          "(goal bt-housing-demand-goal 1)",
          "(build house)",
        ],
        (rule) =>
          rule.replace("    (can-build house)\n", ""),
        "generic housing fallback feasibility",
      ),
    },
    {
      name: "villager-hygiene-local-house-placement-rejected",
      expected: "[Villager hygiene]",
      source: baseline +
        "\n(defrule\n" +
        "    (goal bt-housing-demand-goal 1)\n" +
        "    (building-type-count-total lumber-camp >= 1)\n" +
        "    (can-build house)\n" +
        "=>\n" +
        "    (up-set-placement-data my-player-number lumber-camp c: 6)\n" +
        "    (up-build place-control 0 c: house)\n" +
        ")\n",
    },
    {
      name: "villager-hygiene-first-lumber-pending-regression",
      expected: "[Villager hygiene]",
      source: mutateRuleContaining(
        baseline,
        [
          "(building-type-count-total lumber-camp == 0)",
          "(up-pending-objects c: lumber-camp == 0)",
        ],
        (rule) =>
          rule.replace("    (up-pending-objects c: lumber-camp == 0)\n", ""),
        "first lumber pending guard",
      ),
    },
    {
      name: "villager-hygiene-first-mining-pending-regression",
      expected: "[Villager hygiene]",
      source: mutateRuleContaining(
        baseline,
        [
          "(building-type-count-total mining-camp == 0)",
          "(up-pending-objects c: mining-camp == 0)",
        ],
        (rule) =>
          rule.replace("    (up-pending-objects c: mining-camp == 0)\n", ""),
        "first mining pending guard",
      ),
    },
    {
      name: "villager-hygiene-lumber-radius-regression",
      expected: "[Villager hygiene]",
      source: mutateRuleContaining(
        baseline,
        [
          "(up-modify-sn sn-lumber-camp-max-distance c:+ bt-dropsite-radius-step)",
        ],
        (rule) =>
          rule.replace(
            "    (up-modify-sn sn-lumber-camp-max-distance c:+ bt-dropsite-radius-step)\n",
            "",
          ),
        "adaptive lumber radius",
      ),
    },
    {
      name: "villager-hygiene-mining-radius-regression",
      expected: "[Villager hygiene]",
      source: mutateRuleContaining(
        baseline,
        [
          "(up-modify-sn sn-mining-camp-max-distance c:+ bt-dropsite-radius-step)",
        ],
        (rule) =>
          rule.replace(
            "    (up-modify-sn sn-mining-camp-max-distance c:+ bt-dropsite-radius-step)\n",
            "",
          ),
        "adaptive mining radius",
      ),
    },
    {
      name: "villager-hygiene-lumber-adjacent-override-regression",
      expected: "[Villager hygiene]",
      source: mutateRuleContaining(
        baseline,
        [
          "(dropsite-min-distance wood > 8)",
          "(set-strategic-number sn-allow-adjacent-dropsites 1)",
          "(build lumber-camp)",
        ],
        (rule) =>
          rule.replace(
            "    (set-strategic-number sn-allow-adjacent-dropsites 1)\n",
            "",
          ),
        "scoped lumber adjacent override",
      ),
    },
    {
      name: "villager-hygiene-mining-adjacent-override-regression",
      expected: "[Villager hygiene]",
      source: mutateRuleContaining(
        baseline,
        [
          "(dropsite-min-distance gold > 8)",
          "(set-strategic-number sn-allow-adjacent-dropsites 1)",
          "(build mining-camp)",
        ],
        (rule) =>
          rule.replace(
            "    (set-strategic-number sn-allow-adjacent-dropsites 1)\n",
            "",
          ),
        "scoped mining adjacent override",
      ),
    },
    {
      name: "villager-hygiene-dropsite-restore-regression",
      expected: "[Villager hygiene]",
      source: mutateRuleContaining(
        baseline,
        [
          "(goal bt-dropsite-placement-claim-goal 1)",
          "(set-strategic-number sn-allow-adjacent-dropsites 0)",
        ],
        (rule) =>
          rule.replace(
            "    (set-strategic-number sn-allow-adjacent-dropsites 0)\n",
            "",
          ),
        "dropsite override restoration",
      ),
    },
    {
      name: "villager-hygiene-dropsite-separation-regression",
      expected: "[Villager hygiene]",
      source: mutateRuleContaining(
        baseline,
        [
          "(set-strategic-number sn-dropsite-separation-distance bt-dropsite-normal-separation)",
          "(set-strategic-number sn-allow-adjacent-dropsites 0)",
        ],
        (rule) =>
          rule.replace(
            "    (set-strategic-number sn-dropsite-separation-distance bt-dropsite-normal-separation)\n",
            "",
          ),
        "dropsite normal separation restoration",
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
      name: "castle-bank-must-defer-to-p0-crisis",
      expected: "[Age banking]",
      source: mutateRuleContaining(
        baseline,
        [
          "(current-age == feudal-age)",
          "(unit-type-count villager >= bt-castle-villagers)",
          "(set-goal bt-resource-mode-goal bt-resource-mode-castle-bank)",
          "(set-goal bt-castle-commitment-goal 1)",
        ],
        (rule) =>
          rule.replace("    (goal bt-resource-mode-goal 0)\n", ""),
        "Castle bank P0 guard",
      ),
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
      name: "imperial-bank-must-directly-stop-villagers",
      expected: "[Age banking]",
      source: (() => {
        const marker = "(defrule\n    ; HARD IMPERIAL OWNERSHIP BOUNDARY WHEN NO P0 CRISIS IS ACTIVE";
        const start = baseline.indexOf(marker);
        assert.ok(start >= 0, "[Self-test] hard Imperial bank rule missing");
        const ruleEnd = baseline.indexOf("\n)", start) + 2;
        const rule = baseline.slice(start, ruleEnd);
        const needle = "    (set-goal train-civ-goal -1)\n";
        assert.ok(
          rule.includes(needle),
          "[Self-test] Imperial bank direct villager-stop witness is missing",
        );
        return baseline.replace(rule, rule.replace(needle, ""));
      })(),
    },
    {
      name: "imperial-bank-must-not-depend-on-cataphract-demand",
      expected: "[Age banking]",
      source: (() => {
        const marker = "(defrule\n    ; HARD IMPERIAL OWNERSHIP BOUNDARY WHEN NO P0 CRISIS IS ACTIVE";
        const start = baseline.indexOf(marker);
        assert.ok(start >= 0, "[Self-test] hard Imperial bank rule missing");
        const ruleEnd = baseline.indexOf("\n)", start) + 2;
        const rule = baseline.slice(start, ruleEnd);
        const inserted =
          "    (unit-type-count villager >= bt-imperial-villagers)\n" +
          "    (goal bt-castle-cataphract-demand-goal 0)\n";
        const witness =
          "    (unit-type-count villager >= bt-imperial-villagers)\n";
        assert.ok(
          rule.includes(witness),
          "[Self-test] Imperial bank threshold witness is missing",
        );
        return baseline.replace(rule, rule.replace(witness, inserted));
      })(),
    },
    {
      name: "imperial-villager-stop-must-not-depend-on-cataphract-demand",
      expected: "[Age transition]",
      source: (() => {
        const marker =
          "(defrule\n    (goal train-civ-goal 1)\n    (current-age == castle-age)\n    (unit-type-count villager >= bt-imperial-villagers)";
        const start = baseline.indexOf(marker);
        assert.ok(start >= 0, "[Self-test] Imperial villager stop gate missing");
        const end = baseline.indexOf("\n)", start) + 2;
        const rule = baseline.slice(start, end);
        const commitment =
          "    (goal bt-imperial-commitment-goal 1)\n";
        assert.ok(
          rule.includes(commitment),
          "[Self-test] Imperial commitment witness is missing",
        );
        const mutated = rule.replace(
          commitment,
          "    (goal bt-castle-cataphract-demand-goal 0)\n",
        );
        assert.notEqual(mutated, rule, "[Self-test] Imperial stop mutation did not apply");
        return baseline.replace(rule, mutated);
      })(),
    },
    {
      name: "imperial-research-must-not-depend-on-cataphract-demand",
      expected: "[Age transition]",
      source: (() => {
        const marker =
          "; Imperial age authority owns the transition once the civilian threshold is";
        const start = baseline.indexOf(marker);
        assert.ok(start >= 0, "[Self-test] Imperial research executor missing");
        const end = baseline.indexOf("\n)", start) + 2;
        const rule = baseline.slice(start, end);
        const commitment =
          "    (goal bt-imperial-commitment-goal 1)\n";
        assert.ok(
          rule.includes(commitment),
          "[Self-test] Imperial research commitment witness is missing",
        );
        const mutated = rule.replace(
          commitment,
          "    (goal bt-castle-cataphract-demand-goal 0)\n",
        );
        assert.notEqual(mutated, rule, "[Self-test] Imperial research mutation did not apply");
        return baseline.replace(rule, mutated);
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
      name: "imperial-siege-builder-must-not-depend-on-cataphract-demand",
      expected: "[Imperial prerequisites]",
      source: (() => {
        const needle = "    (building-type-count-total castle < 1)\n";
        const searchFrom = baseline.indexOf("; 15H. CASTLE -> IMPERIAL PREREQUISITE: SECOND QUALIFYING BUILDING");
        const index = baseline.indexOf(needle, searchFrom);
        assert.ok(index >= 0, "[Self-test] Imperial Siege builder anchor is missing");
        return baseline.slice(0, index) +
          baseline.slice(index).replace(
            needle,
            needle + "    (goal bt-castle-cataphract-demand-goal 0)\n",
          ) +
          baseline.slice(index + needle.length);
      })(),
    },
    {
      name: "imperial-university-builder-must-not-depend-on-cataphract-demand",
      expected: "[Imperial prerequisites]",
      source: (() => {
        const marker = "; 15I. CASTLE -> IMPERIAL PREREQUISITE: UNIVERSITY FALLBACK";
        const start = baseline.indexOf(marker);
        assert.ok(start >= 0, "[Self-test] Imperial University section missing");
        const needle = "    (building-type-count-total castle < 1)\n";
        const index = baseline.indexOf(needle, start);
        assert.ok(index >= 0, "[Self-test] Imperial University builder anchor is missing");
        return baseline.slice(0, index) +
          baseline.slice(index).replace(
            needle,
            needle + "    (goal bt-castle-cataphract-demand-goal 0)\n",
          ) +
          baseline.slice(index + needle.length);
      })(),
    },
    {
      name: "imperial-siege-provider-must-accept-monastery-or-university",
      expected: "[Imperial prerequisites]",
      source: (() => {
        const marker = "; 15H. CASTLE -> IMPERIAL PREREQUISITE: SECOND QUALIFYING BUILDING";
        const start = baseline.indexOf(marker);
        assert.ok(start >= 0, "[Self-test] Imperial Siege section missing");
        const end = baseline.indexOf(";---------------------------------------------------------------\n; 15I.", start);
        assert.ok(end > start, "[Self-test] Imperial Siege section bounds missing");
        const section = baseline.slice(start, end);
        const needle =
          "    (or\n" +
          "        (building-type-count-total monastery >= 1)\n" +
          "        (building-type-count-total university >= 1)\n" +
          "    )";
        assert.ok(section.includes(needle), "[Self-test] Siege two-of-three provider witness missing");
        return baseline.replace(needle, "    (building-type-count-total monastery >= 1)");
      })(),
    },
    {
      name: "imperial-university-provider-must-accept-monastery-or-siege",
      expected: "[Imperial prerequisites]",
      source: (() => {
        const marker = "; 15I. CASTLE -> IMPERIAL PREREQUISITE: UNIVERSITY FALLBACK";
        const start = baseline.indexOf(marker);
        assert.ok(start >= 0, "[Self-test] Imperial University section missing");
        const end = baseline.indexOf(";----------------------------------------------------------------\n; CASTLE PREREQUISITE CONSTRUCTION WATCHDOG", start);
        assert.ok(end > start, "[Self-test] Imperial University section bounds missing");
        const section = baseline.slice(start, end);
        const needle =
          "    (or\n" +
          "        (building-type-count-total monastery >= 1)\n" +
          "        (building-type-count-total siege-workshop >= 1)\n" +
          "    )";
        assert.ok(section.includes(needle), "[Self-test] University two-of-three provider witness missing");
        return baseline.replace(needle, "    (building-type-count-total monastery >= 1)");
      })(),
    },
    {
      name: "imperial-builders-must-consume-persistent-demand",
      expected: "[Imperial prerequisites]",
      source: (() => {
        const marker = "; 15H. CASTLE -> IMPERIAL PREREQUISITE: SECOND QUALIFYING BUILDING";
        const start = baseline.indexOf(marker);
        assert.ok(start >= 0, "[Self-test] Imperial Siege section missing");
        const end = baseline.indexOf(";---------------------------------------------------------------\n; 15I.", start);
        assert.ok(end > start, "[Self-test] Imperial Siege section bounds missing");
        const section = baseline.slice(start, end);
        const needle = "    (goal bt-imperial-prereq-demand-goal 1)\n";
        assert.ok(section.includes(needle), "[Self-test] Imperial persistent-demand gate missing");
        return baseline.replace(needle, "");
      })(),
    },
    {
      name: "imperial-funding-mode-must-override-bank-prep",
      expected: "[Imperial prerequisites]",
      source: (() => {
        const marker = "(goal bt-resource-mode-goal bt-resource-mode-imperial-prereq)";
        const start = baseline.indexOf(marker);
        assert.ok(start >= 0, "[Self-test] Imperial prerequisite funding mode missing");
        const needle = "    (current-age == castle-age)\n";
        const index = baseline.indexOf(needle, start);
        assert.ok(index >= 0, "[Self-test] Imperial funding mode anchor missing");
        return baseline.slice(0, index) +
          baseline.slice(index).replace(
            needle,
            "    (goal bt-resource-mode-goal 0)\n" + needle,
          ) +
          baseline.slice(index + needle.length);
      })(),
    },
    {
      name: "imperial-funding-mode-must-prioritize-wood",
      expected: "[Imperial prerequisites]",
      source: (() => {
        const marker = "(goal bt-resource-mode-goal bt-resource-mode-imperial-prereq)";
        const start = baseline.indexOf(marker);
        assert.ok(start >= 0, "[Self-test] Imperial prerequisite funding mode missing");
        const line = "    (set-strategic-number sn-wood-gatherer-percentage 40)\n";
        const index = baseline.indexOf(line, start);
        assert.ok(index >= 0, "[Self-test] Imperial prerequisite wood allocation missing");
        return baseline.slice(0, index) + baseline.slice(index).replace(line, "    (set-strategic-number sn-wood-gatherer-percentage 35)\n");
      })(),
    },
    {
      name: "imperial-demand-producer-must-exist",
      expected: "[Imperial prerequisites]",
      source: (() => {
        const needle = "    (set-goal bt-imperial-prereq-demand-goal 1)\n";
        const index = baseline.indexOf(needle);
        assert.ok(index >= 0, "[Self-test] Imperial demand producer witness is missing");
        return baseline.slice(0, index) + baseline.slice(index).replace(needle, "");
      })(),
    },
    {
      name: "imperial-funding-mode-must-yield-to-p0-crisis",
      expected: "[Imperial prerequisites]",
      source: (() => {
        const marker = "    ; Imperial prerequisite funding overrides age-bank arbitration, but P0";
        const start = baseline.indexOf(marker);
        assert.ok(start >= 0, "[Self-test] Imperial funding mode section missing");
        const needle = "    (not (goal bt-resource-mode-goal bt-resource-mode-food-crisis))\n";
        const index = baseline.indexOf(needle, start);
        assert.ok(index >= 0, "[Self-test] Imperial funding P0 food-crisis guard missing");
        return baseline.slice(0, index) +
          baseline.slice(index).replace(needle, "") +
          baseline.slice(index + needle.length);
      })(),
    },
    {
      name: "imperial-demand-clear-must-retain-world-state-witnesses",
      expected: "[Imperial prerequisites]",
      source: (() => {
        const needle =
          "    (goal bt-imperial-prereq-demand-goal 1)\n" +
          "    (or\n" +
          "        (current-age >= imperial-age)\n";
        const index = baseline.indexOf(needle);
        assert.ok(index >= 0, "[Self-test] Imperial demand-clear lifecycle witness is missing");
        return baseline.slice(0, index) + baseline.slice(index).replace(
          needle,
          "    (goal bt-imperial-prereq-demand-goal 1)\n",
        );
      })(),
    },
    {
      name: "imperial-demand-clear-must-not-use-cataphract-state",
      expected: "[Imperial prerequisites]",
      source: (() => {
        const marker = "; Clear prerequisite demand when the world already proves Imperial/Castle completion.";
        const start = baseline.indexOf(marker);
        assert.ok(start >= 0, "[Self-test] Imperial demand-clear section missing");
        const end = baseline.indexOf("; Temporarily favor wood while the second Castle-age provider is outstanding.", start);
        assert.ok(end > start, "[Self-test] Imperial demand-clear bounds missing");
        const section = baseline.slice(start, end);
        const needle = "    (can-research-with-escrow imperial-age)\n";
        assert.ok(section.includes(needle), "[Self-test] Imperial feasibility witness missing");
        return baseline.slice(0, start) + baseline.slice(start, end).replace(
          needle,
          needle + "    (goal bt-castle-cataphract-demand-goal 0)\n",
        ) + baseline.slice(end);
      })(),
    },
    {
      name: "imperial-villager-stop-must-not-require-research-queue",
      expected: "[Age transition]",
      source: (() => {
        const marker =
          "(defrule\n    (goal train-civ-goal 1)\n    (current-age == castle-age)\n    (unit-type-count villager >= bt-imperial-villagers)";
        const start = baseline.indexOf(marker);
        assert.ok(start >= 0, "[Self-test] Imperial stop-gate rule missing");
        const end = baseline.indexOf("\n)", start) + 2;
        const rule = baseline.slice(start, end);
        const arrow = rule.indexOf("=>");
        assert.ok(arrow >= 0, "[Self-test] Imperial stop-gate action boundary missing");
        const replacement =
          rule.slice(0, arrow) +
          "    (can-research-with-escrow imperial-age)\n" +
          rule.slice(arrow);
        return baseline.slice(0, start) + replacement + baseline.slice(end);
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
      name: "bbc-duc-target-loss-disarm-regression",
      expected: "[BBC DUC] armed latch must disarm when the enemy Trebuchet witness disappears",
      source: mutateRuleContaining(
        baseline,
        [
          "(goal bt-bombard-cannon-demand-goal 1)",
          "(goal bt-bombard-trebuchet-duc-armed-goal 1)",
          "(players-unit-type-count target-player trebuchet-set < 1)",
        ],
        (rule) =>
          rule.replace(
            "    (set-goal bt-bombard-trebuchet-duc-armed-goal 0)\n",
            "",
          ),
        "BBC DUC target-loss disarm",
      ),
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
    const result = runValidator(boundary.source, boundary.name, ["--contract-only"]);
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

  const criticalMutationNames = new Set([
    "missing-closing-parenthesis",
    "unexpected-closing-parenthesis",
    "logical-operator-requires-fact-expressions",
    "logical-operator-arity-rejected",
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
    "duplicate-goal-id-rejected",
    "DE-runtime-rejected-arbalester-alias",
    "unknown-duc-identifier",
    "unknown-class-wildcard-unit-id-rejected",
    "documented-unit-wildcard-rejected-in-non-count-unit-slot",
    "bare-siege-tower-object-slot-rejected",
    "bare-logistica-tech-slot-rejected-without-defconst",
    "elite-varangian-local-tech-id-required",
    "resource-mode-override-without-p0-exclusion-rejected",
    "attack-negative-result-bucket-rejected",
    "feudal-farm-budget-floor-regression-rejected",
    "feudal-farm-budget-hold-regression-rejected",
    "feudal-farm-budget-emergency-escape-regression-rejected",
    "feudal-farm-budget-executor-regression-rejected",
    "feudal-farm-budget-bypass-executor-regression-rejected",
    "villager-hygiene-house-headroom-regression",
    "villager-hygiene-house-emergency-headroom-regression",
    "villager-hygiene-first-house-builder-regression",
    "villager-hygiene-house-pending-cap-regression",
    "villager-hygiene-house-builder-reset-regression",
    "villager-hygiene-house-fallback-can-build-regression",
    "villager-hygiene-local-house-placement-rejected",
    "villager-hygiene-first-lumber-pending-regression",
    "villager-hygiene-first-mining-pending-regression",
    "villager-hygiene-lumber-radius-regression",
    "villager-hygiene-mining-radius-regression",
    "villager-hygiene-lumber-adjacent-override-regression",
    "villager-hygiene-mining-adjacent-override-regression",
    "villager-hygiene-dropsite-restore-regression",
    "villager-hygiene-dropsite-separation-regression",
    "backoff-expiry-owner-missing-rejected",
    "siege-abort-cancels-independent-demand-rejected",
  ]);
  const criticalMutations = mutations.filter((mutation) =>
    criticalMutationNames.has(mutation.name),
  );
  assert.equal(
    criticalMutations.length,
    criticalMutationNames.size,
    "[Self-test] critical mutation inventory drifted; update the curated defensive set",
  );

  const reports = [];
  for (const mutation of criticalMutations) {
    const result = runValidator(mutation.source, mutation.name, ["--contract-only"]);
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
        mutationCount: criticalMutations.length,
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
          "resource-mode-explicit-override-contract",
          "attack-result-non-positive-partition",
          "backoff-expiry-owner-exact-inventory",
          "imperial-siege-abort-package-ownership",
          "feudal-farm-budget-floor",
          "feudal-farm-budget-hold-writer",
          "feudal-farm-budget-emergency-escape",
          "feudal-farm-budget-executor-hold",
          "feudal-farm-budget-bypass-executor",
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
    "bbc-duc-target-loss-disarm-regression",
        ],
      },
      null,
      2,
    ),
  );
} finally {
  fs.rmSync(tempRoot, { recursive: true, force: true });
}
