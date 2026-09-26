"""Errors raised at the native backend process boundary."""
from __future__ import annotations


class NativeBackendError(RuntimeError):
    """Base class for backend availability/protocol failures."""


class BackendUnavailableError(NativeBackendError):
    pass


class BackendVersionMismatchError(NativeBackendError):
    pass


class BackendProtocolError(NativeBackendError):
    pass
