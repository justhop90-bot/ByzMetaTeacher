#!/usr/bin/env python3
"""Minimal Basilisk demand DSL compiler.

The DSL is deliberately thin: predicates and actions remain native .per
expressions. The compiler owns demand lifecycle, validation, goal allocation,
and deterministic rule emission.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


class CompileError(ValueError):
    pass


@dataclass(frozen=True)
class Demand:
    name: str
    requirements: tuple[str, ...]
    action: str
    witness: str
    release: str


NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")


def _clean(line: str) -> str:
    return line.split("#", 1)[0].strip()


def parse(source: str) -> list[Demand]:
    lines = [_clean(x) for x in source.splitlines()]
    lines = [x for x in lines if x]
    out: list[Demand] = []
    i = 0
    while i < len(lines):
        m = re.fullmatch(r"demand\s+([A-Za-z][A-Za-z0-9_-]*)\s*\{", lines[i])
        if not m:
            raise CompileError(f"expected demand header: {lines[i]}")
        name = m.group(1)
        i += 1
        reqs: list[str] = []
        fields: dict[str, str] = {}
        while i < len(lines) and lines[i] != "}":
            m = re.match(r"^(require|action|witness|release)\s+(.+)$", lines[i])
            if not m:
                raise CompileError(f"invalid statement: {lines[i]}")
            key, value = m.groups()
            if key == "require":
                reqs.append(value)
            elif key in fields:
                raise CompileError(f"duplicate {key} in demand {name}")
            else:
                fields[key] = value
            i += 1
        if i == len(lines):
            raise CompileError(f"unterminated demand {name}")
        i += 1
        missing = [k for k in ("action", "witness", "release") if k not in fields]
        if missing:
            raise CompileError(f"demand {name} missing: {', '.join(missing)}")
        out.append(Demand(name, tuple(reqs), fields["action"], fields["witness"], fields["release"]))
    return out


def _validate_expr(expr: str, field: str, name: str) -> None:
    if not (expr.startswith("(") and expr.endswith(")")):
        raise CompileError(f"{name}: {field} must be a parenthesized native .per expression")
    if "=>" in expr or "\n" in expr or "\r" in expr:
        raise CompileError(f"{name}: invalid {field} expression")


def validate(demands: list[Demand]) -> None:
    seen: set[str] = set()
    for d in demands:
        if not NAME_RE.fullmatch(d.name):
            raise CompileError(f"invalid demand name: {d.name}")
        if d.name in seen:
            raise CompileError(f"duplicate demand: {d.name}")
        seen.add(d.name)
        if not d.requirements:
            raise CompileError(f"demand {d.name} needs at least one require")
        for expr in d.requirements:
            _validate_expr(expr, "require", d.name)
        _validate_expr(d.action, "action", d.name)
        _validate_expr(d.witness, "witness", d.name)
        _validate_expr(d.release, "release", d.name)


def compile_source(source: str, base_goal: int = 1000) -> str:
    demands = parse(source)
    validate(demands)
    if base_goal < 0:
        raise CompileError("base goal must be non-negative")

    out = [
        ";============================================================",
        "; BASILISK GENERATED .PER",
        "; Generated from Basilisk demand DSL. Do not edit by hand.",
        ";============================================================",
        "",
        "; Demand goal constants",
    ]
    for n, d in enumerate(demands):
        out.append(f"(defconst demand-{d.name} {base_goal + n})")
    out += ["", "; Demand initialization", "(defrule", "    =>"]
    for d in demands:
        out.append(f"    (set-goal demand-{d.name} 1)")
    out += ["    (disable-self)", ")", ""]

    for d in demands:
        out += [f"; Demand: {d.name}", "(defrule", f"    (goal demand-{d.name} 1)"]
        out.extend(f"    {r}" for r in d.requirements)
        out += ["=>", f"    {d.action}", ")", "",
                f"; Witness/release: {d.name}", "(defrule",
                f"    (goal demand-{d.name} 1)", f"    {d.witness}", f"    {d.release}",
                "=>", f"    (set-goal demand-{d.name} 0)", ")", ""]
    return "\n".join(out).rstrip() + "\n"


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
