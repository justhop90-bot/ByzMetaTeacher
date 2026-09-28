from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class DucOracleConsistencyError(ValueError):
    """Raised when a validly-shaped oracle artifact is internally inconsistent."""


def validate_oracle_consistency(document: Mapping[str, Any]) -> None:
    """Validate semantic relationships left outside portable JSON Schema."""

    fixture = document["fixture"]
    assertions = fixture["assertions"]

    assertion_ids = [assertion["id"] for assertion in assertions]
    if len(assertion_ids) != len(set(assertion_ids)):
        raise DucOracleConsistencyError(
            "fixture assertions contain duplicate ids"
        )

    _validate_fixture_assertion_references(document)


def _validate_fixture_assertion_references(
    document: Mapping[str, Any],
) -> None:
    fixture = document["fixture"]

    for assertion in fixture["assertions"]:
        path = assertion.get("observation_path")
        if path is None:
            continue
        if not _json_pointer_exists(document, path):
            raise DucOracleConsistencyError(
                f"fixture assertion {assertion['id']!r} references missing "
                f"observation path {path!r}"
            )


def _json_pointer_exists(document: Any, pointer: str) -> bool:
    if pointer == "":
        return True

    current = document
    for raw_token in pointer.strip("/").split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping):
            if token not in current:
                return False
            current = current[token]
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes)):
            try:
                current = current[int(token)]
            except (ValueError, IndexError):
                return False
        else:
            return False
    return True


__all__ = [
    "DucOracleConsistencyError",
    "validate_oracle_consistency",
]
