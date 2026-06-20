"""VH-IMPORT — import and aggregation (VH-IMPORT-1, VH-IMPORT-2).

VH-IMPORT-1: import is deterministic (FR-SOURCE-3) — two runs over identical
inputs produce equivalent bundles.
VH-IMPORT-2: a deliberately malformed constraint is rejected while valid
constraints from other sources still import (FR-CONSTRAINT-2, NFR-2).
"""

from __future__ import annotations

from ...config import RegistryConfig, SourceConfig
from ...importer import import_sources
from ..result import CheckResult

SECTION = "VH-IMPORT"


def _determinism(config: RegistryConfig) -> CheckResult:
    r1 = import_sources(config)
    r2 = import_sources(config)
    if r1.bundle.bundle_id == r2.bundle.bundle_id and r1.bundle.to_dict() == r2.bundle.to_dict():
        return CheckResult.ok(
            SECTION,
            "VH-IMPORT-1",
            f"two imports produced an equivalent bundle ({r1.bundle.bundle_id})",
        )
    return CheckResult.fail(
        SECTION,
        "VH-IMPORT-1",
        "import is not deterministic: bundles differ across runs",
        details=[{"run1": r1.bundle.bundle_id, "run2": r2.bundle.bundle_id}],
    )


def _isolation(config: RegistryConfig) -> CheckResult:
    scen = config.base_dir / "scenarios" / "import-isolation"
    sub = RegistryConfig(
        sources=[
            SourceConfig(name="source-a", path=str(scen / "source-a"), precedence=10),
            SourceConfig(name="source-b", path=str(scen / "source-b"), precedence=10),
        ]
    )
    report = import_sources(sub)

    imported_ids = {c.effective_id for c in report.bundle.constraints}
    rejected = {e.constraint_id or e.file for e in report.schema_errors}

    valid_present = {"source-a/ok.a", "source-b/ok.b"} <= imported_ids
    broken_rejected = any("broken" in str(x) for x in rejected)
    broken_excluded = "source-b/broken.one" not in imported_ids

    if valid_present and broken_rejected and broken_excluded:
        return CheckResult.ok(
            SECTION,
            "VH-IMPORT-2",
            "malformed constraint rejected; valid constraints from both sources still imported",
            details=[{"imported": sorted(imported_ids), "rejected": sorted(map(str, rejected))}],
        )
    return CheckResult.fail(
        SECTION,
        "VH-IMPORT-2",
        "malformed-constraint isolation failed",
        details=[
            {
                "valid_present": valid_present,
                "broken_rejected": broken_rejected,
                "broken_excluded": broken_excluded,
                "imported": sorted(imported_ids),
                "schema_errors": [e.to_dict() for e in report.schema_errors],
            }
        ],
    )


def run(config: RegistryConfig) -> list[CheckResult]:
    return [_determinism(config), _isolation(config)]
