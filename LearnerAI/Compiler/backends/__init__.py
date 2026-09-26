"""External validation backends for LearnerAI."""

from .models import NativeDiagnostic, NativeValidationResult, ValidationStatus
from .native_aoe2 import Aoe2NativeBackend, BackendSpec

__all__ = [
    "Aoe2NativeBackend",
    "BackendSpec",
    "NativeDiagnostic",
    "NativeValidationResult",
    "ValidationStatus",
]
