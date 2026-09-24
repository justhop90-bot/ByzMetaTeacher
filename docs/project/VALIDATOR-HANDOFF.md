# Basilisk Validator Handoff

The authoritative controller is `Basilisk/Basilisk.per`.
The authoritative validator is `validation/basilisk-validator.js`.
The deterministic lifecycle replay harness is `validation/repair-lifecycle-replay.js`.
The repository's reference inventories live under `docs/reference/inventories/`.

Validation order is intentional: parser and structural checks precede engine-limit checks, identifier and command vocabulary checks, lifecycle contracts, replay validation, source-order checks, and legacy-harness handoff checks.

The validator must not reference the retired `extracted/` inventory tree or the obsolete ByzTeacher controller path.
The validator must continue to require a handoff document so repository cleanup cannot silently sever the relationship between the current Basilisk controller and its validation harness.

Runtime gameplay remains the final behavioral authority. Static validation proves wiring and engine-contract invariants; it does not prove that Basilisk wins a live AoE2DE match.
