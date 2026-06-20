"""Query / scoping (FR-QUERY-1/2/3, NFR-3).

Selects constraints relevant to a supplied scope and renders an agent-facing view
that includes intent, guidance, severity, deprecation status, and whether (and by
which engine) the constraint is enforced downstream.
"""

from __future__ import annotations

from .bundle import Bundle, ImportedConstraint
from .model import Scope
from .scope import scope_matches


def select(bundle: Bundle, scope: Scope) -> list[ImportedConstraint]:
    """Return only the constraints whose selectors match the scope (FR-QUERY-1)."""
    return [ic for ic in bundle.constraints if scope_matches(ic.constraint.scope, scope)]


def constraint_view(ic: ImportedConstraint) -> dict:
    """Agent-facing rendering of a constraint (FR-QUERY-3).

    Includes the fact that a constraint is enforced downstream and by which
    engine/stage, so an agent knows which constraints are hard downstream gates.
    """
    c = ic.constraint
    enforced_by = [{"engine": b.engine, "policy": b.policy} for b in c.enforcement]
    return {
        "constraint": ic.effective_id,
        "source": ic.source,
        "id": c.id,
        "title": c.title,
        "intent": c.intent,
        "category": c.category.value,
        "severity": c.severity.value,
        "scope": c.scope.model_dump(mode="json", exclude_none=True),
        "guidance": c.guidance.model_dump(mode="json", exclude_none=True),
        "owner": c.owner,
        "version": c.version,
        "deprecated": c.deprecated,
        "successor": c.successor,
        "advisory": c.is_advisory,
        "enforced": bool(c.enforcement),
        "enforced_by": enforced_by,
    }


def get_constraints(bundle: Bundle, scope: Scope) -> list[dict]:
    """FR-QUERY: scoped list of constraint views."""
    return [constraint_view(ic) for ic in select(bundle, scope)]
