from __future__ import annotations

import hashlib
from pathlib import Path

from Compiler.compiler import compile_source


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "Compiler" / "examples" / "basics.basilisk"
GENERATED = ROOT / "Compiler" / "generated" / "Basilisk.per"


def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    generated = compile_source(source).encode("utf-8")
    checked_in = GENERATED.read_bytes()

    if generated != checked_in:
        expected_sha = hashlib.sha256(generated).hexdigest()
        actual_sha = hashlib.sha256(checked_in).hexdigest()
        raise SystemExit(
            "generated/Basilisk.per is stale or non-reproducible: "
            f"expected sha256={expected_sha}, actual sha256={actual_sha}"
        )

    print(
        "verified generated/Basilisk.per is reproducible "
        f"(sha256={hashlib.sha256(checked_in).hexdigest()})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
