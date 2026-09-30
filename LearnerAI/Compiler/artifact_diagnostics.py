"""Deterministic semantic diagnostic annotations for promoted .per artifacts."""

from __future__ import annotations

import re
import textwrap
from collections.abc import Iterable


_HEADER = "; COMPILER RULE DIAGNOSTICS"
_FOOTER = "; END COMPILER RULE DIAGNOSTICS"
_MESSAGE_WIDTH = 180
_WHITESPACE = re.compile(r"\\s+")


def _value(value: object, default: str = "") -> str:
    if value is None:
        return default
    return getattr(value, "value", str(value))


def _persistent(item: object) -> bool:
    return _value(getattr(item, "category", None)) in {
        "PERSISTENT_STATE",
        "PERSISTENT_CONTROL",
    }


def _sort_key(item: object) -> tuple[object, ...]:
    related = getattr(item, "related_rule_order", None)
    return (
        int(getattr(item, "rule_order", 0)),
        _value(getattr(item, "code", None)),
        _value(getattr(item, "state_kind", None)),
        str(getattr(item, "state_identifier", None) or ""),
        int(related) if related is not None else -1,
        str(getattr(item, "related_operation", None) or ""),
        str(getattr(item, "message", "")),
    )


def _message_lines(message: object) -> tuple[str, ...]:
    normalized = _WHITESPACE.sub(" ", str(message).strip())
    if not normalized:
        return ("",)
    return tuple(
        textwrap.wrap(
            normalized,
            width=_MESSAGE_WIDTH,
            break_long_words=False,
            break_on_hyphens=False,
        )
    )


def append_persistent_rule_diagnostics(
    artifact: str,
    diagnostics: Iterable[object],
) -> str:
    """Append stable human-readable PSTATE diagnostics as .per comments."""
    if not isinstance(artifact, str):
        raise TypeError("artifact must be a string")

    persistent = tuple(
        sorted(
            (item for item in diagnostics if _persistent(item)),
            key=_sort_key,
        )
    )
    if not persistent:
        return artifact

    lines = [
        _HEADER,
        "; Persistent-state/control findings are advisory compiler evidence only.",
    ]
    for item in persistent:
        related_rule = getattr(item, "related_rule_order", None)
        related_text = (
            str(related_rule) if related_rule is not None else "none"
        )
        state_kind = str(getattr(item, "state_kind", "") or "unknown")
        state_identifier = str(
            getattr(item, "state_identifier", "") or "unknown"
        )
        operation = str(
            getattr(item, "related_operation", "") or "none"
        )
        category = _value(getattr(item, "category", None))
        lines.append(
            f"; {category} "
            f"rule={int(getattr(item, 'rule_order', 0))} "
            f"code={_value(getattr(item, 'code', None))} "
            f"severity={_value(getattr(item, 'severity', None))} "
            f"state={state_kind}:{state_identifier} "
            f"related-rule={related_text} "
            f"related-operation={operation}"
        )
        wrapped = _message_lines(getattr(item, "message", ""))
        lines.append(f"; message={wrapped[0]}")
        lines.extend(f"; message+={line}" for line in wrapped[1:])
    lines.append(_FOOTER)

    separator = "" if artifact.endswith("\n") else "\n"
    return artifact + separator + "\n".join(lines) + "\n"


__all__ = ["append_persistent_rule_diagnostics"]
