"""Native GoalSpan contracts derived from the checked-in AIRef command schema."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .ir import GoalRole, GoalSpanKind, GoalSpanRequest, StorageRequestId
from .primitives.native_schema import NativeCommandRegistry, load_default_native_schema
from .runtime_binding import NativeParameterContract, NativeParameterKind, NativeStorageContract


_RANGE_RE = re.compile(r"(\d+)\s+to\s+(\d+)")
_WIDTH_RE = re.compile(r"first of\s+(\d+)\s+consecutive goals")


@dataclass(frozen=True)
class StorageContractCatalog:
    contracts: tuple[NativeStorageContract, ...]

    def get(self, contract_id: str) -> NativeStorageContract | None:
        return next((contract for contract in self.contracts if contract.contract_id == contract_id), None)

    def require(self, contract_id: str) -> NativeStorageContract:
        contract = self.get(contract_id)
        if contract is None:
            raise KeyError(contract_id)
        return contract


def _numeric_range(text: str) -> tuple[int | None, int | None]:
    match = _RANGE_RE.search(text)
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def _span_contracts(schema: NativeCommandRegistry) -> tuple[NativeStorageContract, ...]:
    contracts: list[NativeStorageContract] = []
    for command_name in schema.names():
        command = schema.require(command_name)
        for index, parameter in enumerate(command.parameters):
            if parameter.type != "Goal" or parameter.direction != "out":
                continue
            width_match = _WIDTH_RE.search(parameter.note)
            if width_match is None:
                continue

            width = int(width_match.group(1))
            shape = {
                2: GoalSpanKind.POINT_PAIR,
                4: GoalSpanKind.EXTENDED_4,
            }.get(width)
            if shape is None:
                continue

            start_min, start_max = _numeric_range(parameter.range)
            contracts.append(
                NativeStorageContract(
                    contract_id=f"{command_name}.{parameter.name}",
                    command=command_name,
                    parameters=(
                        NativeParameterContract(
                            index=index,
                            kind=NativeParameterKind.GOAL_SPAN_START,
                            width=width,
                            contiguous=True,
                            writes=True,
                        ),
                    ),
                    shape=shape,
                    start_min=start_min,
                    start_max=start_max,
                )
            )
    return tuple(sorted(contracts, key=lambda contract: contract.contract_id))


def default_storage_contracts(
    schema: NativeCommandRegistry | None = None,
) -> StorageContractCatalog:
    return StorageContractCatalog(
        contracts=_span_contracts(schema or load_default_native_schema())
    )


def goal_span_request(
    contract: NativeStorageContract,
    request_id: StorageRequestId,
    *,
    role: GoalRole = GoalRole.NATIVE_OUTPUT,
) -> GoalSpanRequest:
    if contract.shape is None or contract.start_min is None or contract.start_max is None:
        raise ValueError(
            f"native storage contract '{contract.contract_id}' is not a bounded GoalSpan contract"
        )
    parameter = contract.parameters[0]
    return GoalSpanRequest(
        request_id=request_id,
        width=parameter.width,
        shape=contract.shape,
        contract_id=contract.contract_id,
        start_min=contract.start_min,
        start_max=contract.start_max,
        role=role,
    )
