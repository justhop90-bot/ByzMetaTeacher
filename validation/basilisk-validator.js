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
        if (frame.head === "or" || frame.head === "and") {
          assert.ok(
            operands <= 2,
            `[Boolean arity] ${frame.head} has ${operands} operands; expected nested binary form`,
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

  for (let index = 0; index < firstStrategyWriterIndex; index += 1) {
    const rule = rules[index];
    if (
      !rule.includes("(goal strategy-goal") &&
      !rule.includes("(not (goal strategy-goal")
    ) {
      continue;
    }
    assert.ok(
      !/(^|\s)\((build|train|research|attack-now)\b/.test(rule),
      `[One-pass latency] pre-strategy reader at rule ${index} issues an engine action`,
    );
  }

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

  const thumbRingExecutor = rules.find((rule) =>
    rule.includes("(goal bt-research-ranged-counter-package-goal ri-thumb-ring)") &&
    rule.includes("(research ri-thumb-ring)"),
  );
  assert.ok(
    thumbRingExecutor &&
      thumbRingExecutor.includes("(goal bt-resource-mode-goal bt-resource-mode-castle-boom)") &&
      thumbRingExecutor.includes("(goal bt-resource-mode-goal bt-resource-mode-premium-gold)"),
    "[Live gate] Thumb Ring executor must re-check its allowed live resource modes",
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
validateLineHygiene(source);
validateRetryDoctrine(source);
validateLifecycleAnchors(source, rules);
validateSourceOrder(rules);

assert.ok(
  fs.existsSync(legacyValidatorPath),
  "[Harness] legacy lifecycle regression validator is missing",
);

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
    "nested binary boolean arity",
    "line/tab hygiene",
    "persistent-demand bounded-backoff doctrine",
    "lifecycle anchors",
    "pre-strategy one-pass action ban",
    "strategy -> resource-mode -> production -> attack source order",
    "live Thumb Ring resource-mode gate",
    "full repair-lifecycle-replay regression suite",
  ],
}, null, 2));
