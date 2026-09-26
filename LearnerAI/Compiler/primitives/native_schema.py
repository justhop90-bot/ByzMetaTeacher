"""Checked-in AIRef native command schema loader.

Metadata only. This module does not parse .per or assign Basilisk semantic roles.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path


@dataclass(frozen=True)
class NativeParameterSpec:
    name: str
    type: str
    direction: str
    range: str
    note: str


@dataclass(frozen=True)
class NativeCommandSpec:
    name: str
    version: str
    command_type: str
    parameters: tuple[NativeParameterSpec, ...]

    @property
    def parameter_count(self) -> int:
        return len(self.parameters)


class NativeCommandRegistry:
    def __init__(
        self,
        commands: tuple[NativeCommandSpec, ...],
        *,
        source_blob_sha: str,
        command_count: int,
    ):
        self._items = {command.name: command for command in commands}
        self.source_blob_sha = source_blob_sha
        self.command_count = command_count

    @classmethod
    def from_path(cls, path: Path) -> "NativeCommandRegistry":
        raw = json.loads(path.read_text(encoding="utf-8"))
        metadata = raw.get("metadata", {})
        commands = raw.get("commands", [])
        if not isinstance(commands, list) or not commands:
            raise ValueError("AIRef command schema contains no commands")

        source_blob_sha = metadata.get("source_commands_js_blob_sha") or metadata.get("source_blob_sha")
        if not isinstance(source_blob_sha, str) or not source_blob_sha:
            raise ValueError("AIRef command schema is missing its source blob SHA")

        expected_count = metadata.get(
            "covered_command_count",
            metadata.get("ai_ref_command_count"),
        )
        if not isinstance(expected_count, int) or expected_count != len(commands):
            raise ValueError(
                "AIRef command schema count mismatch: "
                f"metadata={expected_count}, commands={len(commands)}"
            )

        specs: list[NativeCommandSpec] = []
        seen: set[str] = set()
        for entry in commands:
            name = entry.get("name")
            if not isinstance(name, str) or not name:
                raise ValueError("AIRef command schema contains a command without a name")
            if name in seen:
                raise ValueError(f"duplicate AIRef command '{name}'")
            seen.add(name)

            parameters = tuple(
                NativeParameterSpec(
                    name=str(parameter.get("name", "")),
                    type=str(parameter.get("type", "")),
                    direction=str(parameter.get("dir", "")),
                    range=str(parameter.get("range", "")),
                    note=str(parameter.get("note", "")),
                )
                for parameter in entry.get("parameters", [])
            )
            specs.append(
                NativeCommandSpec(
                    name=name,
                    version=str(entry.get("version", "")),
                    command_type=str(entry.get("command_type", "")),
                    parameters=parameters,
                )
            )

        return cls(
            tuple(specs),
            source_blob_sha=source_blob_sha,
            command_count=expected_count,
        )

    def get(self, name: str) -> NativeCommandSpec | None:
        return self._items.get(name)

    def require(self, name: str) -> NativeCommandSpec:
        item = self.get(name)
        if item is None:
            raise KeyError(name)
        return item

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._items))


@lru_cache(maxsize=1)
def load_default_native_schema() -> NativeCommandRegistry:
    repo_root = Path(__file__).resolve().parents[3]
    return NativeCommandRegistry.from_path(
        repo_root
        / "docs"
        / "reference"
        / "inventories"
        / "airef-command-schema.json"
    )
