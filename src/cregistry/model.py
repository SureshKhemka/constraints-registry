"""Constraint data model (FR-CONSTRAINT-1, FR-VERSION-1/4).

This module defines the authored constraint schema. It is the single source of
truth for what a constraint *is*; per FR-ENGINE-2 it must NOT change when a new
enforcement engine is added (engines are referenced only by an opaque locator in
``EnforcementBinding``).

Schema validation is performed by Pydantic v2, which yields per-field errors so
that import (FR-CONSTRAINT-2) and the harness (VH-SCHEMA-1) can report exactly
which constraint and which field failed.
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Semantic version, per https://semver.org (FR-VERSION-1).
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-(?:[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+(?:[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


class Category(str, Enum):
    """FR-CONSTRAINT-1 ``category`` — exactly these three values."""

    infrastructure = "infrastructure"
    organizational = "organizational"
    architectural = "architectural"


class Severity(str, Enum):
    """FR-CONSTRAINT-1 ``severity`` — exactly these three values.

    Ordering (hard > soft > advisory) backs the default precedence policy
    (FR-NAMESPACE-2); see ``rank``.
    """

    hard = "hard"
    soft = "soft"
    advisory = "advisory"

    @property
    def rank(self) -> int:
        return {"hard": 2, "soft": 1, "advisory": 0}[self.value]


class _Strict(BaseModel):
    """Base model: unknown fields are rejected as schema errors (FR-CONSTRAINT-2)."""

    model_config = ConfigDict(extra="forbid")


class Endpoint(_Strict):
    """One side of a relationship-style architectural selector (FR-CONSTRAINT-1 scope).

    Supports a layer/component identity plus a domain, and the relational
    modifier ``different_domain`` (target domain differs from source domain),
    mirroring the spec's illustrative architectural constraint.
    """

    layer: str | None = None
    component: str | None = None
    domain: str | None = None
    different_domain: bool | None = None


class Relationship(_Strict):
    """Relationship-style selector for architectural constraints (FR-CONSTRAINT-1).

    Captures a source component, a target component, and a boundary/layer +
    interaction kind, rather than only single-resource attributes.
    """

    source: Endpoint | None = None
    target: Endpoint | None = None
    boundary: str | None = None
    interaction: str | None = None


class Scope(_Strict):
    """Selectors that determine when a constraint is relevant (FR-CONSTRAINT-1).

    Single-resource attribute selectors (providers/resource_types/environments/
    repos) AND relationship-style selectors (FR-CONSTRAINT-1, FR-QUERY-2).
    """

    providers: list[str] = Field(default_factory=list)
    resource_types: list[str] = Field(default_factory=list)
    environments: list[str] = Field(default_factory=list)
    repos: list[str] = Field(default_factory=list)
    relationship: Relationship | None = None


class EnforcementBinding(_Strict):
    """A reference to an external engine + policy (FR-CONSTRAINT-3, FR-ENGINE).

    The registry references the policy by locator only; it does NOT copy the
    enforcement logic. ``engine`` selects an adapter (FR-ENGINE-5); ``policy`` is
    an opaque locator interpreted by that adapter.
    """

    engine: str
    policy: str


class Guidance(_Strict):
    """Agent-facing guidance (FR-CONSTRAINT-1 ``guidance``).

    MUST support do/dont rules and at least one compliant example; SHOULD support
    a non-compliant example.
    """

    do: list[str] = Field(default_factory=list)
    dont: list[str] = Field(default_factory=list)
    example_compliant: str = Field(min_length=1)
    example_noncompliant: str | None = None


class Fixtures(_Strict):
    """Optional pass/fail fixture references (FR-CONSTRAINT-1, FR-INTEGRITY-1).

    ``pass`` is a Python keyword, so it is exposed via the ``pass_`` attribute
    with the YAML/JSON alias ``pass``.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    pass_: str | None = Field(default=None, alias="pass")
    fail: str | None = None


class Constraint(_Strict):
    """A single governance rule (FR-CONSTRAINT-1).

    This is the authored shape (as written in a source repo). Provenance
    (source namespace, effective id) is attached at import time, not here.
    """

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    intent: str = Field(min_length=1)
    category: Category
    scope: Scope = Field(default_factory=Scope)
    severity: Severity
    enforcement: list[EnforcementBinding] = Field(default_factory=list)
    guidance: Guidance
    owner: str = Field(min_length=1)
    fixtures: Fixtures | None = None
    version: str
    # FR-VERSION-4: deprecation with optional successor reference.
    deprecated: bool = False
    successor: str | None = None

    @field_validator("version")
    @classmethod
    def _check_semver(cls, v: str) -> str:
        if not _SEMVER_RE.match(v):
            raise ValueError(f"not a semantic version: {v!r}")
        return v

    @property
    def is_advisory(self) -> bool:
        """An advisory constraint has zero enforcement bindings (FR-CONSTRAINT-1)."""
        return len(self.enforcement) == 0
