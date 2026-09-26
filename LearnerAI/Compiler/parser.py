"""Parser for the intentionally small Basilisk demand language."""
from __future__ import annotations
import re
from .ast import DemandNode, SourceLocation
from .errors import CompileError

_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
_HEADER_RE = re.compile(r"^demand\s+([A-Za-z][A-Za-z0-9_-]*)\s*\{$")
_FIELDS = ("action", "witness", "release")

def _clean_line(line: str) -> tuple[str, int]:
    without_comment = line.split("#", 1)[0]
    leading = len(without_comment) - len(without_comment.lstrip())
    return without_comment.strip(), leading + 1

def _location(line_no: int, column: int) -> SourceLocation:
    return SourceLocation(line_no, column)

def parse(source: str) -> list[DemandNode]:
    raw = source.splitlines()
    out: list[DemandNode] = []
    i = 0
    while i < len(raw):
        text, column = _clean_line(raw[i])
        line_no = i + 1
        if not text:
            i += 1
            continue
        match = _HEADER_RE.fullmatch(text)
        if not match:
            raise CompileError(f"line {line_no}: expected 'demand <name> {{'")
        name = match.group(1)
        header_location = _location(line_no, column)
        if not _NAME_RE.fullmatch(name):
            raise CompileError(f"line {line_no}: invalid demand name '{name}'")
        i += 1
        reqs: list[str] = []
        req_locations: list[SourceLocation] = []
        fields: dict[str, str] = {}
        field_locations: dict[str, SourceLocation] = {}
        while i < len(raw):
            text, statement_column = _clean_line(raw[i])
            line_no = i + 1
            if not text:
                i += 1
                continue
            if text == "}":
                break
            match = re.fullmatch(r"(require|action|witness|release|invalidate)\s+(.+)", text)
            if not match:
                raise CompileError(f"line {line_no}: invalid demand statement")
            key, value = match.groups()
            value_column = statement_column + match.start(2)
            value_location = _location(line_no, value_column)
            if key == "require":
                reqs.append(value)
                req_locations.append(value_location)
            elif key in fields:
                raise CompileError(f"line {line_no}: duplicate {key} in demand '{name}'")
            else:
                fields[key] = value
                field_locations[key] = value_location
            i += 1
        if i >= len(raw):
            raise CompileError(f"line {line_no}: unterminated demand '{name}'")
        missing = [x for x in _FIELDS if x not in fields]
        if not reqs:
            raise CompileError(f"demand '{name}' needs at least one require")
        if missing:
            if "witness" in missing:
                raise CompileError(f"PENDING-WITNESS-MISSING: demand '{name}' missing completion witness")
            raise CompileError(f"demand '{name}' missing: {', '.join(missing)}")
        out.append(
            DemandNode(
                name,
                tuple(reqs),
                fields["action"],
                fields["witness"],
                fields["release"],
                header_location,
                fields.get("invalidate"),
                tuple(req_locations),
                field_locations.get("action"),
                field_locations.get("witness"),
                field_locations.get("release"),
                field_locations.get("invalidate"),
            )
        )
        i += 1
    names = [d.name for d in out]
    if len(names) != len(set(names)):
        dup = next(n for n in names if names.count(n) > 1)
        raise CompileError(f"duplicate demand '{dup}'")
    return out
