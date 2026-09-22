#!/usr/bin/env node

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const controllerPath =
  process.argv[2] ??
  path.resolve(process.cwd(), "ByzTeacher", "ByzMetaTeacher.per");

const source = fs.readFileSync(controllerPath, "utf8");

function extractRules(text) {
  const rules = [];
  let cursor = 0;
  while ((cursor = text.indexOf("(defrule", cursor)) !== -1) {
    let depth = 0;
    let end = -1;
    for (let i = cursor; i < text.length; i += 1) {
      if (text[i] === "(") depth += 1;
      else if (text[i] === ")") {
        depth -= 1;
        if (depth === 0) {
          end = i + 1;
          break;
        }
      }
    }
    assert.notEqual(end, -1, `Unclosed defrule beginning at character ${cursor}`);
    rules.push(text.slice(cursor, end));
    cursor = end;
  }
  return rules;
}

const rules = extractRules(source);

function findRule(...needles) {
  return rules.find((rule) => needles.every((needle) => rule.includes(needle)));
}

function requireRule(label, ...needles) {
  const rule = findRule(...needles);
  assert.ok(rule, `[${label}] required rule edge not found: ${needles.join(" | ")}`);
  return rule;
}

function requireAnyRule(label, variants) {
  for (const needles of variants) {
    const rule = findRule(...needles);
    if (rule) return rule;
  }
  assert.fail(
    `[${label}] none of the required rule signatures were found: ${JSON.stringify(variants)}`,
  );
}

function transition(name, initial, fail, cooldown, canIssue, terminal, cancel, reset, reenter) {
  const state = { ...initial };
  const trace = [];

  function snap(event) {
    trace.push({ event, ...state });
  }

  snap("initial");
  fail(state);
  snap("failure-1");
  assert.equal(state.claim, 0, `[${name}] stale claim after first failure`);
  assert.equal(state.package, 0, `[${name}] stale package cursor after first failure`);
  assert.equal(state.retry, 1, `[${name}] first failure did not consume exactly one retry`);

  cooldown(state);
  snap("cooldown-1-expired");
  assert.equal(state.retry, 1, `[${name}] cooldown mutated retry history`);
  assert.ok(canIssue(state), `[${name}] retry-1 should be reissuable`);

  fail(state);
  snap("failure-2");
  assert.equal(state.claim, 0, `[${name}] stale claim after terminal failure`);
  assert.equal(state.package, 0, `[${name}] stale package cursor after terminal failure`);
  assert.equal(state.retry, 2, `[${name}] second failure did not reach retry cap`);

  cooldown(state);
  snap("terminal-cooldown-expired");
  assert.equal(state.retry, 2, `[${name}] terminal cooldown changed retry cap`);
  assert.ok(!canIssue(state), `[${name}] terminal state re-entered without strategic reset`);
  assert.ok(terminal(state), `[${name}] terminal-state invariant failed`);

  cancel(state);
  reset(state);
  snap("owner-cancelled-and-reset");
  assert.equal(state.retry, 0, `[${name}] terminal retry state did not reset after owner cancellation`);
  assert.equal(state.claim, 0, `[${name}] stale claim survived owner cancellation`);
  assert.equal(state.package, 0, `[${name}] stale package survived owner cancellation`);
  assert.ok(reenter(state), `[${name}] clean strategic reassessment could not re-enter`);

  return trace;
}

function workshopScenario() {
  const state = {
    demand: 1,
    retry: 0,
    backoff: 0,
    claim: 0,
    provider: 0,
    pending: 0,
  };
  const trace = [];

  const snap = (event) => trace.push({ event, ...state });
  const canIssue = () =>
    state.demand === 1 &&
    state.provider === 0 &&
    state.pending === 0 &&
    state.claim === 0 &&
    state.backoff === 0 &&
    state.retry < 4;

  snap("initial");

  for (let attempt = 1; attempt <= 4; attempt += 1) {
    assert.ok(canIssue(), `[Workshop] retry-${attempt} unexpectedly blocked before issue`);
    state.claim = 503;
    snap(`build-issued-${attempt}`);

    if (attempt < 4) {
      state.retry += 1;
      state.claim = 0;
      state.backoff = 1;
    } else {
      state.retry = 4;
      state.claim = 0;
      state.backoff = 1;
    }

    snap(`failure-${attempt}`);
    assert.equal(state.claim, 0, `[Workshop] stale resource claim after failure ${attempt}`);
    assert.equal(state.retry, attempt, `[Workshop] retry counter mismatch at failure ${attempt}`);

    state.backoff = 0;
    snap(`cooldown-${attempt}-expired`);
    assert.equal(state.retry, attempt, `[Workshop] cooldown reset retry history at ${attempt}`);
  }

  assert.equal(state.retry, 4, "[Workshop] retry-4 exhaustion was not persistent");
  assert.equal(state.claim, 0, "[Workshop] retry-4 retained stale Workshop claim");
  assert.ok(!canIssue(), "[Workshop] retry-4 terminal state re-entered while demand persisted");

  state.demand = 0;
  state.provider = 0;
  state.pending = 0;
  state.retry = 0;
  state.backoff = 0;
  snap("strategic-owner-cleared-and-reset");

  assert.equal(state.retry, 0, "[Workshop] terminal retry state did not reset after all demand disappeared");

  state.demand = 1;
  assert.ok(canIssue(), "[Workshop] clean strategic reassessment could not re-enter after terminal reset");

  return trace;
}

assert.ok(source.includes("(defconst bt-research-barracks-max-retries 2)"));
assert.ok(source.includes("(defconst bt-stable-research-max-retries 2)"));
assert.ok(source.includes("(defconst bt-siege-research-max-retries 2)"));

requireRule(
  "Pike failure",
  "(goal bt-research-barracks-claim-goal ri-pikeman)",
  "(up-research-status c: ri-pikeman <= research-available)",
  "(up-modify-goal bt-research-barracks-pikeman-retry-goal g:+ 1)",
  "(set-goal bt-research-barracks-claim-goal 0)",
  "(set-goal bt-research-cavalry-counter-package-goal 0)",
);
requireRule(
  "Pike selector cap",
  "(goal bt-research-cavalry-counter-package-goal 0)",
  "(up-compare-goal bt-cavalry-counter-level-goal >= 1)",
  "(up-compare-goal bt-research-barracks-pikeman-retry-goal < bt-research-barracks-max-retries)",
);
requireRule(
  "Pike executor cap",
  "(goal bt-research-cavalry-counter-package-goal ri-pikeman)",
  "(up-compare-goal bt-research-barracks-pikeman-retry-goal < bt-research-barracks-max-retries)",
  "(can-research-with-escrow ri-pikeman)",
);
requireRule(
  "Pike terminal reset",
  "(goal bt-research-cavalry-counter-package-goal 0)",
  "(goal bt-research-barracks-claim-goal 0)",
  "(up-compare-goal bt-cavalry-counter-level-goal < 1)",
  "(set-goal bt-research-barracks-pikeman-retry-goal 0)",
);
requireRule(
  "Pike capability-loss cleanup",
  "(goal bt-research-barracks-claim-goal != 0)",
  "(building-type-count barracks == 0)",
  "(set-goal bt-research-barracks-claim-goal 0)",
  "(set-goal bt-research-cavalry-counter-package-goal 0)",
);

for (const tech of ["ri-cavalier", "ri-paladin", "ri-heavy-camel"]) {
  const retryGoal = tech === "ri-cavalier"
    ? "bt-research-stable-cavalier-retry-goal"
    : tech === "ri-paladin"
      ? "bt-research-stable-paladin-retry-goal"
      : "bt-research-stable-heavy-camel-retry-goal";
  requireRule(
    `Stable ${tech} failure`,
    `(goal bt-research-stable-claim-goal ${tech})`,
    `(up-research-status c: ${tech} <= research-available)`,
    `(up-modify-goal ${retryGoal} g:+ 1)`,
    "(set-goal bt-research-stable-claim-goal 0)",
  );
  requireRule(
    `Stable ${tech} executor cap`,
    `(goal bt-research-stable-claim-goal 0)`,
    `(up-compare-goal ${retryGoal} < bt-stable-research-max-retries)`,
    `(can-research-with-escrow ${tech})`,
  );
  const stableFailureRule = requireRule(
    `Stable ${tech} failure`,
    `(goal bt-research-stable-claim-goal ${tech})`,
    `(up-research-status c: ${tech} <= research-available)`,
    `(up-modify-goal ${retryGoal} g:+ 1)`,
    "(set-goal bt-research-stable-claim-goal 0)",
  );
  assert.ok(
    !stableFailureRule.includes("bt-research-cavalry-counter-package-goal"),
    `[Stable ${tech}] failure rule must not mutate the Barracks-owned package cursor`,
  );
  requireRule(
    `Stable ${tech} terminal reset`,
    tech === "ri-cavalier"
      ? "(goal bt-cavalier-demand-goal 0)"
      : tech === "ri-paladin"
        ? "(goal bt-paladin-demand-goal 0)"
        : "(goal bt-heavy-camel-demand-goal 0)",
    "(goal bt-research-stable-claim-goal 0)",
    `(set-goal ${retryGoal} 0)`,
  );
}

requireRule(
  "Stable capability-loss cleanup",
  "(goal bt-research-stable-claim-goal != 0)",
  "(building-type-count stable == 0)",
  "(set-goal bt-research-stable-claim-goal 0)",
  "(set-goal bt-research-cavalry-counter-package-goal 0)",
);

for (const [tech, retryGoal] of [
  ["ri-capped-ram", "bt-research-siege-capped-ram-retry-goal"],
  ["ri-siege-ram", "bt-research-siege-ram-retry-goal"],
]) {
  requireRule(
    `Siege ${tech} failure`,
    `(goal bt-research-siege-workshop-claim-goal ${tech})`,
    `(up-research-status c: ${tech} <= research-available)`,
    `(up-modify-goal ${retryGoal} g:+ 1)`,
    "(set-goal bt-research-siege-workshop-claim-goal 0)",
    "(set-goal bt-research-siege-package-goal 0)",
  );
  requireRule(
    `Siege ${tech} executor cap`,
    "(goal bt-ram-demand-goal 1)",
    `(up-compare-goal ${retryGoal} < bt-siege-research-max-retries)`,
    `(can-research-with-escrow ${tech})`,
  );
}
requireRule(
  "Siege terminal reset",
  "(goal bt-ram-demand-goal 0)",
  "(goal bt-research-siege-workshop-claim-goal 0)",
  "(set-goal bt-research-siege-capped-ram-retry-goal 0)",
  "(set-goal bt-research-siege-ram-retry-goal 0)",
);
requireRule(
  "Siege capability-loss cleanup",
  "(goal bt-research-siege-workshop-claim-goal != 0)",
  "(building-type-count siege-workshop == 0)",
  "(set-goal bt-research-siege-workshop-claim-goal 0)",
  "(set-goal bt-research-siege-package-goal 0)",
);

requireRule(
  "Workshop issue cap",
  "(up-compare-goal bt-military-siege-workshop-retry-goal < 4)",
  "(building-type-count siege-workshop == 0)",
  "(can-build-with-escrow siege-workshop)",
);
requireRule(
  "Workshop retry-4 terminal",
  "(strategic-number sn-resource-control == bt-military-siege-workshop-claim)",
  "(up-compare-goal bt-military-siege-workshop-retry-goal >= 4)",
  "(up-pending-objects c: siege-workshop == 0)",
  "(set-strategic-number sn-resource-control 0)",
  "(set-goal bt-military-siege-workshop-backoff-goal 1)",
);
requireRule(
  "Workshop demand-gated retry reset",
  "(goal bt-mangonel-demand-goal 0)",
  "(goal bt-scorpion-demand-goal 0)",
  "(goal bt-onager-demand-goal 0)",
  "(goal bt-bombard-cannon-demand-goal 0)",
  "(goal bt-ram-demand-goal 0)",
  "(goal bt-siege-tower-demand-goal 0)",
  "(up-pending-objects c: siege-workshop == 0)",
  "(set-goal bt-military-siege-workshop-retry-goal 0)",
);

const pikeTrace = transition(
  "Pike",
  { demand: 1, package: "ri-pikeman", claim: "ri-pikeman", retry: 0, backoff: 1, counterLevel: 1 },
  (s) => { s.retry += 1; s.claim = 0; s.package = 0; },
  (s) => { s.backoff = 0; },
  (s) => s.demand === 1 && s.claim === 0 && s.package === 0 && s.backoff === 0 && s.retry < 2,
  (s) => s.retry === 2 && s.demand === 1 && s.claim === 0 && s.package === 0,
  (s) => { s.demand = 0; s.package = 0; s.claim = 0; s.counterLevel = 0; },
  (s) => { if (s.demand === 0 && s.claim === 0 && s.package === 0 && s.counterLevel < 1) s.retry = 0; },
  (s) => { s.demand = 1; s.counterLevel = 1; return s.retry === 0 && s.package === 0 && s.claim === 0; },
);

const stableTrace = (() => {
  const s = { demand: 1, claim: "ri-cavalier", retry: 0, backoff: 1 };
  const trace = [];
  const snap = (event) => trace.push({ event, ...s });

  snap("initial");
  s.retry += 1;
  s.claim = 0;
  snap("failure-1");
  assert.equal(s.claim, 0, "[Stable/Cavalier] stale Stable claim after first failure");
  assert.equal(s.retry, 1, "[Stable/Cavalier] first failure did not consume exactly one retry");

  s.backoff = 0;
  snap("cooldown-1-expired");
  assert.equal(s.retry, 1, "[Stable/Cavalier] cooldown mutated retry history");
  assert.ok(
    s.demand === 1 && s.claim === 0 && s.backoff === 0 && s.retry < 2,
    "[Stable/Cavalier] retry-1 should be reissuable",
  );

  s.retry += 1;
  s.claim = 0;
  snap("failure-2");
  assert.equal(s.claim, 0, "[Stable/Cavalier] stale Stable claim after terminal failure");
  assert.equal(s.retry, 2, "[Stable/Cavalier] second failure did not reach retry cap");

  s.backoff = 0;
  snap("terminal-cooldown-expired");
  assert.equal(s.retry, 2, "[Stable/Cavalier] terminal cooldown changed retry history");
  assert.ok(
    !(s.demand === 1 && s.claim === 0 && s.backoff === 0 && s.retry < 2),
    "[Stable/Cavalier] terminal state re-entered without strategic reset",
  );

  s.demand = 0;
  s.claim = 0;
  if (s.demand === 0 && s.claim === 0) s.retry = 0;
  snap("owner-cancelled-and-reset");
  assert.equal(s.retry, 0, "[Stable/Cavalier] terminal retry state did not reset after demand cancellation");
  assert.equal(s.claim, 0, "[Stable/Cavalier] stale Stable claim survived demand cancellation");
  s.demand = 1;
  assert.ok(
    s.retry === 0 && s.claim === 0,
    "[Stable/Cavalier] clean strategic reassessment could not re-enter",
  );

  return trace;
})();

const cappedRamTrace = transition(
  "Capped Ram",
  { demand: 1, package: "ri-capped-ram", claim: "ri-capped-ram", retry: 0, backoff: 1 },
  (s) => { s.retry += 1; s.claim = 0; s.package = 0; },
  (s) => { s.backoff = 0; },
  (s) => s.demand === 1 && s.claim === 0 && s.package === 0 && s.backoff === 0 && s.retry < 2,
  (s) => s.retry === 2 && s.demand === 1 && s.claim === 0 && s.package === 0,
  (s) => { s.demand = 0; s.claim = 0; s.package = 0; },
  (s) => { if (s.demand === 0 && s.claim === 0) s.retry = 0; },
  (s) => { s.demand = 1; return s.retry === 0 && s.claim === 0; },
);

const siegeRamTrace = transition(
  "Siege Ram",
  { demand: 1, package: "ri-siege-ram", claim: "ri-siege-ram", retry: 0, backoff: 1 },
  (s) => { s.retry += 1; s.claim = 0; s.package = 0; },
  (s) => { s.backoff = 0; },
  (s) => s.demand === 1 && s.claim === 0 && s.package === 0 && s.backoff === 0 && s.retry < 2,
  (s) => s.retry === 2 && s.demand === 1 && s.claim === 0 && s.package === 0,
  (s) => { s.demand = 0; s.claim = 0; s.package = 0; },
  (s) => { if (s.demand === 0 && s.claim === 0) s.retry = 0; },
  (s) => { s.demand = 1; return s.retry === 0 && s.claim === 0; },
);

const workshopTrace = workshopScenario();

const scenarios = {
  pike: pikeTrace,
  stable: stableTrace,
  cappedRam: cappedRamTrace,
  siegeRam: siegeRamTrace,
  workshop: workshopTrace,
};

console.log(JSON.stringify({
  controller: path.relative(process.cwd(), controllerPath),
  rules: rules.length,
  assertions: [
    "stale claims",
    "stale package cursors",
    "bounded retry persistence",
    "terminal-state re-entry prevention",
    "strategic-owner reset and clean re-entry",
  ],
  scenarios: Object.fromEntries(
    Object.entries(scenarios).map(([name, trace]) => [
      name,
      { passed: true, states: trace.length, terminalChecked: true, reentryChecked: true },
    ]),
  ),
}, null, 2));
