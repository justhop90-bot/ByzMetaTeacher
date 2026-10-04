# Byzantine Core v1 canonical build

The Core v1 build is the compiler-produced artifact path. It is separate from the currently checked-in `Byzantine.per` runtime artifact because `main` contains narrow runtime repairs that are not yet represented as compiler policy.

Build the canonical compiler artifact with:

```bash
PYTHONPATH=LearnerAI python tools/build_byzantine_bot.py
```

This writes:

- `dist/byzantine/Byzantine.per`
- `dist/byzantine/Byzantine.manifest.json`

The builder resolves the pinned Byzantine profile, materializes the current effective civilization snapshot, calls the canonical `build_byzantine_strategy()` entry point, compiles it twice, and refuses to write the artifact when the two compilations differ.

The manifest records the profile/civilization/patch identity, effective snapshot fingerprint, artifact SHA-256, source Git revision, build input identity, rule/line counts, artifact byte length, and the native parser revision used by the authoritative CI acceptance workflow.

This proves compiler reproducibility. It does not prove that the generated artifact is already behaviorally equivalent to the hand-repaired checked-in `Byzantine.per`, and it does not prove DE runtime behavior. Those remain separate gates in the Core v1 roadmap.
