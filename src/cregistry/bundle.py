"""Bundle model (FR-VERSION-2, FR-NAMESPACE-1, FR-SOURCE-4).

A Bundle is an immutable, versioned, aggregated snapshot of all imported
constraints. Its identifier is a content hash, which gives determinism
(FR-SOURCE-3 / NFR-1): identical inputs produce an identical bundle id.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .model import Constraint


@dataclass(frozen=True)
class ImportedConstraint:
    """A constraint plus its provenance (FR-SOURCE-4) and namespace (FR-NAMESPACE-1)."""

    source: str
    constraint: Constraint

    @property
    def effective_id(self) -> str:
        """Namespaced identifier = source namespace + id (FR-NAMESPACE-1)."""
        return f"{self.source}/{self.constraint.id}"

    def to_dict(self) -> dict:
        return {
            "effective_id": self.effective_id,
            "source": self.source,
            "constraint": self.constraint.model_dump(mode="json", by_alias=True),
        }


def _canonical_blob(constraints: list[ImportedConstraint]) -> str:
    payload = [ic.to_dict() for ic in sorted(constraints, key=lambda ic: ic.effective_id)]
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class Bundle:
    """An immutable, versioned aggregate snapshot (FR-VERSION-2)."""

    bundle_id: str
    constraints: list[ImportedConstraint]
    # Precedence decisions recorded at import (FR-NAMESPACE-2); populated in the
    # precedence step. Each entry is a JSON-serialisable record.
    precedence: list[dict] = field(default_factory=list)

    @classmethod
    def from_constraints(
        cls, constraints: list[ImportedConstraint], precedence: list[dict] | None = None
    ) -> "Bundle":
        bundle_id = "sha256:" + hashlib.sha256(_canonical_blob(constraints).encode()).hexdigest()
        return cls(
            bundle_id=bundle_id,
            constraints=sorted(constraints, key=lambda ic: ic.effective_id),
            precedence=precedence or [],
        )

    def get(self, effective_id: str) -> ImportedConstraint | None:
        return next((c for c in self.constraints if c.effective_id == effective_id), None)

    def to_dict(self) -> dict:
        return {
            "bundle_id": self.bundle_id,
            "constraints": [c.to_dict() for c in self.constraints],
            "precedence": self.precedence,
        }
