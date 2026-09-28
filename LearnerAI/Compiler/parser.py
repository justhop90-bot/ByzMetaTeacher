"""Parser for the intentionally small AoE2 .per compiler source language."""
from __future__ import annotations
import re
from .ast import DemandNode, SourceLocation
from .errors import CompileError

_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
_HEADER_RE = re.compile(r"^demand\s+([A-Za-z][A-Za-z0-9_-]*)\s*\{$")
_FIELDS = ("action", "witness", "release")
_SN_STATE_RE = re.compile(r"^sn\s+([a-z][a-z0-9_-]*)\s*=\s*(-?[0-9]+)$")

def _clean_line(line: str) -> tuple[str, int]:
    without_comment = line.split("#", 1)[0]
    leading = len(without_comment) - len(without_comment.lstrip())
    return without_comment.strip(), leading + 1

def _location(
    line_no: int,
    column: int,
    *,
    source_unit: str,
    line_offset: int,
    first_line_column_offset: int,
) -> SourceLocation:
    if line_no == 1:
        column += first_line_column_offset
    return SourceLocation(line_no + line_offset, column, source_unit)


def parse(
    source: str,
    *,
    source_unit: str = "<source>",
    line_offset: int = 0,
    first_line_column_offset: int = 0,
) -> list[DemandNode]:
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
        header_location = _location(
            line_no,
            column,
            source_unit=source_unit,
            line_offset=line_offset,
            first_line_column_offset=first_line_column_offset,
        )
        if not _NAME_RE.fullmatch(name):
            raise CompileError(f"line {line_no + line_offset}: invalid demand name '{name}'")
        i += 1
        reqs: list[str] = []
        req_locations: list[SourceLocation] = []
        fields: dict[str, str] = {}
        field_locations: dict[str, SourceLocation] = {}
        strategic_number_states: list[tuple[str, int, SourceLocation]] = []
        while i < len(raw):
            text, statement_column = _clean_line(raw[i])
            line_no = i + 1
            if not text:
                i += 1
                continue
            if text == "}":
                break
            sn_match = _SN_STATE_RE.fullmatch(text)
            if sn_match:
                sn_name, sn_value = sn_match.groups()
                if any(existing[0] == sn_name for existing in strategic_number_states):
                    raise CompileError(
                        f"line {line_no + line_offset}: duplicate sn state '{sn_name}' "
                        f"in demand '{name}'"
                    )
                if not -32768 <= int(sn_value) <= 32767:
                    raise CompileError(
                        f"line {line_no + line_offset}: SN state '{sn_name}' initial value "
                        "must be in -32768..32767"
                    )
                value_location = _location(
                    line_no,
                    statement_column,
                    source_unit=source_unit,
                    line_offset=line_offset,
                    first_line_column_offset=first_line_column_offset,
                )
                strategic_number_states.append(
                    (sn_name, int(sn_value), value_location)
                )
                i += 1
                continue
            match = re.fullmatch(r"(require|action|witness|release|invalidate)\s+(.+)", text)
            if not match:
                raise CompileError(f"line {line_no + line_offset}: invalid demand statement")
            key, value = match.groups()
            value_column = statement_column + match.start(2)
            value_location = _location(
                line_no,
                value_column,
                source_unit=source_unit,
                line_offset=line_offset,
                first_line_column_offset=first_line_column_offset,
            )
            if key == "require":
                reqs.append(value)
                req_locations.append(value_location)
            elif key in fields:
                raise CompileError(f"line {line_no + line_offset}: duplicate {key} in demand '{name}'")
            else:
                fields[key] = value
                field_locations[key] = value_location
            i += 1
        if i >= len(raw):
            raise CompileError(f"line {line_no + line_offset}: unterminated demand '{name}'")
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
                tuple(strategic_number_states),
            )
        )
        i += 1
    names = [d.name for d in out]
    if len(names) != len(set(names)):
        dup = next(n for n in names if names.count(n) > 1)
        raise CompileError(f"duplicate demand '{dup}'")
    return out
