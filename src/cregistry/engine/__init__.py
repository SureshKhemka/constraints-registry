"""Enforcement-engine integration (FR-ENGINE).

This package is the single, stable boundary through which enforcement engines are
integrated (FR-ENGINE-1). Adding a new engine means adding one adapter module
that implements ``EngineAdapter`` and one config line (FR-ENGINE-2/5); nothing
else in the system changes.
"""

from .interface import EngineAdapter, EngineVerdict, Verdict, Violation
from .registry import EngineRegistry, required_engines

__all__ = [
    "EngineAdapter",
    "EngineVerdict",
    "Verdict",
    "Violation",
    "EngineRegistry",
    "required_engines",
]
