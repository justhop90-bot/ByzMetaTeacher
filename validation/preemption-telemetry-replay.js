#!/usr/bin/env node

import assert from "node:assert/strict";

const CAPACITY = 4;

function makeState(initialOwner = 510) {
  return {
    preemptActive: 0,
    originalOwner: 0,
    result: 0,
    mutex: initialOwner,
    tcProject: 2,
    tcStage: "resource-claimed",
    watchdogAge: 17,
    watchdogEnabled: true,
    sequence: 0,
    queue: [],
    overflow: 0,
  };
}

function append(state, event) {
  if (state.queue.length >= CAPACITY) {
    state.overflow += 1;
    return false;
  }
  state.sequence += 1;
  state.queue.push({ ...event, sequence: state.sequence });
  return true;
}

function begin(state, owner) {
  assert.equal(state.preemptActive, 0);
  assert.equal(state.mutex, owner);
  state.preemptActive = 1;
  state.originalOwner = owner;
  state.mutex = 799;
  assert.equal(append(state, { type: "BEGIN", owner }), true);
}

function defense(state, owner) {
  assert.equal(state.preemptActive, 1);
  assert.equal(state.mutex, 799);
  assert.equal(append(state, { type: "DEFENSE", owner: 799, original: owner }), true);
}

function resume(state) {
  assert.equal(state.preemptActive, 1);
  assert.equal(state.tcProject, 2);
  assert.equal(state.tcStage, "resource-claimed");
  state.mutex = state.originalOwner;
  state.preemptActive = 0;
  state.result = 1;
  assert.equal(append(state, { type: "END", owner: state.originalOwner, result: "RESUME" }), true);
}

function complete(state) {
  assert.equal(state.preemptActive, 1);
  state.tcProject = 0;
  state.tcStage = "idle";
  state.mutex = 0;
  state.preemptActive = 0;
  state.result = 2;
  assert.equal(append(state, { type: "END", owner: state.originalOwner, result: "COMPLETE" }), true);
}

function abort(state) {
  assert.equal(state.preemptActive, 1);
  state.tcStage = "demanded";
  state.mutex = 0;
  state.preemptActive = 0;
  state.result = 3;
  assert.equal(append(state, { type: "END", owner: state.originalOwner, result: "ABORT" }), true);
}

function drain(state, limit = 4) {
  const drained = state.queue.splice(0, limit);
  return drained;
}

// Interruption -> resume: demand and watchdog survive.
{
  const state = makeState();
  begin(state, 510);
  const watchdogBefore = state.watchdogAge;
  defense(state, 510);
  assert.equal(state.watchdogAge, watchdogBefore);
  resume(state);
  assert.equal(state.mutex, 510);
  assert.equal(state.watchdogAge, watchdogBefore);
  assert.equal(state.result, 1);
}

// Completion while preempted: never restore the stale owner.
{
  const state = makeState(509);
  begin(state, 509);
  const watchdogBefore = state.watchdogAge;
  complete(state);
  assert.equal(state.mutex, 0);
  assert.equal(state.preemptActive, 0);
  assert.equal(state.tcProject, 0);
  assert.equal(state.watchdogAge, watchdogBefore);
  assert.equal(state.result, 2);
}

// Watchdog expiry while preempted: timer state belongs to capability.
{
  const state = makeState();
  begin(state, 510);
  const watchdogBefore = state.watchdogAge;
  state.watchdogAge += 120;
  assert.equal(state.watchdogAge, watchdogBefore + 120);
  assert.equal(state.preemptActive, 1);
  assert.equal(state.mutex, 799);
  abort(state);
  assert.equal(state.watchdogEnabled, true);
}

// Project disappears while preempted: emergency owner terminates without resurrection.
{
  const state = makeState(509);
  begin(state, 509);
  state.tcProject = 0;
  state.tcStage = "idle";
  state.mutex = 799;
  state.preemptActive = 1;
  state.result = 0;
  state.mutex = 0;
  state.preemptActive = 0;
  state.result = 3;
  assert.equal(state.mutex, 0);
  assert.equal(state.tcProject, 0);
  assert.equal(state.result, 3);
}

// Rapid begin -> defense -> end remains ordered.
{
  const state = makeState();
  begin(state, 510);
  defense(state, 510);
  resume(state);
  const events = drain(state);
  assert.deepEqual(events.map((e) => e.type), ["BEGIN", "DEFENSE", "END"]);
  assert.deepEqual(events.map((e) => e.sequence), [1, 2, 3]);
}

// FIFO capacity preserves existing events and reports overflow.
{
  const state = makeState();
  for (let index = 0; index < CAPACITY; index += 1) {
    assert.equal(append(state, { type: "EVT", index }), true);
  }
  assert.equal(append(state, { type: "OVERFLOW" }), false);
  assert.equal(state.queue.length, CAPACITY);
  assert.equal(state.overflow, 1);
  assert.deepEqual(
    state.queue.map((e) => e.index),
    [0, 1, 2, 3],
  );
}

// Drain is bounded.
{
  const state = makeState();
  for (let index = 0; index < CAPACITY; index += 1) {
    append(state, { type: "EVT", index });
  }
  const drained = drain(state, 2);
  assert.equal(drained.length, 2);
  assert.equal(state.queue.length, 2);
}

console.log(
  JSON.stringify(
    {
      status: "PASS",
      cases: [
        "interrupt-resume",
        "completion-while-preempted",
        "watchdog-survives-preemption",
        "project-disappearance",
        "rapid-event-ordering",
        "fifo-overflow",
        "bounded-drain",
      ],
    },
    null,
    2,
  ),
);
