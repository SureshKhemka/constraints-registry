"""Import / aggregation pipeline (FR-SOURCE-1/2/3/4, FR-NAMESPACE-1, NFR-1/2).

Loads constraints from the configured sources, validates each (delegating to
``loader``), namespaces and records provenance, resolves precedence
(FR-NAMESPACE-2, see ``precedence``), and produces a deterministic, immutable
versioned bundle (FR-VERSION-2). A malformed constraint is reported but does not
prevent valid constraints from importing (FR-CONSTRAINT-2, NFR-2).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field

from .bundle import Bundle, ImportedConstraint
from .config import RegistryConfig, load_config
from .loader import SchemaError, load_source
from .precedence import Conflict, resolve_precedence


@dataclass
class ImportReport:
    """Structured, machine-readable import result (NFR-4)."""

    bundle: Bundle
    schema_errors: list[SchemaError] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        # Schema errors are isolated (the rest still imports), but an unresolvable
        # precedence conflict is a hard import error (FR-NAMESPACE-3).
        return len(self.conflicts) == 0

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "bundle_id": self.bundle.bundle_id,
            "constraint_count": len(self.bundle.constraints),
            "schema_errors": [e.to_dict() for e in self.schema_errors],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "precedence": self.bundle.precedence,
        }


def import_sources(config: RegistryConfig) -> ImportReport:
    imported: list[ImportedConstraint] = []
    schema_errors: list[SchemaError] = []

    for src in config.sources:
        src_dir = config.resolved_source_path(src)
        result = load_source(src.name, src_dir)
        schema_errors.extend(result.errors)
        for constraint in result.constraints:
            imported.append(ImportedConstraint(source=src.name, constraint=constraint))

    precedence_records, conflicts = resolve_precedence(imported, config)
    bundle = Bundle.from_constraints(imported, precedence_records)
    return ImportReport(bundle=bundle, schema_errors=schema_errors, conflicts=conflicts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import sources into a constraint bundle")
    parser.add_argument("--config", default="registry.config.yaml")
    parser.add_argument("--emit-bundle", action="store_true", help="print the full bundle JSON")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    report = import_sources(config)
    out = report.to_dict()
    if args.emit_bundle:
        out["bundle"] = report.bundle.to_dict()
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
