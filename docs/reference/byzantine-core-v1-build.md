# Byzantine Core v1 canonical build

The canonical build is a four-stage artifact pipeline:

```
Byzantine strategy
    -> compiler artifact
    -> runtime assembly
    -> runtime promotion
    -> Byzantine.per
```

Build with:

```bash
PYTHONPATH=LearnerAI python tools/build_byzantine_bot.py
```

The builder produces and verifies:

- `dist/byzantine/Byzantine.compiler.per`
- `dist/byzantine/Byzantine.compiler.manifest.json`
- `dist/byzantine/Byzantine.runtime.per`
- `dist/byzantine/Byzantine.runtime.manifest.json`
- `Byzantine.per`
- `Byzantine.manifest.json`

Runtime assembly consumes the compiler artifact plus the explicitly declared:

```
runtime/byzantine/Byzantine.runtime-overlay.per
runtime/byzantine/Byzantine.runtime-overlay.json
```

The assembler verifies both input hashes, rejects duplicate emitted rule bodies between compiler and overlay, and writes the runtime manifest deterministically. Promotion then byte-copies the verified runtime artifact into the canonical root artifact and verifies byte identity again.

The builder fails closed when the runtime overlay or its manifest is missing. This is intentional: the current repository has not yet extracted a canonical runtime overlay from the checked-in `Byzantine.per`. The old behavior in which `dist/byzantine/Byzantine.per` could be green while root `Byzantine.per` remained a separate hand-repaired artifact is no longer an accepted artifact contract.

The manifests record exact SHA-256 values, canonical paths, compiler source revision, effective Byzantine snapshot identity, assembly lineage, and promotion provenance. The semantic verifier checks the complete compiler -> runtime -> promotion hash chain.

This proves static artifact lineage and reproducibility. It does not prove DE runtime behavior, queue timing, DUC object liveness, native Strategic Number mutation, or any other runtime-only property that remains OPEN evidence.
