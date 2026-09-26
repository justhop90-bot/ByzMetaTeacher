"""Canonical native-fact values and parameter normalization.

The native .per language deliberately permits several different surface
representations for the same *kind* of parameter.  AIRef documents, for
example, that BuildingId and UnitId may be supplied as a defined name, an
object ID, or a class.  The compiler therefore preserves identifier namespace
and reference form instead of collapsing everything into strings or integers.

This module is a value-normalization layer only.  It does not resolve runtime
symbols, query GameData, or prove a predicate true.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import TypeAlias

from ..primitives.native_hygiene import AIRefProvenance


class CanonicalKind(str, Enum):
    INTEGER = "INTEGER"
    ENUM = "ENUM"
    IDENTIFIER = "IDENTIFIER"
    SYMBOL = "SYMBOL"


class ParameterSemanticKind(str, Enum):
    INTEGER = "INTEGER"
    ENUM = "ENUM"
    IDENTIFIER = "IDENTIFIER"
    SYMBOL = "SYMBOL"


class IdentifierForm(str, Enum):
    NUMERIC_ID = "NUMERIC_ID"
    NAME = "NAME"
    CLASS = "CLASS"


@dataclass(frozen=True)
class CanonicalInteger:
    value: int

    @property
    def kind(self) -> CanonicalKind:
        return CanonicalKind.INTEGER


@dataclass(frozen=True)
class CanonicalEnum:
    domain: str
    value: str

    def __post_init__(self) -> None:
        if not self.domain:
            raise ValueError("canonical enum domain is required")
        if not self.value:
            raise ValueError("canonical enum value is required")

    @property
    def kind(self) -> CanonicalKind:
        return CanonicalKind.ENUM


@dataclass(frozen=True)
class CanonicalIdentifier:
    namespace: str
    form: IdentifierForm
    value: int | str

    def __post_init__(self) -> None:
        if not self.namespace:
            raise ValueError("canonical identifier namespace is required")
        if self.form is IdentifierForm.NUMERIC_ID:
            if isinstance(self.value, bool) or not isinstance(self.value, int):
                raise ValueError("numeric identifier value must be an integer")
        else:
            if not isinstance(self.value, str) or not self.value:
                raise ValueError(
                    "named/class identifier value must be a non-empty string"
                )
        if isinstance(self.value, str) and not self.value:
            raise ValueError("canonical identifier value is required")

    @property
    def kind(self) -> CanonicalKind:
        return CanonicalKind.IDENTIFIER


@dataclass(frozen=True)
class CanonicalSymbol:
    namespace: str
    name: str

    def __post_init__(self) -> None:
        if not self.namespace:
            raise ValueError("canonical symbol namespace is required")
        if not self.name:
            raise ValueError("canonical symbol name is required")

    @property
    def kind(self) -> CanonicalKind:
        return CanonicalKind.SYMBOL


CanonicalValue: TypeAlias = (
    CanonicalInteger
    | CanonicalEnum
    | CanonicalIdentifier
    | CanonicalSymbol
)



@dataclass(frozen=True)
class NormalizedFact:
    """
    Canonical semantic representation of one native fact occurrence.

    identity_key deliberately excludes provenance so repeated occurrences
    of the same semantic atom compare as the same logical fact while each
    occurrence retains its own evidence chain.
    """

    semantic_id: str
    canonical_args: tuple[CanonicalValue, ...]
    provenance: tuple[AIRefProvenance, ...]

    def __post_init__(self) -> None:
        if not self.semantic_id:
            raise ValueError("normalized fact semantic_id is required")
        if not isinstance(self.canonical_args, tuple):
            raise TypeError("normalized fact canonical_args must be a tuple")
        if not isinstance(self.provenance, tuple):
            raise TypeError("normalized fact provenance must be a tuple")
        if not self.provenance:
            raise ValueError("normalized fact provenance is required")
        for value in self.canonical_args:
            if not isinstance(
                value,
                (
                    CanonicalInteger,
                    CanonicalEnum,
                    CanonicalIdentifier,
                    CanonicalSymbol,
                ),
            ):
                raise TypeError(
                    "normalized fact canonical_args contains a non-canonical value"
                )
        for evidence in self.provenance:
            if not isinstance(evidence, AIRefProvenance):
                raise TypeError(
                    "normalized fact provenance contains invalid evidence"
                )

    @property
    def identity_key(self) -> tuple[str, tuple[CanonicalValue, ...]]:
        """
        Stable logical identity.

        Semantic provenance is intentionally excluded. It describes the
        evidence supporting this occurrence, not the identity of the atom.
        """
        return self.semantic_id, self.canonical_args


@dataclass(frozen=True)
class EnumNormalization:
    domain: str
    members: tuple[str, ...]
    aliases: tuple[tuple[str, str], ...] = ()
    case_sensitive: bool = False

    def __post_init__(self) -> None:
        if not self.domain:
            raise ValueError("enum normalization domain is required")
        if not self.members:
            raise ValueError(f"enum domain '{self.domain}' requires members")

        canonical_members = tuple(
            self._normalize_text(member) for member in self.members
        )
        if len(canonical_members) != len(set(canonical_members)):
            raise ValueError(
                f"enum domain '{self.domain}' contains duplicate members"
            )

        alias_keys = set()
        for source, target in self.aliases:
            source_key = self._normalize_text(source)
            target_key = self._normalize_text(target)
            if source_key in alias_keys:
                raise ValueError(
                    f"enum domain '{self.domain}' contains duplicate alias '{source}'"
                )
            if target_key not in canonical_members:
                raise ValueError(
                    f"enum alias '{source}' targets unknown member '{target}'"
                )
            alias_keys.add(source_key)

    def _normalize_text(self, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("enum values must be strings")
        normalized = value.strip()
        if not normalized:
            raise ValueError("enum values cannot be empty")
        return normalized if self.case_sensitive else normalized.upper()

    def canonicalize(self, value: object) -> CanonicalEnum:
        if isinstance(value, Enum):
            raw = value.value
        else:
            raw = value

        if not isinstance(raw, str):
            raise ValueError(
                f"value {value!r} is not a valid enum member for '{self.domain}'"
            )

        key = self._normalize_text(raw)
        aliases = {
            self._normalize_text(source): self._normalize_text(target)
            for source, target in self.aliases
        }
        target = aliases.get(key, key)

        members = {
            self._normalize_text(member)
            for member in self.members
        }
        if target not in members:
            raise ValueError(
                f"value '{raw}' is not a member of enum domain '{self.domain}'"
            )

        return CanonicalEnum(self.domain, target)


@dataclass(frozen=True)
class IdentifierNormalization:
    namespace: str
    accepted_forms: tuple[IdentifierForm, ...]
    names: tuple[str, ...] = ()
    classes: tuple[str, ...] = ()
    aliases: tuple[tuple[str, str, IdentifierForm], ...] = ()
    case_sensitive: bool = False
    allow_numeric_strings: bool = False
    minimum_numeric_id: int | None = None
    maximum_numeric_id: int | None = None

    def __post_init__(self) -> None:
        if not self.namespace:
            raise ValueError("identifier namespace is required")
        if not self.accepted_forms:
            raise ValueError(
                f"identifier namespace '{self.namespace}' requires accepted forms"
            )
        if len(self.accepted_forms) != len(set(self.accepted_forms)):
            raise ValueError(
                f"identifier namespace '{self.namespace}' has duplicate forms"
            )
        if (
            IdentifierForm.NAME in self.accepted_forms
            and not self.names
            and not any(form is IdentifierForm.NAME for _, _, form in self.aliases)
        ):
            raise ValueError(
                f"identifier namespace '{self.namespace}' accepts NAME "
                "but defines no names"
            )
        if (
            IdentifierForm.CLASS in self.accepted_forms
            and not self.classes
            and not any(form is IdentifierForm.CLASS for _, _, form in self.aliases)
        ):
            raise ValueError(
                f"identifier namespace '{self.namespace}' accepts CLASS "
                "but defines no classes"
            )
        if self.minimum_numeric_id is not None and self.maximum_numeric_id is not None:
            if self.minimum_numeric_id > self.maximum_numeric_id:
                raise ValueError("identifier numeric bounds are inverted")

        seen_aliases: set[tuple[str, IdentifierForm]] = set()
        name_values = {
            self._normalize_text(value)
            for value in self.names
        }
        class_values = {
            self._normalize_text(value)
            for value in self.classes
        }
        if name_values & class_values:
            overlap = sorted(name_values & class_values)[0]
            raise ValueError(
                f"identifier '{self.namespace}' is ambiguous between NAME and CLASS: "
                f"'{overlap}'"
            )

        for source, target, form in self.aliases:
            if form not in self.accepted_forms:
                raise ValueError(
                    f"identifier alias '{source}' uses unaccepted form '{form.value}'"
                )
            key = (self._normalize_text(source), form)
            if key in seen_aliases:
                raise ValueError(
                    f"duplicate identifier alias '{source}' for form '{form.value}'"
                )
            seen_aliases.add(key)
            target_key = self._normalize_text(target)
            if form is IdentifierForm.NAME and target_key not in name_values:
                raise ValueError(
                    f"identifier alias '{source}' targets unknown name '{target}'"
                )
            if form is IdentifierForm.CLASS and target_key not in class_values:
                raise ValueError(
                    f"identifier alias '{source}' targets unknown class '{target}'"
                )

    def _normalize_text(self, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("identifier names/classes must be strings")
        normalized = value.strip()
        if not normalized:
            raise ValueError("identifier names/classes cannot be empty")
        return normalized if self.case_sensitive else normalized.lower()

    def canonicalize(self, value: object) -> CanonicalIdentifier:
        if isinstance(value, bool):
            raise ValueError(
                f"boolean is not a valid identifier in namespace '{self.namespace}'"
            )

        if isinstance(value, int):
            if IdentifierForm.NUMERIC_ID not in self.accepted_forms:
                raise ValueError(
                    f"numeric identifier form is not accepted by '{self.namespace}'"
                )
            self._validate_numeric_id(value)
            return CanonicalIdentifier(
                self.namespace,
                IdentifierForm.NUMERIC_ID,
                value,
            )

        if not isinstance(value, str):
            raise ValueError(
                f"value {value!r} is not a valid identifier in namespace "
                f"'{self.namespace}'"
            )

        raw = value.strip()
        if not raw:
            raise ValueError("identifier text cannot be empty")

        if (
            self.allow_numeric_strings
            and re.fullmatch(r"[+-]?\d+", raw)
            and IdentifierForm.NUMERIC_ID in self.accepted_forms
        ):
            numeric = int(raw, 10)
            self._validate_numeric_id(numeric)
            return CanonicalIdentifier(
                self.namespace,
                IdentifierForm.NUMERIC_ID,
                numeric,
            )

        key = self._normalize_text(raw)
        aliases = {
            (self._normalize_text(source), form): self._normalize_text(target)
            for source, target, form in self.aliases
        }

        candidates: list[CanonicalIdentifier] = []
        if IdentifierForm.NAME in self.accepted_forms:
            target = aliases.get((key, IdentifierForm.NAME), key)
            name_values = {
                self._normalize_text(item) for item in self.names
            }
            if target in name_values:
                candidates.append(
                    CanonicalIdentifier(
                        self.namespace,
                        IdentifierForm.NAME,
                        target,
                    )
                )

        if IdentifierForm.CLASS in self.accepted_forms:
            target = aliases.get((key, IdentifierForm.CLASS), key)
            class_values = {
                self._normalize_text(item) for item in self.classes
            }
            if target in class_values:
                candidates.append(
                    CanonicalIdentifier(
                        self.namespace,
                        IdentifierForm.CLASS,
                        target,
                    )
                )

        if len(candidates) > 1:
            raise ValueError(
                f"identifier '{raw}' is ambiguous in namespace '{self.namespace}'"
            )
        if not candidates:
            raise ValueError(
                f"value '{raw}' is not a declared identifier in namespace "
                f"'{self.namespace}'"
            )
        return candidates[0]

    def _validate_numeric_id(self, value: int) -> None:
        if self.minimum_numeric_id is not None and value < self.minimum_numeric_id:
            raise ValueError(
                f"identifier '{self.namespace}' must be >= {self.minimum_numeric_id}"
            )
        if self.maximum_numeric_id is not None and value > self.maximum_numeric_id:
            raise ValueError(
                f"identifier '{self.namespace}' must be <= {self.maximum_numeric_id}"
            )


@dataclass(frozen=True)
class SymbolNormalization:
    namespace: str
    case_sensitive: bool = True
    allowed_names: tuple[str, ...] = ()
    aliases: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.namespace:
            raise ValueError("symbol namespace is required")
        if len(self.allowed_names) != len(set(self.allowed_names)):
            raise ValueError(
                f"symbol namespace '{self.namespace}' has duplicate names"
            )
        allowed = {
            self._normalize_text(name)
            for name in self.allowed_names
        }
        for source, target in self.aliases:
            if self._normalize_text(target) not in allowed:
                raise ValueError(
                    f"symbol alias '{source}' targets unknown symbol '{target}'"
                )

    def _normalize_text(self, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("symbol names must be strings")
        normalized = value.strip()
        if not normalized:
            raise ValueError("symbol names cannot be empty")
        return normalized if self.case_sensitive else normalized.lower()

    def canonicalize(self, value: object) -> CanonicalSymbol:
        if not isinstance(value, str):
            raise ValueError(
                f"value {value!r} is not a valid symbol in namespace "
                f"'{self.namespace}'"
            )

        key = self._normalize_text(value)
        aliases = {
            self._normalize_text(source): self._normalize_text(target)
            for source, target in self.aliases
        }
        key = aliases.get(key, key)

        if self.allowed_names:
            allowed = {
                self._normalize_text(name)
                for name in self.allowed_names
            }
            if key not in allowed:
                raise ValueError(
                    f"symbol '{value}' is not declared in namespace "
                    f"'{self.namespace}'"
                )

        return CanonicalSymbol(self.namespace, key)


@dataclass(frozen=True)
class CanonicalizationContext:
    parameter_name: str
    kind: ParameterSemanticKind
    enum_spec: EnumNormalization | None = None
    identifier_spec: IdentifierNormalization | None = None
    symbol_spec: SymbolNormalization | None = None
    minimum: int | None = None
    maximum: int | None = None

    def __post_init__(self) -> None:
        if not self.parameter_name:
            raise ValueError("parameter_name is required")

        selected = {
            ParameterSemanticKind.ENUM: self.enum_spec,
            ParameterSemanticKind.IDENTIFIER: self.identifier_spec,
            ParameterSemanticKind.SYMBOL: self.symbol_spec,
        }

        if self.kind is ParameterSemanticKind.INTEGER:
            if any(contract is not None for contract in (self.enum_spec, self.identifier_spec, self.symbol_spec)):
                raise ValueError("integer context cannot carry enum/identifier/symbol contracts")
        else:
            contract = selected[self.kind]
            if contract is None:
                raise ValueError(
                    f"{self.kind.value} context requires its normalization contract"
                )

        if self.minimum is not None and self.maximum is not None:
            if self.minimum > self.maximum:
                raise ValueError("integer bounds are inverted")

    @classmethod
    def integer(
        cls,
        *,
        parameter_name: str,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> "CanonicalizationContext":
        return cls(
            parameter_name=parameter_name,
            kind=ParameterSemanticKind.INTEGER,
            minimum=minimum,
            maximum=maximum,
        )

    @classmethod
    def enum(
        cls,
        *,
        parameter_name: str,
        domain: str,
        members: tuple[str, ...],
        aliases: tuple[tuple[str, str], ...] = (),
        case_sensitive: bool = False,
    ) -> "CanonicalizationContext":
        return cls(
            parameter_name=parameter_name,
            kind=ParameterSemanticKind.ENUM,
            enum_spec=EnumNormalization(
                domain=domain,
                members=members,
                aliases=aliases,
                case_sensitive=case_sensitive,
            ),
        )

    @classmethod
    def identifier(
        cls,
        *,
        parameter_name: str,
        namespace: str,
        accepted_forms: tuple[IdentifierForm, ...],
        names: tuple[str, ...] = (),
        classes: tuple[str, ...] = (),
        aliases: tuple[tuple[str, str, IdentifierForm], ...] = (),
        case_sensitive: bool = False,
        allow_numeric_strings: bool = False,
        minimum_numeric_id: int | None = None,
        maximum_numeric_id: int | None = None,
    ) -> "CanonicalizationContext":
        return cls(
            parameter_name=parameter_name,
            kind=ParameterSemanticKind.IDENTIFIER,
            identifier_spec=IdentifierNormalization(
                namespace=namespace,
                accepted_forms=accepted_forms,
                names=names,
                classes=classes,
                aliases=aliases,
                case_sensitive=case_sensitive,
                allow_numeric_strings=allow_numeric_strings,
                minimum_numeric_id=minimum_numeric_id,
                maximum_numeric_id=maximum_numeric_id,
            ),
        )

    @classmethod
    def symbol(
        cls,
        *,
        parameter_name: str,
        namespace: str,
        case_sensitive: bool = True,
        allowed_names: tuple[str, ...] = (),
        aliases: tuple[tuple[str, str], ...] = (),
    ) -> "CanonicalizationContext":
        return cls(
            parameter_name=parameter_name,
            kind=ParameterSemanticKind.SYMBOL,
            symbol_spec=SymbolNormalization(
                namespace=namespace,
                case_sensitive=case_sensitive,
                allowed_names=allowed_names,
                aliases=aliases,
            ),
        )


def canonicalize_value(
    value: object,
    context: CanonicalizationContext,
) -> CanonicalValue:
    if context.kind is ParameterSemanticKind.INTEGER:
        if isinstance(value, bool):
            raise ValueError(
                f"boolean is not a valid integer for parameter "
                f"'{context.parameter_name}'"
            )

        if isinstance(value, int):
            normalized = value
        elif isinstance(value, str) and re.fullmatch(r"[+-]?\d+", value.strip()):
            normalized = int(value.strip(), 10)
        else:
            raise ValueError(
                f"value {value!r} is not a valid integer for parameter "
                f"'{context.parameter_name}'"
            )

        if context.minimum is not None and normalized < context.minimum:
            raise ValueError(
                f"parameter '{context.parameter_name}' must be >= {context.minimum}"
            )
        if context.maximum is not None and normalized > context.maximum:
            raise ValueError(
                f"parameter '{context.parameter_name}' must be <= {context.maximum}"
            )
        return CanonicalInteger(normalized)

    if context.kind is ParameterSemanticKind.ENUM:
        assert context.enum_spec is not None
        return context.enum_spec.canonicalize(value)

    if context.kind is ParameterSemanticKind.IDENTIFIER:
        assert context.identifier_spec is not None
        return context.identifier_spec.canonicalize(value)

    if context.kind is ParameterSemanticKind.SYMBOL:
        assert context.symbol_spec is not None
        return context.symbol_spec.canonicalize(value)

    raise ValueError(
        f"unsupported canonicalization kind '{context.kind.value}'"
    )


__all__ = [
    "CanonicalEnum",
    "CanonicalIdentifier",
    "CanonicalInteger",
    "CanonicalKind",
    "CanonicalSymbol",
    "CanonicalValue",
    "NormalizedFact",
    "CanonicalizationContext",
    "EnumNormalization",
    "IdentifierForm",
    "IdentifierNormalization",
    "ParameterSemanticKind",
    "SymbolNormalization",
    "canonicalize_value",
]
