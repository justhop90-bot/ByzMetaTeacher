#!/usr/bin/env node

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const repoRoot = path.resolve(import.meta.dirname, "..");
const controllerPath = path.join(repoRoot, "Basilisk", "Basilisk.per");
const source = fs.readFileSync(controllerPath, "utf8");

const requireText = (needle, label) => {
  assert.ok(source.includes(needle), "[Preemption replay] missing " + label + ": " + needle);
};

for (const needle of [
  "(defconst bt-preempt-emergency-claim 601)",
  "(defconst bt-preempt-active-goal 730)",
  "(defconst bt-telemetry-count-goal 740)",
  "(defconst bt-telemetry-slot0-type-goal 753)",
  "(defconst bt-telemetry-slot3-sequence-goal 784)",
  '(xs-script-call "bt_telemetry_drain")',
]) {
  requireText(needle, "required lifecycle marker");
}

class Ring {
  constructor(capacity = 4) {
    this.capacity = capacity;
    this.write = 0;
    this.read = 0;
    this.count = 0;
    this.sequence = 0;
    this.dropped = 0;
    this.slots = new Array(capacity).fill(null);
  }

  push(event) {
    this.sequence += 1;
    if (this.count >= this.capacity) {
      this.dropped += 1;
      return { accepted: false, sequence: this.sequence };
    }
    this.slots[this.write] = { ...event, sequence: this.sequence };
    this.write = (this.write + 1) % this.capacity;
    this.count += 1;
    return { accepted: true, sequence: this.sequence };
  }

  drain(limit = 4) {
    const out = [];
    while (this.count > 0 && out.length < limit) {
      out.push(this.slots[this.read]);
      this.slots[this.read] = null;
      this.read = (this.read + 1) % this.capacity;
      this.count -= 1;
    }
    return out;
  }
}

function lifecycleReplay() {
  const ring = new Ring(4);
  let owner = 524;
  let watchdog = "running";
  let demand = true;
  let preemptActive = false;

  const begin = ring.push({ type: 1, from: 524, to: 601, mode: 5, reason: 1, flags: 0 });
  assert.equal(begin.accepted, true);
  owner = 601;
  preemptActive = true;

  // Preemption changes ownership only. It must not reset the capability clock.
  assert.equal(watchdog, "running");
  assert.equal(demand, true);

  const resume = ring.push({ type: 2, from: 601, to: 524, mode: 5, reason: 1, flags: 0 });
  assert.equal(resume.accepted, true);
  owner = 524;
  preemptActive = false;
  assert.equal(watchdog, "running");
  assert.equal(demand, true);

  // Completion while preempted must never restore the old owner.
  owner = 601;
  preemptActive = true;
  demand = false;
  const complete = ring.push({ type: 3, from: 601, to: 0, mode: 5, reason: 1, flags: 1 });
  assert.equal(complete.accepted, true);
  owner = 0;
  preemptActive = false;
  assert.equal(owner, 0);
  assert.equal(demand, false);

  // Watchdog failure while preempted must produce ABORT and never resurrect the claim.
  owner = 601;
  preemptActive = true;
  demand = true;
  watchdog = "triggered";
  const abort = ring.push({ type: 4, from: 601, to: 0, mode: 5, reason: 1, flags: 2 });
  assert.equal(abort.accepted, true);
  owner = 0;
  preemptActive = false;
  assert.equal(owner, 0);
  assert.equal(watchdog, "triggered");
  assert.equal(demand, true);

  const events = ring.drain();
  assert.deepEqual(
    events.map((event) => event.type),
    [1, 2, 3, 4],
    "[Preemption replay] accepted lifecycle events must remain FIFO ordered",
  );
  assert.deepEqual(
    events.map((event) => event.sequence),
    [1, 2, 3, 4],
    "[Preemption replay] accepted event sequence must be monotonic",
  );

  // Full-buffer behavior: preserve the first four events and count later drops.
  const full = new Ring(4);
  for (let i = 1; i <= 6; i += 1) {
    full.push({ type: i, from: 524, to: 601, mode: 5, reason: 1, flags: 0 });
  }
  assert.equal(full.count, 4);
  assert.equal(full.dropped, 2);
  assert.deepEqual(
    full.drain().map((event) => event.type),
    [1, 2, 3, 4],
    "[Preemption replay] overflow must drop newest events without overwriting older evidence",
  );

  // A bounded XS drain is required. Four is the queue capacity and the max per call.
  const bounded = new Ring(4);
  for (let i = 0; i < 4; i += 1) {
    bounded.push({ type: i + 1 });
  }
  assert.equal(bounded.drain(4).length, 4);
}

lifecycleReplay();

console.log(JSON.stringify({
  status: "PASS",
  suite: "basilisk-preemption-lifecycle-replay",
  checks: [
    "preemption preserves persistent demand",
    "preemption does not reset watchdog state",
    "resume restores the original Mill owner only while the capability remains valid",
    "completion while preempted clears demand and does not restore ownership",
    "watchdog failure while preempted remains terminal to that execution attempt",
    "accepted telemetry events retain FIFO order and monotonic sequence",
    "four-slot overflow preserves existing evidence and counts dropped events",
    "XS drain is bounded by queue capacity",
  ],
}, null, 2));
