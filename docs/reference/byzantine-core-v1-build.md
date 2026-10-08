# Byzantine Core v1 canonical build

The canonical build has two distinct ownership layers:

```
Byzantine strategy
    -> compiler artifact
    -> woven-runtime provenance verification
    -> packaged runtime artifact
```

The compiler owns the rules it emits. The checked-in `Byzantine.per` is the authoritative woven runtime program and owns final rule ordering because community/runtime adaptations are interleaved with compiler-owned rules.

Build with:

```bash
PYTHONPATH=LearnerAI python tools/build_byzantine_bot.py
```

The builder produces and verifies:

- `dist/byzantine/Byzantine.compiler.per`
- `dist/byzantine/Byzantine.compiler.manifest.json`
- `dist/byzantine/Byzantine.runtime.per`
- `dist/byzantine/Byzantine.runtime.manifest.json`

The packaged runtime artifact is a byte copy of the checked-in authoritative `Byzantine.per`. The compiler does not reorder or reconstruct the woven runtime program.

The critical lineage invariant is rule conservation. Every compiler-owned `defrule` body, including duplicate multiplicity, must occur verbatim in the authoritative woven runtime artifact. The verifier does not require compiler rule order to equal runtime rule order because the latter is a community/runtime composition boundary.

This closes the previous split-brain failure mode more honestly than a compiler-plus-suffix overlay model. A changed compiler rule that disappears from the woven runtime is a hard lineage failure. A community-only runtime rule is permitted and remains outside compiler ownership.

The manifests record exact SHA-256 values, compiler source revision, effective Byzantine snapshot identity, compiler rule count, woven runtime rule count, and the conservation result.

This proves static artifact provenance and reproducibility. It does not prove DE runtime behavior, queue timing, DUC object liveness, native Strategic Number mutation, or other runtime-only properties that remain OPEN evidence.
