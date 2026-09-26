#!/usr/bin/env python3
"""Basilisk compiler entry point.

Pipeline: source -> AST -> semantic IR -> deterministic .per.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    compiler_dir = Path(__file__).resolve().parent
    sys.path[:] = [entry for entry in sys.path if Path(entry or ".").resolve() != compiler_dir]
    sys.path.insert(0, str(compiler_dir.parent))
    from Compiler.errors import CompileError
    from Compiler.parser import parse
    from Compiler.primitives import default_de_registry
    from Compiler.semantic import analyze
    from Compiler.emitter import emit
else:
    from .errors import CompileError
    from .parser import parse
    from .primitives import default_de_registry
    from .semantic import analyze
    from .emitter import emit

def compile_source(source: str, base_goal: int = 1000) -> str:
    ast = parse(source)
    ir = analyze(ast, default_de_registry(), base_goal)
    return emit(ir)

def main() -> int:
    ap = argparse.ArgumentParser(description="Compile Basilisk demand DSL to .per")
    ap.add_argument("source", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--base-goal", type=int, default=1000)
    args = ap.parse_args()
    try:
        result = compile_source(args.source.read_text(encoding="utf-8"), args.base_goal)
    except (OSError, CompileError) as exc:
        ap.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result, encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
