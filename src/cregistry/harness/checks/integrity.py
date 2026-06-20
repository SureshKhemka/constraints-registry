"""VH-INTEGRITY — fixture cross-check / anti-drift (VH-INTEGRITY-1/2).

VH-INTEGRITY-1: for every constraint with a binding + fixtures, the pass fixture
evaluates pass and the fail fixture evaluates fail via the bound engine
(FR-INTEGRITY-1).
VH-INTEGRITY-2: a binding whose referenced policy does not resolve is detected
and fails (FR-INTEGRITY-2/3).
"""

from __future__ import annotations

from ...config import RegistryConfig, SourceConfig
from ...engine.registry import EngineRegistry
from ...importer import import_sources
from ...integrity import check_integrity
from ..result import CheckResult

SECTION = "VH-INTEGRITY"


def _cross_check(config: RegistryConfig) -> CheckResult:
    bundle = import_sources(config).bundle
    registry = EngineRegistry.from_config(config)
    opa = registry.get("opa")
    if opa is not None and not getattr(opa, "available", True):
        return CheckResult.skip(
            SECTION, "VH-INTEGRITY-1", "opa binary not installed; cannot cross-check fixtures"
        )

    report = check_integrity(bundle, config, registry)
    if report.ok and report.cross_checked > 0:
        return CheckResult.ok(
            SECTION,
            "VH-INTEGRITY-1",
            f"all bound constraints' fixtures cross-check correctly ({report.cross_checked} evaluations)",
        )
    return CheckResult.fail(
        SECTION, "VH-INTEGRITY-1", "fixture cross-check found drift", details=[report.to_dict()]
    )


def _broken_binding(config: RegistryConfig) -> CheckResult:
    scen = config.base_dir / "scenarios" / "broken-binding"
    sub = RegistryConfig(
        sources=[SourceConfig(name="broken-binding", path=str(scen / "src"))],
        engines=config.engines,
    )
    sub.base_dir = config.base_dir
    bundle = import_sources(sub).bundle
    registry = EngineRegistry.from_config(sub)

    report = check_integrity(bundle, sub, registry)
    unresolved = [i for i in report.issues if i.kind == "policy-unresolved"]
    if unresolved and any(i.constraint == "broken-binding/broken.orphan-binding" for i in unresolved):
        return CheckResult.ok(
            SECTION,
            "VH-INTEGRITY-2",
            "broken/orphaned policy binding detected and reported as an integrity error",
            details=[i.to_dict() for i in unresolved],
        )
    return CheckResult.fail(
        SECTION,
        "VH-INTEGRITY-2",
        "broken-binding detection failed",
        details=[report.to_dict()],
    )


def run(config: RegistryConfig) -> list[CheckResult]:
    return [_cross_check(config), _broken_binding(config)]
