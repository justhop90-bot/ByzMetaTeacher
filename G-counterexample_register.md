# Counterexample register (mandatory) — claims vs contradictory evidence
Each entry: assumption | contradiction | evidence | implication | status.

1. ASSUMPTION: attack-now is the attack actuator.
   CONTRA: local corpus has 47 attack-now vs 1455 town-size + 10202 set-SN; control is
   SN/town-size/DUC-mediated. Promisory/Naga pipelines stage via groups/targets.
   IMPL: attack lifecycle must model mediated control, not just attack-now. The compiler now connects only the narrow issue emission path; mediated control, completion, release, and group-state semantics remain open.
   STATUS: OPEN — issue slice connected; needs full attack-controller lifecycle (Prompt 9).

2. ASSUMPTION: escrow is a minor feasibility flag.
   CONTRA: 10859 escrow hits; escrow.per (Promisory) + commodity.per + resource_control 49KB (Duke).
   IMPL: escrow lowering is a first-line gap, not polish. STATUS: OPEN (Prompt 6).

3. ASSUMPTION: DUC needs only syntactic support.
   CONTRA: 11595 up-find + 11898 up-set-target; retained filters/capacity/stale targets
   carry cross-pass state the binder marks UNSUPPORTED.
   IMPL: DUC emission is blocking for military/scouting fidelity. STATUS: OPEN (Prompts 7-8).

4. ASSUMPTION: pending/total counts are completion-safe witnesses.
   CONTRA: `test_pending_and_total_state_cannot_be_completion_witness` forbids them, but
   lewisc64 current+queued idiom treats them as admission; no engine proof either way.
   IMPL: needs runtime/label proof, currently COMPILER POLICY. STATUS: OPEN (Prompt 5).

5. ASSUMPTION: same-pass goal visibility follows source order for all accesses.
   CONTRA: `source_order.py` explicitly drops LIFECYCLE accesses; lifecycle order enforced
   separately by witness/release validators + emitter. Untested interaction for mixed access.
   IMPL: Prompt-1 root-cause territory. STATUS: UNDER INVESTIGATION (PR86).

6. ASSUMPTION: `resource-found` latches permanently.
   CONTRA: no engine proof of latch-vs-live; dropsite rules in Niek assume re-query value.
   IMPL: mark OPEN-UNKNOWN until runtime evidence. STATUS: OPEN.

7. ASSUMPTION: TSA 12→144 unrolled rules are the pattern to compile.
   CONTRA: unrolling is a workaround for no arithmetic; compiler should generate
   arithmetically (lewisc64 `+=` precedent).
   IMPL: expressiveness gap is semantic, not syntactic. STATUS: DESIGN GUIDANCE (Prompt 12).

8. ASSUMPTION: ten bots doing X = ten independent evidences.
   CONTRA: niektb/AI is a snapshot of tim-kos Duke; TSA is a single textbook lineage;
   team-coordination-goal 392 shared Barbarian↔Promi↔HD-AI.
   IMPL: lineage must discount duplicates (this register applies the discount).
   STATUS: METHOD APPLIED.

9. ASSUMPTION: unknown SNs fail loudly.
   CONTRA: community practice assumes silent ignore (version-dependent); no engine proof.
   IMPL: SN catalog must record per-SN version scope, not assume errors. STATUS: OPEN (Prompt 3).

10. ASSUMPTION: `timer-triggered` can be statically proven true.
    CONTRA: `recurrent_execution.py:185-186` forces UNKNOWN by design (staged expiry).
    IMPL: not a bug —AÇÃO tests must assert UNKNOWN, and DSL must not require static-true.
    STATUS: CONFIRMED DESIGN (not a gap).

11. ASSUMPTION: load order never affects behavior beyond inclusion.
    CONTRA: Duke per-map loads + defconst shadowing across 27 files; order-sensitive
    constant/mode setup is standard practice.
    IMPL: source_graph fingerprint must remain order-sensitive (it is) — do not normalize.
    STATUS: GUARDED.

12. ASSUMPTION: `56% compiler / 42% bot` estimates are measurable.
    CONTRA: no coverage denominator exists yet; DUC/SN/timer tests are fixture-only and
    would inflate emission coverage if counted.
    IMPL: replace with artifact-based measurement (Section Coverage below).
    STATUS: SUPERSEDED by this program.
