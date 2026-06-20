"""VH-SCHEMA — schema conformance (VH-SCHEMA-1).

Verifies that every constraint in every configured source conforms to the
constraint schema (FR-CONSTRAINT-1), failing with a per-constraint, per-field
report on any violation.
"""

from __future__ import annotations

from ...config import RegistryConfig
from ...loader import load_source
from ..result import CheckResult

SECTION = "VH-SCHEMA"


def run(config: RegistryConfig) -> list[CheckResult]:
    errors: list[dict] = []
    total = 0
    for src in config.sources:
        src_dir = config.resolved_source_path(src)
        result = load_source(src.name, src_dir)
        total += len(result.constraints)
        errors.extend(e.to_dict() for e in result.errors)

    if errors:
        return [
            CheckResult.fail(
                SECTION,
                "VH-SCHEMA-1",
                f"{len(errors)} schema violation(s) across configured sources",
                details=errors,
            )
        ]
    return [
        CheckResult.ok(
            SECTION,
            "VH-SCHEMA-1",
            f"all {total} constraint(s) in {len(config.sources)} source(s) conform to schema",
        )
    ]
