"""VH-OUTPUT — harness output (VH-OUTPUT-1, VH-OUTPUT-2).

VH-OUTPUT-1: the harness emits a structured, machine-readable result and returns
non-zero on any failure (NFR-4).
VH-OUTPUT-2: the harness runs end-to-end against a small, self-contained set of
sample sources and fixtures bundled with the project (no external repositories).
"""

from __future__ import annotations

import json

from ...config import RegistryConfig
from ..result import CheckResult, Status

SECTION = "VH-OUTPUT"


def _structured(config: RegistryConfig) -> CheckResult:
    # Import here to avoid a circular import at module load.
    from ..run import build_report

    ok = CheckResult.ok("X", "X-1", "ok")
    bad = CheckResult.fail("X", "X-2", "bad")

    all_pass = build_report([ok])
    with_fail = build_report([ok, bad])

    serializable = True
    try:
        json.dumps(with_fail)
    except (TypeError, ValueError):
        serializable = False

    shape_ok = {"passed", "summary", "checks"} <= set(with_fail)
    # Non-zero mapping: main() returns 0 only when report["passed"] is True.
    nonzero_on_fail = all_pass["passed"] is True and with_fail["passed"] is False

    if serializable and shape_ok and nonzero_on_fail:
        return CheckResult.ok(
            SECTION,
            "VH-OUTPUT-1",
            "harness emits structured JSON and reports non-zero (passed=false) on any failure",
        )
    return CheckResult.fail(
        SECTION, "VH-OUTPUT-1", "structured-output/exit-code contract failed",
        details=[{"serializable": serializable, "shape_ok": shape_ok, "nonzero_on_fail": nonzero_on_fail}],
    )


def _self_contained(config: RegistryConfig) -> CheckResult:
    problems: list[str] = []
    if not config.sources:
        problems.append("no sources configured")
    for src in config.sources:
        if "://" in src.path:
            problems.append(f"source {src.name} references a non-local path: {src.path}")
        path = config.resolved_source_path(src)
        if not path.exists():
            problems.append(f"source {src.name} path does not exist locally: {path}")
        else:
            try:
                path.resolve().relative_to(config.base_dir.resolve())
            except ValueError:
                problems.append(f"source {src.name} is outside the project tree: {path}")

    if not problems:
        return CheckResult.ok(
            SECTION,
            "VH-OUTPUT-2",
            f"harness ran end-to-end against {len(config.sources)} self-contained local source(s)",
        )
    return CheckResult.fail(SECTION, "VH-OUTPUT-2", "self-containment check failed", details=[{"problems": problems}])


def run(config: RegistryConfig) -> list[CheckResult]:
    return [_structured(config), _self_contained(config)]
