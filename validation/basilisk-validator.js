#!/usr/bin/env node

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const repoRoot = path.resolve(import.meta.dirname, "..");
const controllerPath = path.resolve(
  process.argv[2] ?? path.join(repoRoot, "Basilisk", "Basilisk.per"),
);
const legacyValidatorPath = path.join(
  repoRoot,
  "validation",
  "repair-lifecycle-replay.js",
);

const source = fs.readFileSync(controllerPath, "utf8");

function stripComments(text) {
  return text
    .split("\n")
    .map((line) => line.split(";")[0])
    .join("\n");
}

function extractRules(text) {
  const rules = [];
  let cursor = 0;
  const sanitized = stripComments(text);
  while ((cursor = sanitized.indexOf("(defrule", cursor)) !== -1) {
    let depth = 0;
    let end = -1;
    for (let i = cursor; i < sanitized.length; i += 1) {
      if (sanitized[i] === "(") depth += 1;
      else if (sanitized[i] === ")") {
        depth -= 1;
        if (depth === 0) {
          end = i + 1;
          break;
        }
      }
    }
    assert.notEqual(end, -1, "[Parser] unclosed defrule");
    rules.push(sanitized.slice(cursor, end));
    cursor = end;
  }
  return rules;
}

function validateBalancedParens(text) {
  let depth = 0;
  let line = 1;
  for (const ch of stripComments(text)) {
    if (ch === "(") depth += 1;
    if (ch === ")") depth -= 1;
    assert.ok(depth >= 0, `[Parser] unexpected closing parenthesis near line ${line}`);
    if (ch === "\n") line += 1;
  }
  assert.equal(depth, 0, "[Parser] unclosed parenthesis at end of controller");
}

function validateBooleanArity(text) {
  const sanitized = stripComments(text);
  const logicalArity = new Map([
    ["not", 1],
    ["and", 2],
    ["nand", 2],
    ["nor", 2],
    ["or", 2],
    ["xor", 2],
    ["xnor", 2],
  ]);
  let cursor = 0;
  while ((cursor = sanitized.indexOf("(defrule", cursor)) !== -1) {
    let depth = 0;
    let end = -1;
    for (let i = cursor; i < sanitized.length; i += 1) {
      if (sanitized[i] === "(") depth += 1;
      else if (sanitized[i] === ")") {
        depth -= 1;
        if (depth === 0) {
          end = i + 1;
          break;
        }
      }
    }
    assert.notEqual(end, -1, "[Boolean arity] unclosed defrule");
    const rule = sanitized.slice(cursor, end);
    const stack = [];
    let token = "";
    const flushToken = () => {
      if (!token) return;
      const frame = stack.at(-1);
      frame.items += 1;
      if (frame.items === 1) frame.head = token;
      token = "";
    };
    for (const ch of rule) {
      if (ch === "(") {
        flushToken();
        if (stack.length) stack.at(-1).items += 1;
        stack.push({ items: 0, head: null });
      } else if (ch === ")") {
        flushToken();
        const frame = stack.pop();
        const operands = frame.items - 1;
        const expected = logicalArity.get(frame.head);
        if (expected !== undefined) {
          assert.equal(
            operands,
            expected,
            `[Boolean arity] ${frame.head} has ${operands} operands; expected exactly ${expected}`,
          );
        }
      } else if (/\s/.test(ch)) {
        flushToken();
      } else {
        token += ch;
      }
    }
    cursor = end;
  }
}

function renderRule(rule) {
  return String(rule);
}

function countRuleElements(rule) {
  let forms = 0;
  for (const ch of rule) {
    if (ch === "(") forms += 1;
  }
  return forms - 1;
}

function validateEngineLimits(sourceText, rules) {
  const lines = sourceText.split("\n");
  const maxLineLength = Math.max(...lines.map((line) => line.length));
  assert.ok(
    rules.length <= 10000,
    `[Engine limits] controller has ${rules.length} rules; DE limit is 10000`,
  );
  assert.ok(
    maxLineLength <= 255,
    `[Engine limits] controller line reaches ${maxLineLength} characters; DE limit is 255`,
  );

  let worstRule = -1;
  let worstElements = 0;
  for (let index = 0; index < rules.length; index += 1) {
    const elements = countRuleElements(rules[index]);
    if (elements > worstElements) {
      worstElements = elements;
      worstRule = index;
    }
    assert.ok(
      elements <= 32,
      `[Engine limits] rule ${index} has ${elements} elements; DE limit is 32`,
    );
  }

  const badDefconstTimers = [...sourceText.matchAll(
    /\(defconst\s+[^\s)]+timer[^\s)]*\s+(-?\d+)\)/g,
  )]
    .map((match) => Number(match[1]))
    .filter((value) => value < 1 || value > 50);
  assert.equal(
    badDefconstTimers.length,
    0,
    `[Engine limits] numeric timer defconst outside 1..50: ${badDefconstTimers.join(", ")}`,
  );

  const badLiteralTimers = [...stripComments(sourceText).matchAll(
    /\((?:enable-timer|disable-timer|timer-triggered|up-timer-status)\s+(-?\d+)(?:\s|\))/g,
  )]
    .map((match) => Number(match[1]))
    .filter((value) => value < 1 || value > 50);
  assert.equal(
    badLiteralTimers.length,
    0,
    `[Engine limits] numeric timer command outside 1..50: ${badLiteralTimers.join(", ")}`,
  );

  return { maxLineLength, worstRule, worstElements };
}

function validateEngineActionContracts(rules) {
  for (let index = 0; index < rules.length; index += 1) {
    const rule = rules[index];
    for (const match of rule.matchAll(/\((build|train|research)\s+([^\s)]+)\)/g)) {
      const kind = match[1];
      const target = match[2];
      const exact = `(can-${kind} ${target})`;
      const escrow = `(can-${kind}-with-escrow ${target})`;
      assert.ok(
        rule.includes(exact) || rule.includes(escrow),
        `[Action contract] rule ${index} issues ${kind} ${target} without matching ${exact} or ${escrow}`,
      );

      if (kind === "train") {
        assert.ok(
          rule.includes("(unit-type-count-total") ||
            rule.includes("(up-pending-objects"),
          `[Queue witness] train ${target} at rule ${index} lacks a queued/completed count witness`,
        );
      }

      if (kind === "build") {
        assert.ok(
          rule.includes("(building-type-count-total") ||
            rule.includes("(up-pending-objects"),
          `[Foundation witness] build ${target} at rule ${index} lacks a completed/pending building witness`,
        );
      }
    }
  }
}

function validateAttackContracts(rules) {
  const attackRules = rules.filter((rule) => rule.includes("(attack-now)"));
  assert.ok(
    attackRules.length > 0,
    "[Attack contract] no attack-now executor exists",
  );
  for (const [index, rule] of rules.entries()) {
    if (!rule.includes("(attack-now)")) continue;
    assert.ok(
      rule.includes("(timer-triggered bt-attack-timer)"),
      `[Attack contract] attack-now rule ${index} lacks the attack timer trigger`,
    );
    assert.ok(
      rule.includes("(goal attack-goal 0)"),
      `[Attack contract] attack-now rule ${index} lacks attack-goal idle gating`,
    );
    if (rule.includes("(goal strategy-goal bt-strategy-castle-power)")) {
      assert.ok(
        rule.includes("(unit-type-count crossbowman >= bt-standing-crossbow-target-goal)"),
        `[Attack completion] Castle-Power attack rule ${index} lacks actual Crossbow completion witness`,
      );
    }
  }
}

function validateStateCoverage(rules) {
  for (const state of [
    "strategy-goal",
    "unit-goal",
    "bt-resource-mode-goal",
    "attack-goal",
  ]) {
    const writerIndices = rules
      .map((rule, index) =>
        rule.includes(`(set-goal ${state}`) ? index : -1,
      )
      .filter((index) => index >= 0);
    const readerIndices = rules
      .map((rule, index) =>
        rule.includes(`(goal ${state}`) ||
        rule.includes(`(not (goal ${state}`) ? index : -1,
      )
      .filter((index) => index >= 0);
    const actionReaderIndices = rules
      .map((rule, index) =>
        (
          rule.includes(`(goal ${state}`) ||
          rule.includes(`(not (goal ${state}`)
        ) && /\((build|train|research|attack-now)\b/.test(rule)
          ? index
          : -1,
      )
      .filter((index) => index >= 0);

    assert.ok(
      writerIndices.length > 0,
      `[State coverage] no writer exists for ${state}`,
    );
    assert.ok(
      readerIndices.length > 0,
      `[State coverage] no reader exists for ${state}`,
    );
    assert.ok(
      actionReaderIndices.some((index) => index > writerIndices[0]),
      `[State coverage] no engine-action consumer exists downstream of ${state}'s first writer`,
    );
  }
}

function validateHandoffWiring(repoRootPath, legacyPath) {
  assert.ok(
    fs.existsSync(legacyPath),
    "[Harness] legacy lifecycle regression validator is missing",
  );
  const legacySource = fs.readFileSync(legacyPath, "utf8");
  assert.ok(
    !legacySource.includes("ByzTeacher/ByzMetaTeacher.per"),
    "[Harness] legacy validator still defaults to the obsolete ByzTeacher controller path",
  );
  assert.ok(
    legacySource.includes("Basilisk") && legacySource.includes("Basilisk.per"),
    "[Harness] legacy validator does not default to Basilisk/Basilisk.per",
  );
  assert.ok(
    fs.existsSync(path.join(repoRootPath, "validation", "VALIDATOR-HANDOFF.md")),
    "[Harness] validator handoff document is missing",
  );
}

function ruleIndex(rules, ...needles) {
  const index = rules.findIndex((rule) =>
    needles.every((needle) => renderRule(rule).includes(needle)),
  );
  assert.notEqual(index, -1, `[Source order] rule not found: ${needles.join(" | ")}`);
  return index;
}

function requireRule(rules, label, ...needles) {
  ruleIndex(rules, ...needles);
  return label;
}

function validateLineHygiene(text) {
  const lines = text.split("\n");
  const maxLength = Math.max(...lines.map((line) => line.length));
  assert.ok(
    maxLength <= 260,
    `[Hygiene] controller line exceeds 260 characters (max observed: ${maxLength})`,
  );
  assert.ok(
    !/\t/.test(text),
    "[Hygiene] tab characters are not permitted in Basilisk.per",
  );
  return maxLength;
}

function validateSourceOrder(rules) {
  const firstStrategyWriterIndex = ruleIndex(rules, "(set-goal strategy-goal");
  const finalStrategyWriterIndex = Math.max(
    ...rules
      .map((rule, index) =>
        rule.includes("(set-goal strategy-goal") ? index : -1,
      )
      .filter((index) => index >= 0),
  );
  const resourceModeResetIndex = ruleIndex(
    rules,
    "(true)",
    "(set-goal bt-resource-mode-goal 0)",
  );
  const firstProductionIndex = ruleIndex(
    rules,
    "(goal bt-standing-army-demand-goal 1)",
    "(strategic-number sn-resource-control == 0)",
    "(can-build barracks)",
    "(build barracks)",
  );
  const attackIndex = ruleIndex(
    rules,
    "(timer-triggered bt-attack-timer)",
    "(goal attack-goal 0)",
    "(attack-now)",
  );

  for (let index = 0; index < finalStrategyWriterIndex; index += 1) {
    const rule = rules[index];
    if (
      !rule.includes("(goal strategy-goal") &&
      !rule.includes("(not (goal strategy-goal")
    ) {
      continue;
    }
    assert.ok(
      !/(^|\s)\((build|train|research|attack-now)\b/.test(rule),
      `[One-pass latency] strategy reader at rule ${index} before final strategy writer issues an engine action`,
    );
  }

  assert.ok(
    finalStrategyWriterIndex >= firstStrategyWriterIndex,
    "[Source order] final strategy writer must not precede first strategy writer",
  );
  assert.ok(
    finalStrategyWriterIndex < resourceModeResetIndex,
    "[Source order] final strategy writer must precede resource-mode arbitration",
  );
  assert.ok(
    resourceModeResetIndex < firstProductionIndex,
    "[Source order] resource-mode arbitration must precede production",
  );
  assert.ok(
    firstProductionIndex < attackIndex,
    "[Source order] production capability must precede attack delivery",
  );
}

function validateRetryDoctrine(sourceText) {
  const forbidden = [
    "bt-research-barracks-max-retries",
    "bt-stable-research-max-retries",
    "bt-siege-research-max-retries",
    "bt-economic-research-max-retries",
    "bt-research-mining-camp-gold-shaft-mining-retry-goal",
    "bt-research-barracks-pikeman-retry-goal",
    "bt-research-stable-cavalier-retry-goal",
    "bt-research-stable-paladin-retry-goal",
    "bt-research-stable-heavy-camel-retry-goal",
    "bt-research-siege-capped-ram-retry-goal",
    "bt-research-siege-ram-retry-goal",
    "bt-military-siege-workshop-retry-goal",
  ];
  for (const symbol of forbidden) {
    assert.ok(
      !sourceText.includes(symbol),
      `[Retry doctrine] stale terminal-retry symbol remains: ${symbol}`,
    );
  }
  assert.ok(
    sourceText.includes("(defconst bt-research-failure-backoff-seconds 30)"),
    "[Retry doctrine] shared bounded research backoff constant is missing",
  );
}

function validateLifecycleAnchors(sourceText, rules) {
  for (const symbol of [
    "bt-strategy-boom",
    "bt-strategy-rush",
    "bt-strategy-flush",
    "bt-strategy-castle-power",
    "bt-resource-mode-goal",
    "bt-standing-army-demand-goal",
    "bt-attack-timer",
  ]) {
    assert.ok(sourceText.includes(symbol), `[Lifecycle] missing canonical state symbol: ${symbol}`);
  }

  requireRule(
    rules,
    "RUSH -> Castle-power",
    "(goal strategy-goal bt-strategy-rush)",
    "(current-age >= castle-age)",
    "(players-building-count target-player > 0)",
    "(unit-type-count archer-line >= 4)",
    "(set-goal strategy-goal bt-strategy-castle-power)",
  );
  requireRule(
    rules,
    "RUSH -> BOOM fallback",
    "(goal strategy-goal bt-strategy-rush)",
    "(current-age >= castle-age)",
    "(set-goal strategy-goal bt-strategy-boom)",
  );
  requireRule(
    rules,
    "Castle-power expiry",
    "(goal strategy-goal bt-strategy-castle-power)",
    "(current-age >= imperial-age)",
    "(set-goal strategy-goal bt-strategy-boom)",
  );
}

validateBalancedParens(source);
validateBooleanArity(source);
const rules = extractRules(source);
assert.ok(rules.length > 0, "[Parser] no defrule forms found");
const engineLimitReport = validateEngineLimits(source, rules);
validateLineHygiene(source);
validateRetryDoctrine(source);
validateLifecycleAnchors(source, rules);
validateEngineActionContracts(rules);
validateAttackContracts(rules);
validateStateCoverage(rules);
validateSourceOrder(rules);
validateHandoffWiring(repoRoot, legacyValidatorPath);

const legacy = spawnSync(
  process.execPath,
  [legacyValidatorPath, controllerPath],
  {
    stdio: "inherit",
    cwd: repoRoot,
  },
);

assert.equal(
  legacy.status,
  0,
  `[Harness] repair-lifecycle-replay.js failed with exit code ${legacy.status}`,
);

const controllerRelative = path.relative(repoRoot, controllerPath) || controllerPath;
console.log(JSON.stringify({
  status: "PASS",
  entrypoint: "validation/basilisk-validator.js",
  controller: controllerRelative,
  rules: rules.length,
  checks: [
    "balanced parentheses",
    "exact logical-operator arity",
    "DE rule/element/line/timer hard limits",
    "line/tab hygiene",
    "persistent-demand bounded-backoff doctrine",
    "lifecycle anchors",
    "engine-action can-* contracts",
    "queued/completed train witnesses",
    "completed/pending build witnesses",
    "attack-now timer/idle/completion contracts",
    "critical state writer/reader/action coverage",
    "pre-final-strategy one-pass action ban",
    "strategy -> resource-mode -> production -> attack source order",
    "live Thumb Ring resource-mode gate",
    "validator handoff wiring",
    "full repair-lifecycle-replay regression suite",
  ],
  maxControllerLine: engineLimitReport.maxLineLength,
  maxRuleElements: engineLimitReport.worstElements,
  maxRuleIndex: engineLimitReport.worstRule,
}, null, 2));
