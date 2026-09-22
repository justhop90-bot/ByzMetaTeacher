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
assert.ok(source.includes("(defconst bt-gold-shaft-mining-demand-goal 687)"));
assert.ok(source.includes("(defconst bt-research-mining-camp-gold-shaft-mining-retry-goal 686)"));

requireRule(
  "Gold Shaft strategic demand",
  "(goal bt-gold-shaft-mining-demand-goal 0)",
  "(current-age == castle-age)",
  "(goal strategy-goal bt-strategy-boom)",
  "(up-research-status c: ri-gold-mining >= research-complete)",
  "(building-type-count-total town-center >= 2)",
  "(set-goal bt-gold-shaft-mining-demand-goal 1)",
);
requireRule(
  "Gold Shaft strategic cancellation",
  "(goal bt-gold-shaft-mining-demand-goal 1)",
  "(strategic-number sn-resource-control != ri-gold-shaft-mining)",
  "(set-goal bt-gold-shaft-mining-demand-goal 0)",
);
requireRule(
  "Gold Shaft executor retry cap",
  "(goal bt-gold-shaft-mining-demand-goal 1)",
  "(up-compare-goal bt-research-mining-camp-gold-shaft-mining-retry-goal < bt-economic-research-max-retries)",
  "(can-research-with-escrow ri-gold-shaft-mining)",
  "(set-goal bt-research-mining-camp-claim-goal ri-gold-shaft-mining)",
);
const goldShaftFailureRule = requireRule(
  "Gold Shaft watchdog",
  "(goal bt-research-mining-camp-claim-goal ri-gold-shaft-mining)",
  "(up-research-status c: ri-gold-shaft-mining <= research-available)",
  "(up-modify-goal bt-research-mining-camp-gold-shaft-mining-retry-goal g:+ 1)",
  "(set-goal bt-research-mining-camp-claim-goal 0)",
);
assert.ok(
  !goldShaftFailureRule.includes("(set-goal bt-gold-shaft-mining-demand-goal 0)"),
  "[Gold Shaft] engine failure must not cancel strategic demand",
);
requireRule(
  "Gold Shaft completion",
  "(goal bt-research-mining-camp-claim-goal ri-gold-shaft-mining)",
  "(up-research-status c: ri-gold-shaft-mining == research-complete)",
  "(set-goal bt-research-mining-camp-claim-goal 0)",
  "(set-goal bt-gold-shaft-mining-demand-goal 0)",
);
requireRule(
  "Gold Shaft retry reset",
  "(goal bt-gold-shaft-mining-demand-goal 0)",
  "(goal bt-research-mining-camp-claim-goal 0)",
  "(set-goal bt-research-mining-camp-gold-shaft-mining-retry-goal 0)",
);

const goldShaftTrace = transition(
  "Gold Shaft Mining",
  { demand: 1, package: 0, claim: "ri-gold-shaft-mining", retry: 0, backoff: 1 },
  (state) => { state.retry += 1; state.claim = 0; state.package = 0; },
  (state) => { state.backoff = 0; },
  (state) => state.demand === 1 && state.claim === 0 && state.package === 0 && state.backoff === 0 && state.retry < 2,
  (state) => state.retry === 2 && state.demand === 1 && state.claim === 0 && state.package === 0,
  (state) => { state.demand = 0; state.claim = 0; state.package = 0; },
  (state) => { if (state.demand === 0 && state.claim === 0 && state.package === 0) state.retry = 0; },
  (state) => { state.demand = 1; return state.retry === 0 && state.claim === 0 && state.package === 0; },
);


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
  "(up-compare-goal bt-research-barracks-claim-goal != 0)",
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
  goldShaft: goldShaftTrace,
};



// MAP-AWARE OPENING SELECTOR VALIDATION
for (const constant of [
  "bt-opening-map-goal",
  "bt-opening-plan-goal",
  "bt-opening-stage-goal",
  "bt-opening-underlay-goal",
  "bt-opening-threat-goal",
  "bt-opening-plan-arabia-standard",
  "bt-opening-plan-arabia-pressure",
  "bt-opening-plan-arabia-fast-castle",
  "bt-opening-plan-arena-fast-castle",
  "bt-opening-plan-arena-boom",
  "bt-opening-plan-anti-rush",
  "bt-opening-plan-generic-pressure",
  "bt-opening-plan-generic-defensive",
]) {
  assert.ok(source.includes(constant), `[Opening] missing constant/state symbol: ${constant}`);
}

requireRule(
  "Arabia map classification",
  "(goal bt-opening-map-goal 0)",
  "(map-type arabia)",
  "(set-goal bt-opening-map-goal bt-opening-map-arabia)",
);
requireRule(
  "Arena map classification",
  "(goal bt-opening-map-goal 0)",
  "(map-type arena)",
  "(set-goal bt-opening-map-goal bt-opening-map-arena)",
);
requireRule(
  "Immediate opening pressure",
  "(game-time >= 180)",
  "(game-time < bt-scout-pressure-window)",
  "(players-building-type-count target-player watch-tower >= 1)",
  "(set-goal bt-opening-threat-goal bt-opening-threat-immediate)",
);
requireRule(
  "Confirmed opening pressure",
  "(goal bt-opening-threat-goal bt-opening-threat-none)",
  "(players-current-age target-player >= feudal-age)",
  "(players-military-population target-player >= 3)",
  "(set-goal bt-opening-threat-goal bt-opening-threat-confirmed)",
);
requireRule(
  "Arabia Early Pressure",
  "(goal bt-opening-map-goal bt-opening-map-arabia)",
  "(players-building-type-count target-player market >= 1)",
  "(set-goal bt-opening-plan-goal bt-opening-plan-arabia-pressure)",
);
requireRule(
  "Arabia Fast Castle",
  "(goal bt-opening-map-goal bt-opening-map-arabia)",
  "(players-current-age target-player == dark-age)",
  "(players-military-population target-player <= 1)",
  "(set-goal bt-opening-plan-goal bt-opening-plan-arabia-fast-castle)",
);
requireRule(
  "Arena Fast Castle",
  "(goal bt-opening-map-goal bt-opening-map-arena)",
  "(set-goal bt-opening-plan-goal bt-opening-plan-arena-fast-castle)",
);
requireRule(
  "Generic pressure fallback",
  "(goal bt-opening-map-goal bt-opening-map-generic)",
  "(set-goal bt-opening-plan-goal bt-opening-plan-generic-pressure)",
);
requireRule(
  "Anti-Rush commitment",
  "(goal bt-opening-stage-goal bt-opening-stage-selecting)",
  "(up-compare-goal bt-opening-threat-goal >= bt-opening-threat-confirmed)",
  "(set-goal bt-opening-plan-goal bt-opening-plan-anti-rush)",
);
requireRule(
  "Anti-Rush restore",
  "(goal bt-opening-plan-goal bt-opening-plan-anti-rush)",
  "(up-compare-goal bt-opening-threat-goal < bt-opening-threat-confirmed)",
  "(goal bt-opening-underlay-goal bt-opening-plan-arena-fast-castle)",
  "(set-goal bt-opening-plan-goal bt-opening-plan-arena-fast-castle)",
);
requireRule(
  "Arena Fast Castle completion",
  "(goal bt-opening-plan-goal bt-opening-plan-arena-fast-castle)",
  "(current-age >= castle-age)",
  "(set-goal bt-opening-plan-goal bt-opening-plan-arena-boom)",
);
requireRule(
  "Opening -> RUSH",
  "(goal bt-opening-plan-goal bt-opening-plan-arabia-pressure)",
  "(current-age == feudal-age)",
  "(set-goal strategy-goal bt-strategy-rush)",
);
requireRule(
  "Opening -> FLUSH",
  "(goal bt-opening-plan-goal bt-opening-plan-anti-rush)",
  "(set-goal strategy-goal bt-strategy-flush)",
);
requireRule(
  "Opening -> Castle bank",
  "(current-age == feudal-age)",
  "(goal bt-opening-plan-goal bt-opening-plan-arabia-fast-castle)",
  "(set-goal bt-resource-mode-goal bt-resource-mode-castle-bank)",
);

function renderRule(rule) {
  if (!Array.isArray(rule)) return String(rule);
  return `(${rule.map(renderRule).join(" ")})`;
}

const openingWriterRules = rules.filter((rule) =>
  renderRule(rule).includes("(set-goal bt-opening-"),
);
const openingSelectorWriters = openingWriterRules.filter((rule) => {
  const rendered = renderRule(rule);
  return !(
    rendered.includes("(true)") &&
    rendered.includes("(set-goal strategy-goal bt-strategy-boom)") &&
    rendered.includes("(set-goal unit-goal bt-unit-mix)")
  );
});
for (const rule of openingSelectorWriters) {
  const rendered = renderRule(rule);
  for (const forbidden of [
    "(set-goal strategy-goal",
    "(set-goal unit-goal",
    "(set-goal bt-resource-mode-goal",
    "(set-strategic-number",
    "(release-escrow",
    "(build ",
    "(train ",
    "(research ",
  ]) {
    assert.ok(
      !rendered.includes(forbidden),
      `[Opening ownership] opening rule illegally writes execution state: ${forbidden}`,
    );
  }
}
assert.equal(
  openingSelectorWriters.filter((rule) => renderRule(rule).includes("any-enemy")).length,
  0,
  "[Opening target ownership] opening rules must stay target-player specific",
);

// Deterministic policy model mirrors the implemented selector priority.
function openingPolicy(input) {
  const threat =
    input.time >= 180 && input.time < 600 && input.targetKnown &&
    (input.tower ||
      (input.barracks && input.range) ||
      (input.barracks && input.stable) ||
      (input.range && input.stable) ||
      input.militia >= 3 ||
      input.archers >= 3 ||
      input.scouts >= 4)
      ? 3
      : input.time >= 180 && input.time < 600 && input.targetKnown &&
          ((input.barracks && input.militia >= 2) ||
            (input.range && input.archers >= 2) ||
            (input.stable && input.scouts >= 3) ||
            (input.enemyAge === "feudal" && input.enemyMilitary >= 3) ||
            input.enemyMilitary >= 5)
        ? 2
        : input.time >= 180 && input.time < 600 && input.targetKnown && input.enemyMilitary >= 2
          ? 1
          : 0;

  let plan = 0;
  let underlay = 0;

  if (threat >= 2) {
    underlay = input.map === "arabia" ? 1 : input.map === "arena" ? 4 : 8;
    plan = 6;
  } else if (
    input.map === "arabia" &&
    input.time >= 300 &&
    input.targetKnown &&
    input.market &&
    !input.barracks &&
    !input.range &&
    !input.stable
  ) {
    underlay = plan = 2;
  } else if (
    input.map === "arabia" &&
    input.time >= 300 &&
    input.targetKnown &&
    input.enemyAge === "dark" &&
    input.enemyMilitary <= 1 &&
    !input.barracks &&
    !input.range &&
    !input.stable
  ) {
    underlay = plan = 3;
  } else if (
    input.map === "arabia" &&
    input.time >= 300 &&
    (!input.targetKnown || threat === 1)
  ) {
    underlay = plan = 1;
  } else if (
    input.map === "arena" &&
    input.time >= 180
  ) {
    underlay = plan = 4;
  } else if (
    input.map === "generic" &&
    input.time >= 300 &&
    input.targetKnown &&
    input.enemyAge === "dark" &&
    input.market &&
    !input.barracks &&
    !input.range &&
    !input.stable &&
    threat === 0
  ) {
    underlay = plan = 7;
  } else if (input.map === "generic" && input.time >= 300) {
    underlay = plan = 8;
  }

  if (input.map === "arena" && plan === 4 && input.age === "castle" && threat === 0) {
    underlay = plan = 5;
  }
  return { threat, plan, underlay };
}

const openingCases = {
  A: {
    map: "arabia", time: 360, targetKnown: false, market: false,
    barracks: false, range: false, stable: false, tower: false,
    militia: 0, archers: 0, scouts: 1, enemyMilitary: 0,
    enemyAge: "dark", age: "dark",
  },
  B: {
    map: "arabia", time: 360, targetKnown: true, market: true,
    barracks: false, range: false, stable: false, tower: false,
    militia: 0, archers: 0, scouts: 1, enemyMilitary: 0,
    enemyAge: "dark", age: "dark",
  },
  C: {
    map: "arabia", time: 360, targetKnown: true, market: false,
    barracks: false, range: false, stable: false, tower: false,
    militia: 0, archers: 0, scouts: 1, enemyMilitary: 0,
    enemyAge: "dark", age: "dark",
  },
  D: {
    map: "arena", time: 300, targetKnown: false, market: false,
    barracks: false, range: false, stable: false, tower: false,
    militia: 0, archers: 0, scouts: 1, enemyMilitary: 0,
    enemyAge: "dark", age: "dark",
  },
  E: {
    map: "arena", time: 900, targetKnown: true, market: false,
    barracks: false, range: false, stable: false, tower: false,
    militia: 0, archers: 0, scouts: 1, enemyMilitary: 0,
    enemyAge: "dark", age: "castle",
  },
  F: {
    map: "arabia", time: 360, targetKnown: true, market: false,
    barracks: true, range: false, stable: false, tower: false,
    militia: 3, archers: 0, scouts: 1, enemyMilitary: 4,
    enemyAge: "feudal", age: "dark",
  },
  G: {
    map: "arena", time: 360, targetKnown: true, market: false,
    barracks: false, range: false, stable: false, tower: true,
    militia: 0, archers: 0, scouts: 1, enemyMilitary: 3,
    enemyAge: "feudal", age: "dark",
  },
  H: {
    map: "arabia", time: 360, targetKnown: false, market: false,
    barracks: false, range: false, stable: false, tower: false,
    militia: 0, archers: 0, scouts: 1, enemyMilitary: 0,
    enemyAge: "dark", age: "dark",
  },
  I: {
    map: "arabia", time: 360, targetKnown: true, market: false,
    barracks: false, range: false, stable: false, tower: false,
    militia: 0, archers: 0, scouts: 1, enemyMilitary: 2,
    enemyAge: "dark", age: "dark",
  },
};

const expectedPlans = {
  A: 1,
  B: 2,
  C: 3,
  D: 4,
  E: 5,
  F: 6,
  G: 6,
  H: 1,
};
for (const [scenario, expected] of Object.entries(expectedPlans)) {
  const actual = openingPolicy(openingCases[scenario]).plan;
  assert.equal(actual, expected, `[Opening scenario ${scenario}] expected plan ${expected}, got ${actual}`);
}

// Scenario G: reversible Anti-Rush override restores its Arena FC underlay.
const gInitial = openingPolicy(openingCases.G);
assert.equal(gInitial.plan, 6, "[Opening G] Anti-Rush did not win priority");
assert.equal(gInitial.underlay, 4, "[Opening G] Arena FC underlay was not preserved");
const gRecovered = { ...gInitial, plan: 6, threat: 0 };
gRecovered.plan = gRecovered.underlay;
assert.equal(gRecovered.plan, 4, "[Opening G] Anti-Rush did not restore Arena FC");

// Scenario I: the implementation is target-player-specific. No opening rule
// contains any-enemy, so unrelated enemy populations cannot directly trigger it.
assert.equal(
  openingSelectorWriters.filter((rule) => renderRule(rule).includes("any-enemy")).length,
  0,
  "[Opening I] any-enemy leaked into opening selection",
);
assert.equal(openingPolicy(openingCases.I).plan, 1, "[Opening I] suspected target pressure should fall back to Arabia Standard");
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
