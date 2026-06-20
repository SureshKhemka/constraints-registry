"""Constraint loading + structured schema-error reporting (FR-CONSTRAINT-2).

Reads authored constraint files (one constraint per YAML file) and validates them
against the schema, producing a per-constraint, per-field error report. A single
invalid constraint never aborts loading of the others (FR-CONSTRAINT-2, NFR-2);
errors are collected and returned.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import ValidationError

from .model import Constraint


@dataclass(frozen=True)
class SchemaError:
    """One schema violation, attributable to a constraint and a field (VH-SCHEMA-1)."""

    source: str
    file: str
    field: str
    message: str
    constraint_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "file": self.file,
            "constraint_id": self.constraint_id,
            "field": self.field,
            "message": self.message,
        }


@dataclass
class LoadResult:
    """Outcome of loading one source's constraints."""

    constraints: list[Constraint] = field(default_factory=list)
    errors: list[SchemaError] = field(default_factory=list)
    # Maps each loaded constraint id -> file it came from (for fixtures/policies).
    files: dict[str, str] = field(default_factory=dict)


def _field_path(loc: tuple) -> str:
    parts = [str(p) for p in loc]
    return ".".join(parts) if parts else "<root>"


def load_constraint_file(path: Path, source: str) -> tuple[Constraint | None, list[SchemaError]]:
    """Load and validate a single constraint file.

    Returns ``(constraint, [])`` on success or ``(None, [errors])`` on failure.
    Never raises for schema/parse problems — they are returned as SchemaErrors.
    """
    rel = path.name
    try:
        raw = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        return None, [SchemaError(source, rel, "<yaml>", f"YAML parse error: {exc}")]

    if not isinstance(raw, dict):
        return None, [SchemaError(source, rel, "<root>", "constraint file must be a YAML mapping")]

    probable_id = raw.get("id") if isinstance(raw.get("id"), str) else None

    try:
        constraint = Constraint.model_validate(raw)
    except ValidationError as exc:
        errors = [
            SchemaError(
                source=source,
                file=rel,
                field=_field_path(e["loc"]),
                message=e["msg"],
                constraint_id=probable_id,
            )
            for e in exc.errors()
        ]
        return None, errors

    return constraint, []


def load_source(source_name: str, source_dir: Path) -> LoadResult:
    """Load every constraint under ``<source_dir>/constraints/*.yaml``.

    Collects valid constraints and per-file schema errors independently
    (FR-CONSTRAINT-2): one bad file does not block the rest.
    """
    result = LoadResult()
    constraints_dir = source_dir / "constraints"
    if not constraints_dir.is_dir():
        result.errors.append(
            SchemaError(source_name, str(constraints_dir), "<source>", "no constraints/ directory")
        )
        return result

    for cfile in sorted(constraints_dir.glob("*.yaml")):
        constraint, errors = load_constraint_file(cfile, source_name)
        if errors:
            result.errors.extend(errors)
            continue
        assert constraint is not None
        if constraint.id in result.files:
            result.errors.append(
                SchemaError(
                    source_name,
                    cfile.name,
                    "id",
                    f"duplicate id within source: {constraint.id!r} "
                    f"(also in {result.files[constraint.id]})",
                    constraint_id=constraint.id,
                )
            )
            continue
        result.constraints.append(constraint)
        result.files[constraint.id] = cfile.name

    return result
