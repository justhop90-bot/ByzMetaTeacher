# ByzMetaTeacher repository guide

This repository keeps the executable Basilisk controller separate from the accumulated reference material and audit paperwork. The `.per` controller is not being refactored by the documentation cleanup.

## Repository layout

- `Basilisk/Basilisk.per` — authoritative Basilisk controller. Runtime code; left untouched by this cleanup.
- `Basiliskload.per` — minimal loader for the Basilisk controller.
- `validation/` — repository validators and lifecycle replay/self-test tools.
- `tools/` — maintenance scripts that are not part of the runtime controller.
- `docs/project/` — Basilisk design notes, implementation checklists, and project history.
- `docs/audits/` — historical lint and repair records.
- `docs/reference/` — engine and civilization reference material.
- `docs/validation/` — validation handoff notes.

The large engine-reference set is kept under `docs/reference/engine/` rather than polluting the repository root. Files are grouped by the kind of AIRef material they document.

The cleanup is deliberately repository-only: no Basilisk rule logic, goals, strategic numbers, XS behavior, or runtime include paths are changed here.
