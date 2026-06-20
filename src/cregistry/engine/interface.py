"""The stable engine interface (FR-ENGINE-1/3).

This is *layer 1* of the normalized result schema: what an engine knows. An
adapter returns only ``EngineVerdict`` / ``Violation`` — it carries no
constraint-level concepts (severity, deprecation, advisory). The orchestrator
wraps these into the constraint-level report (layer 2, see ``validate``). Keeping
the layers separate is what lets the conformance suite (VH-ENGINE-2) test any
adapter in isolation and keeps the FR-ENGINE-2 boundary clean.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..model import EnforcementBinding


class Verdict(str, Enum):
    passed = "pass"
    failed = "fail"
    error = "error"  # engine could not run (e.g. policy missing/unparseable)


@dataclass(frozen=True)
class Violation:
    """A single normalized finding (engine-agnostic).

    ``message`` is required; everything else is what an engine *may* be able to
    report. ``raw`` retains the engine-native record for debugging but is treated
    as opaque by the core (never parsed). ``remediation`` is optional; the engine
    may set it, otherwise the orchestrator fills it from the constraint guidance.
    """

    message: str
    rule: str | None = None
    resource: str | None = None
    path: str | None = None
    raw: Any | None = None
    remediation: str | None = None

    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "rule": self.rule,
            "resource": self.resource,
            "path": self.path,
            "raw": self.raw,
            "remediation": self.remediation,
        }


@dataclass(frozen=True)
class EngineVerdict:
    """Structured verdict for one (artifact, policy) evaluation (FR-ENGINE-3)."""

    verdict: Verdict
    engine: str
    policy: str
    error: str | None = None
    violations: list[Violation] = field(default_factory=list)

    @property
    def is_pass(self) -> bool:
        return self.verdict is Verdict.passed

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict.value,
            "engine": self.engine,
            "policy": self.policy,
            "error": self.error,
            "violations": [v.to_dict() for v in self.violations],
        }

    @classmethod
    def passed_(cls, engine: str, policy: str) -> "EngineVerdict":
        return cls(Verdict.passed, engine, policy)

    @classmethod
    def failed_(cls, engine: str, policy: str, violations: list[Violation]) -> "EngineVerdict":
        return cls(Verdict.failed, engine, policy, violations=violations)

    @classmethod
    def errored(cls, engine: str, policy: str, message: str) -> "EngineVerdict":
        return cls(Verdict.error, engine, policy, error=message)


class EngineAdapter(ABC):
    """The contract every enforcement engine implements (FR-ENGINE-1/2/3).

    Implementations live under ``engine/adapters`` and are loaded by config
    (FR-ENGINE-5). Implementing this interface is the *only* code needed to add
    an engine (FR-ENGINE-2).
    """

    #: Engine name used to match enforcement bindings and config entries.
    name: str

    @abstractmethod
    def can_handle(self, binding: EnforcementBinding) -> bool:
        """(a) Can this adapter handle the given enforcement binding? (FR-ENGINE-3a)"""

    @abstractmethod
    def evaluate(self, artifact: Any, policy: str) -> EngineVerdict:
        """(b) Evaluate ``artifact`` against the referenced ``policy`` and return a
        structured pass/fail verdict with violation details (FR-ENGINE-3b).

        ``policy`` is a resolved locator (for file-based engines, an absolute
        path). Must never raise for an unrunnable policy — return a Verdict.error
        verdict instead (NFR-2)."""
