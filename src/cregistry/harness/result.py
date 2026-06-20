"""Harness result types and the check registry (Section 7, VH-OUTPUT-1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Status(str, Enum):
    passed = "pass"
    failed = "fail"
    skipped = "skip"


@dataclass
class CheckResult:
    """Outcome of a single VH-* check.

    ``check`` is the canonical requirement id (e.g. "VH-SCHEMA-1") so the JSON
    output traces directly back to the spec. ``skip`` is for genuinely
    unavailable preconditions (e.g. conftest not installed) and never fails the
    run, but is reported with a reason.
    """

    section: str
    check: str
    status: Status
    message: str
    details: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "section": self.section,
            "check": self.check,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
        }

    @classmethod
    def ok(cls, section: str, check: str, message: str, details: list[dict] | None = None) -> "CheckResult":
        return cls(section, check, Status.passed, message, details or [])

    @classmethod
    def fail(cls, section: str, check: str, message: str, details: list[dict] | None = None) -> "CheckResult":
        return cls(section, check, Status.failed, message, details or [])

    @classmethod
    def skip(cls, section: str, check: str, message: str, details: list[dict] | None = None) -> "CheckResult":
        return cls(section, check, Status.skipped, message, details or [])
