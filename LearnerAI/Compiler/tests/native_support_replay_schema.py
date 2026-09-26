from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

SCHEMA_VERSION = 1
FIXTURE_NAMES = frozenset(
    {"native-known", "native-typed", "semantically-adapted", "unsupported"}
)
PLATFORMS = frozenset({"linux", "win32", "darwin"})
SUPPORT_STATES = frozenset(
    {
        "native-known",
        "native-typed",
        "semantically-adapted",
        "executable-safe",
        "unsupported",
    }
)
DIAGNOSTIC_SOURCES = frozenset({"LearnerAI", "aoe2-ai-parser"})
DIAGNOSTIC_SEVERITIES = frozenset({"error", "warning", "info"})
SUPPORT_CODES = frozenset(
    {
        "NATIVE-SUPPORT-001",
        "NATIVE-SUPPORT-002",
        "NATIVE-SUPPORT-003",
        "NATIVE-SUPPORT-004",
        "NATIVE-SUPPORT-005",
    }
)

TOP_LEVEL_FIELDS = frozenset({"schema_version", "python", "platform", "fixtures"})
FIXTURE_FIELDS = frozenset(
    {
        "diagnostics",
        "support_diagnostics",
        "support_state_sequence",
        "artifact_sha256",
    }
)
DIAGNOSTIC_FIELDS = frozenset(
    {
        "id",
        "source",
        "code",
        "severity",
        "confidence",
        "message",
        "suggestion",
        "path",
        "line",
        "column",
        "end_line",
        "end_column",
        "references",
    }
)
SUPPORT_DIAGNOSTIC_FIELDS = frozenset(
    {"command", "state", "code", "severity", "message"}
)

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_ID = re.compile(r"^[0-9a-f]{64}$")


class SnapshotSchemaError(ValueError):
    """Raised when a cross-platform replay snapshot violates its schema."""


def _fail(path: str, message: str) -> None:
    raise SnapshotSchemaError(f"{path}: {message}")


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(path, f"expected object, got {type(value).__name__}")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(path, f"expected array, got {type(value).__name__}")
    return value


def _exact_keys(
    value: Mapping[str, Any],
    expected: frozenset[str],
    path: str,
) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        _fail(path, f"missing fields: {', '.join(missing)}")
    if extra:
        _fail(path, f"extra fields: {', '.join(extra)}")


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str):
        _fail(path, f"expected string, got {type(value).__name__}")
    if not value:
        _fail(path, "must not be empty")
    return value


def _optional_string(value: Any, path: str) -> None:
    if value is not None and not isinstance(value, str):
        _fail(path, f"expected string or null, got {type(value).__name__}")


def _optional_integer(value: Any, path: str) -> None:
    if value is not None and type(value) is not int:
        _fail(path, f"expected integer or null, got {type(value).__name__}")


def _json_value(value: Any, path: str) -> None:
    if value is None or type(value) in {str, int, float, bool}:
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                _fail(path, "reference object keys must be strings")
            _json_value(item, f"{path}.{key}")
        return
    _fail(path, f"contains non-JSON value {type(value).__name__}")


def _validate_diagnostic(value: Any, path: str) -> None:
    item = _mapping(value, path)
    _exact_keys(item, DIAGNOSTIC_FIELDS, path)

    identifier = _string(item["id"], f"{path}.id")
    if not _ID.fullmatch(identifier):
        _fail(f"{path}.id", "must be a 64-character lowercase hexadecimal digest")

    source = _string(item["source"], f"{path}.source")
    if source not in DIAGNOSTIC_SOURCES:
        _fail(f"{path}.source", f"unsupported source {source!r}")

    _string(item["code"], f"{path}.code")
    severity = _string(item["severity"], f"{path}.severity")
    if severity not in DIAGNOSTIC_SEVERITIES:
        _fail(f"{path}.severity", f"unsupported severity {severity!r}")

    _optional_string(item["confidence"], f"{path}.confidence")
    _string(item["message"], f"{path}.message")
    _optional_string(item["suggestion"], f"{path}.suggestion")
    _optional_string(item["path"], f"{path}.path")
    _optional_integer(item["line"], f"{path}.line")
    _optional_integer(item["column"], f"{path}.column")
    _optional_integer(item["end_line"], f"{path}.end_line")
    _optional_integer(item["end_column"], f"{path}.end_column")

    references = _list(item["references"], f"{path}.references")
    for index, reference in enumerate(references):
        reference_path = f"{path}.references[{index}]"
        _mapping(reference, reference_path)
        _json_value(reference, reference_path)


def _validate_support_diagnostic(value: Any, path: str) -> None:
    item = _mapping(value, path)
    _exact_keys(item, SUPPORT_DIAGNOSTIC_FIELDS, path)

    _string(item["command"], f"{path}.command")
    state = _string(item["state"], f"{path}.state")
    if state not in SUPPORT_STATES:
        _fail(f"{path}.state", f"unsupported state {state!r}")

    code = _string(item["code"], f"{path}.code")
    if code not in SUPPORT_CODES:
        _fail(f"{path}.code", f"unsupported support diagnostic code {code!r}")

    expected_code = {
        "native-known": "NATIVE-SUPPORT-001",
        "native-typed": "NATIVE-SUPPORT-002",
        "semantically-adapted": "NATIVE-SUPPORT-003",
        "executable-safe": "NATIVE-SUPPORT-004",
        "unsupported": "NATIVE-SUPPORT-005",
    }[state]
    if code != expected_code:
        _fail(
            f"{path}.code",
            f"state {state!r} requires {expected_code}, got {code!r}",
        )

    severity = _string(item["severity"], f"{path}.severity")
    if severity not in DIAGNOSTIC_SEVERITIES:
        _fail(f"{path}.severity", f"unsupported severity {severity!r}")

    _string(item["message"], f"{path}.message")


def validate_snapshot(
    snapshot: Any,
    *,
    source: str = "<snapshot>",
) -> dict[str, Any]:
    root = _mapping(snapshot, source)
    _exact_keys(root, TOP_LEVEL_FIELDS, source)

    version = root["schema_version"]
    if type(version) is not int or version != SCHEMA_VERSION:
        _fail(
            f"{source}.schema_version",
            f"expected integer {SCHEMA_VERSION}, got {version!r}",
        )

    python = _string(root["python"], f"{source}.python")
    if not _VERSION.fullmatch(python):
        _fail(f"{source}.python", "must be a major.minor.patch version")

    platform = _string(root["platform"], f"{source}.platform")
    if platform not in PLATFORMS:
        _fail(f"{source}.platform", f"unsupported platform {platform!r}")

    fixtures = _mapping(root["fixtures"], f"{source}.fixtures")
    actual_fixtures = set(fixtures)
    missing = sorted(FIXTURE_NAMES - actual_fixtures)
    extra = sorted(actual_fixtures - FIXTURE_NAMES)
    if missing:
        _fail(f"{source}.fixtures", f"missing fixtures: {', '.join(missing)}")
    if extra:
        _fail(f"{source}.fixtures", f"extra fixtures: {', '.join(extra)}")

    for name in sorted(FIXTURE_NAMES):
        path = f"{source}.fixtures.{name}"
        fixture = _mapping(fixtures[name], path)
        _exact_keys(fixture, FIXTURE_FIELDS, path)

        diagnostics = _list(fixture["diagnostics"], f"{path}.diagnostics")
        if not diagnostics:
            _fail(f"{path}.diagnostics", "must contain at least one diagnostic")
        for index, diagnostic in enumerate(diagnostics):
            _validate_diagnostic(diagnostic, f"{path}.diagnostics[{index}]")

        support_diagnostics = _list(
            fixture["support_diagnostics"],
            f"{path}.support_diagnostics",
        )
        if not support_diagnostics:
            _fail(
                f"{path}.support_diagnostics",
                "must contain at least one support diagnostic",
            )
        for index, diagnostic in enumerate(support_diagnostics):
            _validate_support_diagnostic(
                diagnostic,
                f"{path}.support_diagnostics[{index}]",
            )

        states = _list(
            fixture["support_state_sequence"],
            f"{path}.support_state_sequence",
        )
        for index, state in enumerate(states):
            state_text = _string(state, f"{path}.support_state_sequence[{index}]")
            if state_text not in SUPPORT_STATES:
                _fail(
                    f"{path}.support_state_sequence[{index}]",
                    f"unsupported state {state_text!r}",
                )

        support_states = [item["state"] for item in support_diagnostics]
        if support_states != states:
            _fail(
                path,
                "support_state_sequence must exactly match "
                "support_diagnostics[*].state",
            )

            if states[-1] != "unsupported":
            _fail(
                path,
                "support_state_sequence must terminate in unsupported",
            )

        artifact_hash = _string(
            fixture["artifact_sha256"],
            f"{path}.artifact_sha256",
        )
        if not _HEX64.fullmatch(artifact_hash):
            _fail(
                f"{path}.artifact_sha256",
                "must be a 64-character lowercase SHA-256 digest",
            )

    return dict(root)
