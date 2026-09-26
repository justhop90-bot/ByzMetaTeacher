# State Timers

Timers are execution mechanisms, not strategic truth.

## Valid uses

- temporary cooldown;
- bounded watchdog;
- attack regrouping;
- re-observation cadence;
- engine-required timing.

## Invalid use

Do not use a timer as the sole proof that:

- Castle should happen;
- the economy is ready;
- an enemy is committed to a unit;
- a technology is completed;
- an army is strong enough.

## Source

Read AIRef timer semantics, current Basilisk timer usage, and docs/audits/Basilisk-Removable-State-Audit-2026-09.md.

## Acceptance

Every timer must have an owner, purpose, start/reset behavior, and release/expiry meaning.
