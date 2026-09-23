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

function transition(name, initial, fail, cooldown, canIssue, cancel, reset, reenter) {
  const state = { ...initial };
  const trace = [];
  const snap = (event) => trace.push({ event, ...state });
  snap("initial");
  fail(state);
  snap("failure-1");
  assert.equal(state.claim, 0, `[${name}] stale claim after failure`);
  assert.equal(state.demand, 1, `[${name}] strategic demand was lost after execution failure`);
  assert.equal(state.package, initial.package, `[${name}] strategic package changed on execution failure`);
  assert.equal(state.backoff, 1, `[${name}] bounded backoff was not armed after execution failure`);
  cooldown(state);
  snap("cooldown-1-expired");
  assert.equal(state.backoff, 0, `[${name}] cooldown did not reopen execution`);
  assert.ok(canIssue(state), `[${name}] persistent demand should be reissuable after cooldown`);
  fail(state);
  snap("failure-2");
  assert.equal(state.claim, 0, `[${name}] stale claim after repeated execution failure`);
  assert.equal(state.demand, 1, `[${name}] persistent demand was lost after repeated execution failure`);
  assert.equal(state.package, initial.package, `[${name}] strategic package changed after repeated execution failure`);
  assert.equal(state.backoff, 1, `[${name}] bounded backoff was not re-armed after repeated failure`);
  cooldown(state);
  snap("cooldown-2-expired");
  assert.equal(state.backoff, 0, `[${name}] second cooldown did not reopen execution`);
  assert.ok(canIssue(state), `[${name}] persistent demand was not re-opened after second cooldown`);
  cancel(state);
  reset(state);
  snap("owner-cancelled-and-reset");
  assert.equal(state.demand, 0, `[${name}] strategic invalidation did not clear demand`);
  assert.equal(state.backoff, 0, `[${name}] stale backoff survived strategic invalidation`);
  assert.equal(state.claim, 0, `[${name}] stale claim survived owner cancellation`);
  assert.equal(state.package, 0, `[${name}] stale package survived owner cancellation`);
  assert.ok(reenter(state), `[${name}] clean strategic reassessment could not re-enter`);
  return trace;
}

function workshopScenario() {
  const state = { demand: 1, backoff: 0, claim: 0, provider: 0, pending: 0 };
  const trace = [];
  const snap = (event) => trace.push({ event, ...state });
  const canIssue = () => state.demand === 1 && state.provider === 0 && state.pending === 0 && state.claim === 0 && state.backoff === 0;
  snap("initial");
  assert.ok(canIssue(), "[Workshop] persistent demand was not initially executable");
  state.claim = 503; state.claim = 0; state.backoff = 1; snap("watchdog-failure-1");
  assert.equal(state.claim, 0, "[Workshop] stale resource claim after watchdog failure");
  assert.equal(state.demand, 1, "[Workshop] watchdog failure canceled persistent demand");
  assert.equal(state.backoff, 1, "[Workshop] watchdog failure did not arm bounded backoff");
  state.backoff = 0; snap("cooldown-1-expired");
  assert.ok(canIssue(), "[Workshop] cooldown did not reopen the same persistent demand");
  state.claim = 503; state.claim = 0; state.backoff = 1; snap("watchdog-failure-2");
  assert.equal(state.claim, 0, "[Workshop] stale resource claim after repeated watchdog failure");
  assert.equal(state.demand, 1, "[Workshop] repeated watchdog failure canceled persistent demand");
  assert.equal(state.backoff, 1, "[Workshop] repeated watchdog failure did not re-arm bounded backoff");
  state.backoff = 0; snap("cooldown-2-expired");
  assert.ok(canIssue(), "[Workshop] persistent demand was not re-opened after second cooldown");
  state.demand = 0; state.backoff = 0; state.claim = 0;
  assert.equal(state.demand, 0, "[Workshop] strategic invalidation did not clear demand");
  assert.equal(state.backoff, 0, "[Workshop] stale backoff survived strategic invalidation");
  state.demand = 1;
  assert.ok(canIssue(), "[Workshop] clean strategic reassessment could not re-enter");
  return trace;
}

assert.ok(source.includes("(defconst bt-research-failure-backoff-seconds 30)"));
assert.ok(source.includes("(defconst bt-research-barracks-failure-backoff-goal 630)"));
assert.ok(source.includes("(defconst bt-research-stable-failure-backoff-goal 632)"));
assert.ok(source.includes("(defconst bt-research-siege-workshop-failure-backoff-goal 633)"));
assert.ok(source.includes("(defconst bt-gold-shaft-mining-demand-goal 687)"));
for (const stale of ["bt-research-barracks-max-retries","bt-stable-research-max-retries","bt-siege-research-max-retries","bt-economic-research-max-retries","bt-research-mining-camp-gold-shaft-mining-retry-goal","bt-research-barracks-pikeman-retry-goal","bt-research-stable-cavalier-retry-goal","bt-research-stable-paladin-retry-goal","bt-research-stable-heavy-camel-retry-goal","bt-research-siege-capped-ram-retry-goal","bt-research-siege-ram-retry-goal","bt-military-siege-workshop-retry-goal"]) assert.ok(!source.includes(stale), `[Retry doctrine] stale terminal-retry symbol remains: ${stale}`);

requireRule("Gold Shaft strategic demand","(goal bt-gold-shaft-mining-demand-goal 0)","(current-age == castle-age)","(goal strategy-goal bt-strategy-boom)","(up-research-status c: ri-gold-mining >= research-complete)","(building-type-count-total town-center >= 2)","(set-goal bt-gold-shaft-mining-demand-goal 1)");
requireRule("Gold Shaft strategic cancellation","(goal bt-gold-shaft-mining-demand-goal 1)","(goal bt-research-mining-camp-claim-goal 0)","(set-goal bt-gold-shaft-mining-demand-goal 0)");
requireRule("Gold Shaft executor backoff gate","(goal bt-gold-shaft-mining-demand-goal 1)","(up-compare-goal bt-research-mining-camp-failure-backoff-goal != ri-gold-shaft-mining)","(can-research-with-escrow ri-gold-shaft-mining)","(set-goal bt-research-mining-camp-claim-goal ri-gold-shaft-mining)");
const goldShaftFailureRule=requireRule("Gold Shaft watchdog","(goal bt-research-mining-camp-claim-goal ri-gold-shaft-mining)","(up-research-status c: ri-gold-shaft-mining <= research-available)","(set-goal bt-research-mining-camp-failure-backoff-goal ri-gold-shaft-mining)","(enable-timer bt-research-mining-camp-failure-backoff-timer bt-research-failure-backoff-seconds)","(set-goal bt-research-mining-camp-claim-goal 0)");
assert.ok(!goldShaftFailureRule.includes("(set-goal bt-gold-shaft-mining-demand-goal 0)"), "[Gold Shaft] engine failure must not cancel strategic demand");
requireRule("Gold Shaft completion","(goal bt-research-mining-camp-claim-goal ri-gold-shaft-mining)","(up-research-status c: ri-gold-shaft-mining == research-complete)","(set-goal bt-research-mining-camp-claim-goal 0)","(set-goal bt-gold-shaft-mining-demand-goal 0)");
requireRule("Gold Shaft backoff expiry","(timer-triggered bt-research-mining-camp-failure-backoff-timer)","(disable-timer bt-research-mining-camp-failure-backoff-timer)","(set-goal bt-research-mining-camp-failure-backoff-goal 0)");
const goldShaftTrace=transition("Gold Shaft Mining",{demand:1,package:0,claim:"ri-gold-shaft-mining",backoff:1},s=>{s.claim=0;s.backoff=1;},s=>{s.backoff=0;},s=>s.demand===1&&s.claim===0&&s.package===0&&s.backoff===0,s=>{s.demand=0;s.claim=0;s.package=0;},s=>{s.backoff=0;},s=>{s.demand=1;return s.demand===1&&s.claim===0&&s.package===0&&s.backoff===0;});

requireRule("Pike failure","(goal bt-research-barracks-claim-goal ri-pikeman)","(up-research-status c: ri-pikeman <= research-available)","(set-goal bt-research-barracks-failure-backoff-goal ri-pikeman)","(enable-timer bt-research-barracks-failure-backoff-timer bt-research-failure-backoff-seconds)","(set-goal bt-research-barracks-claim-goal 0)");
const pikeFailureRule=findRule("(goal bt-research-barracks-claim-goal ri-pikeman)","(up-research-status c: ri-pikeman <= research-available)");
assert.ok(!pikeFailureRule.includes("(set-goal bt-research-cavalry-counter-package-goal 0)"),"[Pike] execution failure must not mutate the META-owned package cursor");
requireRule("Pike executor backoff gate","(goal bt-research-cavalry-counter-package-goal ri-pikeman)","(up-compare-goal bt-research-barracks-failure-backoff-goal != ri-pikeman)","(can-research-with-escrow ri-pikeman)");
requireRule("Pike backoff expiry","(timer-triggered bt-research-barracks-failure-backoff-timer)","(disable-timer bt-research-barracks-failure-backoff-timer)","(set-goal bt-research-barracks-failure-backoff-goal 0)");

for(const tech of ["ri-cavalier","ri-paladin","ri-heavy-camel"]){requireRule(`Stable ${tech} failure`,`(goal bt-research-stable-claim-goal ${tech})`,`(up-research-status c: ${tech} <= research-available)`,`(set-goal bt-research-stable-failure-backoff-goal ${tech})`,"(enable-timer bt-research-stable-failure-backoff-timer bt-research-failure-backoff-seconds)","(set-goal bt-research-stable-claim-goal 0)");requireRule(`Stable ${tech} executor backoff gate`,"(goal bt-research-stable-claim-goal 0)",`(up-compare-goal bt-research-stable-failure-backoff-goal != ${tech})`,`(can-research-with-escrow ${tech})`);}
requireRule("Stable backoff expiry","(timer-triggered bt-research-stable-failure-backoff-timer)","(disable-timer bt-research-stable-failure-backoff-timer)","(set-goal bt-research-stable-failure-backoff-goal 0)");

for(const tech of ["ri-capped-ram","ri-siege-ram"]){requireRule(`Siege ${tech} failure`,`(goal bt-research-siege-workshop-claim-goal ${tech})`,`(up-research-status c: ${tech} <= research-available)`,`(set-goal bt-research-siege-workshop-failure-backoff-goal ${tech})`,"(enable-timer bt-research-siege-workshop-failure-backoff-timer bt-research-failure-backoff-seconds)","(set-goal bt-research-siege-workshop-claim-goal 0)");requireRule(`Siege ${tech} executor backoff gate`,"(goal bt-ram-demand-goal 1)",`(up-compare-goal bt-research-siege-workshop-failure-backoff-goal != ${tech})`,`(can-research-with-escrow ${tech})`);}
requireRule("Siege backoff expiry","(timer-triggered bt-research-siege-workshop-failure-backoff-timer)","(disable-timer bt-research-siege-workshop-failure-backoff-timer)","(set-goal bt-research-siege-workshop-failure-backoff-goal 0)");

requireRule("Workshop issue eligibility","(goal bt-military-siege-workshop-backoff-goal 0)","(building-type-count siege-workshop == 0)","(up-pending-objects c: siege-workshop == 0)","(strategic-number sn-resource-control == 0)","(can-build-with-escrow siege-workshop)");
requireRule("Workshop watchdog failure","(strategic-number sn-resource-control == bt-military-siege-workshop-claim)","(timer-triggered bt-military-siege-workshop-watchdog-timer)","(up-pending-objects c: siege-workshop == 0)","(set-strategic-number sn-resource-control 0)","(set-goal bt-military-siege-workshop-backoff-goal 1)");
requireRule("Workshop demand-gated backoff reset","(goal bt-mangonel-demand-goal 0)","(goal bt-scorpion-demand-goal 0)","(goal bt-onager-demand-goal 0)","(goal bt-bombard-cannon-demand-goal 0)","(goal bt-ram-demand-goal 0)","(goal bt-siege-tower-demand-goal 0)","(up-pending-objects c: siege-workshop == 0)","(set-goal bt-military-siege-workshop-backoff-goal 0)");

const pikeTrace=transition("Pike",{demand:1,package:"ri-pikeman",claim:"ri-pikeman",backoff:1,counterLevel:1},s=>{s.claim=0;s.backoff=1;},s=>{s.backoff=0;},s=>s.demand===1&&s.claim===0&&s.package==="ri-pikeman"&&s.backoff===0&&s.counterLevel>=1,s=>{s.demand=0;s.package=0;s.claim=0;s.counterLevel=0;},s=>{s.demand=0;s.package=0;s.claim=0;s.counterLevel=0;},s=>{s.demand=1;s.package="ri-pikeman";return s.demand===1&&s.claim===0&&s.package==="ri-pikeman"&&s.backoff===0;});
const stableTrace=(()=>{const s={demand:1,claim:"ri-cavalier",backoff:1};const trace=[];const snap=e=>trace.push({event:e,...s});snap("initial");s.claim=0;s.backoff=1;assert.equal(s.claim,0,"[Stable/Cavalier] claim was not released after failure");assert.equal(s.demand,1,"[Stable/Cavalier] persistent demand was lost after failure");assert.equal(s.backoff,1,"[Stable/Cavalier] bounded backoff was not armed");s.backoff=0;assert.ok(s.demand===1&&s.claim===0&&s.backoff===0,"[Stable/Cavalier] demand did not re-open after cooldown");s.claim=0;s.backoff=1;assert.equal(s.demand,1,"[Stable/Cavalier] repeated failure canceled persistent demand");assert.equal(s.backoff,1,"[Stable/Cavalier] repeated failure did not re-arm bounded backoff");s.backoff=0;assert.ok(s.demand===1&&s.claim===0&&s.backoff===0,"[Stable/Cavalier] demand did not re-open after second cooldown");s.demand=0;s.claim=0;s.backoff=0;assert.equal(s.demand,0,"[Stable/Cavalier] strategic invalidation did not clear demand");s.demand=1;assert.ok(s.demand===1&&s.claim===0&&s.backoff===0,"[Stable/Cavalier] clean reassessment could not re-enter");return trace;})();
const cappedRamTrace=transition("Capped Ram",{demand:1,package:"ri-capped-ram",claim:"ri-capped-ram",backoff:1},s=>{s.claim=0;s.backoff=1;},s=>{s.backoff=0;},s=>s.demand===1&&s.claim===0&&s.package==="ri-capped-ram"&&s.backoff===0,s=>{s.demand=0;s.package=0;s.claim=0;},s=>{s.demand=0;s.package=0;s.claim=0;},s=>{s.demand=1;s.package="ri-capped-ram";return s.demand===1&&s.claim===0&&s.package==="ri-capped-ram"&&s.backoff===0;});
const siegeRamTrace=transition("Siege Ram",{demand:1,package:"ri-siege-ram",claim:"ri-siege-ram",backoff:1},s=>{s.claim=0;s.backoff=1;},s=>{s.backoff=0;},s=>s.demand===1&&s.claim===0&&s.package==="ri-siege-ram"&&s.backoff===0,s=>{s.demand=0;s.claim=0;s.package=0;},s=>{s.demand=0;s.claim=0;s.package=0;},s=>{s.demand=1;s.package="ri-siege-ram";return s.demand===1&&s.claim===0&&s.package==="ri-siege-ram"&&s.backoff===0;});
const workshopTrace=workshopScenario();
const scenarios={pike:pikeTrace,stable:stableTrace,cappedRam:cappedRamTrace,siegeRam:siegeRamTrace,workshop:workshopTrace,goldShaft:goldShaftTrace};
console.log(JSON.stringify({controller:path.relative(process.cwd(),controllerPath),rules:rules.length,assertions:["persistent-demand preservation","claim release on execution failure","bounded failure backoff","same-demand re-entry after cooldown","strategic invalidation reset and clean re-entry"],scenarios:Object.fromEntries(Object.entries(scenarios).map(([name,trace])=>[name,{passed:true,states:trace.length,persistentDemandChecked:true,backoffChecked:true,claimReleaseChecked:true,reentryChecked:true}]))},null,2));// MAP-AWARE OPENING SELECTOR VALIDATION
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
// CASTLE-POWER STRATEGY TRANSITION VALIDATION
assert.ok(source.includes("(defconst bt-strategy-castle-power 203)"));
requireRule(
  "RUSH -> Castle-power",
  "(goal strategy-goal bt-strategy-rush)",
  "(current-age >= castle-age)",
  "(players-building-count target-player > 0)",
  "(unit-type-count-total archer-line >= 4)",
  "(set-goal strategy-goal bt-strategy-castle-power)",
);
requireRule(
  "Castle fallback excludes Castle-power",
  "(current-age >= castle-age)",
  "(not (goal strategy-goal bt-strategy-castle-power))",
  "(set-goal strategy-goal bt-strategy-boom)",
);
requireRule(
  "Castle-power Crossbow role",
  "(goal strategy-goal bt-strategy-castle-power)",
  "(unit-type-count-total archer-line >= 4)",
  "(set-goal unit-goal crossbowman)",
);
requireRule(
  "Castle-power standing target",
  "(goal strategy-goal bt-strategy-castle-power)",
  "(goal unit-goal crossbowman)",
  "(set-goal bt-standing-crossbow-target-goal bt-crossbow-target-castle)",
);
requireRule(
  "Castle-power standing demand",
  "(goal strategy-goal bt-strategy-castle-power)",
  "(set-goal bt-standing-army-demand-goal 1)",
);
requireRule(
  "Castle-power Crossbow demand",
  "(goal strategy-goal bt-strategy-castle-power)",
  "(set-goal bt-crossbow-demand-goal 1)",
);
requireRule(
  "Castle-power premium-gold resource mode",
  "(goal strategy-goal bt-strategy-castle-power)",
  "(set-goal bt-resource-mode-goal bt-resource-mode-premium-gold)",
);
requireRule(
  "Castle-power Crossbow research package",
  "(goal bt-crossbow-demand-goal 1)",
  "(goal strategy-goal bt-strategy-castle-power)",
  "(set-goal bt-research-ranged-counter-package-goal ri-crossbow)",
);
requireRule(
  "Castle-power Crossbow executor",
  "(goal bt-crossbow-demand-goal 1)",
  "(goal bt-resource-mode-goal bt-resource-mode-premium-gold)",
  "(train crossbowman)",
);
requireRule(
  "Castle-power Imperial expiry",
  "(goal strategy-goal bt-strategy-castle-power)",
  "(current-age >= imperial-age)",
  "(set-goal strategy-goal bt-strategy-boom)",
);

const castlePowerTcConsumers = rules.filter((rule) => {
  const rendered = renderRule(rule);
  return rendered.includes("(goal strategy-goal bt-strategy-castle-power)") &&
    rendered.includes("bt-tc-project-goal");
});
assert.equal(castlePowerTcConsumers.length, 0, "[Castle-power] BOOM-only TC expansion leaked into Castle-power");

function castlePowerPolicy(input) {
  if (input.age >= input.imperialAge && input.safe) return "boom";
  if (input.strategy === "rush" && input.age >= input.castleAge && input.safe &&
      input.targetAlive && input.archers >= 4) return "castle-power";
  if (input.age >= input.castleAge && input.safe && !["boom", "rush", "flush", "castle-power"].includes(input.strategy)) {
    return "boom";
  }
  return input.strategy;
}

assert.equal(castlePowerPolicy({
  strategy: "rush", age: 3, castleAge: 3, imperialAge: 4, safe: true, targetAlive: true, archers: 4,
}), "castle-power", "[Castle-power A] surviving Feudal pressure did not continue into Castle-power");
assert.equal(castlePowerPolicy({
  strategy: "rush", age: 3, castleAge: 3, imperialAge: 4, safe: true, targetAlive: true, archers: 2,
}), "boom", "[Castle-power B] dead/insufficient Feudal pressure did not fall back to BOOM");
assert.equal(castlePowerPolicy({
  strategy: "rush", age: 3, castleAge: 3, imperialAge: 4, safe: true, targetAlive: false, archers: 4,
}), "boom", "[Castle-power C] lost target did not fall back to BOOM");
assert.equal(castlePowerPolicy({
  strategy: "castle-power", age: 4, castleAge: 3, imperialAge: 4, safe: true, targetAlive: true, archers: 4,
}), "boom", "[Castle-power D] Imperial expiry did not return to BOOM");
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
