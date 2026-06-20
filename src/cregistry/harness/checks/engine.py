"""VH-ENGINE — engine-interface conformance (VH-ENGINE-1/2/3).

VH-ENGINE-1: the shipped reference adapter (OPA) satisfies the FR-ENGINE-3 ops.
VH-ENGINE-2: a reusable conformance suite for the interface itself, runnable
against any adapter and loaded by config (FR-ENGINE-2/5).
VH-ENGINE-3: advisory constraints (no binding) are handled with zero engines
involved (FR-ENGINE-4).
"""

from __future__ import annotations

import json

from ...config import RegistryConfig
from ...engine.conformance import ConformanceCase, run_conformance
from ...engine.interface import Verdict
from ...engine.registry import EngineRegistry, required_engines
from ...importer import import_sources
from ...model import EnforcementBinding
from ..result import CheckResult

SECTION = "VH-ENGINE"


def _opa_cases(config: RegistryConfig) -> list[ConformanceCase]:
    """Build conformance cases from the bundled constraints' real fixtures."""
    bundle = import_sources(config).bundle
    cases: list[ConformanceCase] = []
    for ic in bundle.constraints:
        c = ic.constraint
        if not c.enforcement or c.fixtures is None:
            continue
        for binding in c.enforcement:
            if binding.engine != "opa":
                continue
            policy = config.resolved_policy_path(ic.source, binding.policy)
            if c.fixtures.pass_:
                art = json.loads(config.resolved_policy_path(ic.source, c.fixtures.pass_).read_text())
                cases.append(ConformanceCase(f"{ic.effective_id}:pass", str(policy), art, Verdict.passed))
            if c.fixtures.fail:
                art = json.loads(config.resolved_policy_path(ic.source, c.fixtures.fail).read_text())
                cases.append(ConformanceCase(f"{ic.effective_id}:fail", str(policy), art, Verdict.failed))
    return cases


def _reference_adapter(config: RegistryConfig) -> CheckResult:
    registry = EngineRegistry.from_config(config)
    opa = registry.get("opa")
    if opa is None:
        return CheckResult.fail(
            SECTION, "VH-ENGINE-1", "opa adapter not loaded from config",
            details=[e.to_dict() for e in registry.load_errors],
        )
    if not getattr(opa, "available", True):
        return CheckResult.skip(
            SECTION, "VH-ENGINE-1", "opa binary not installed; skipping reference-adapter check"
        )

    cases = _opa_cases(config)
    # FR-ENGINE-3a + 3b on the real reference adapter against real fixtures.
    handles = opa.can_handle(EnforcementBinding(engine="opa", policy="x"))
    verdicts_ok = all(opa.evaluate(c.artifact, c.policy).verdict is c.expected for c in cases)
    if handles and cases and verdicts_ok:
        return CheckResult.ok(
            SECTION, "VH-ENGINE-1",
            f"reference OPA adapter satisfies interface ops over {len(cases)} fixture case(s)",
        )
    return CheckResult.fail(
        SECTION, "VH-ENGINE-1", "reference adapter did not satisfy interface ops",
        details=[{"can_handle": handles, "cases": len(cases), "verdicts_ok": verdicts_ok}],
    )


def _conformance_suite(config: RegistryConfig) -> CheckResult:
    # FR-ENGINE-5: adapter obtained purely via config-driven loading.
    registry = EngineRegistry.from_config(config)
    opa = registry.get("opa")
    if opa is None:
        return CheckResult.fail(SECTION, "VH-ENGINE-2", "opa adapter not configured")
    if not getattr(opa, "available", True):
        return CheckResult.skip(SECTION, "VH-ENGINE-2", "opa binary not installed; skipping suite")

    results = run_conformance(opa, _opa_cases(config))
    failed = [r for r in results if not r["ok"]]
    if not failed and len(results) > 1:
        return CheckResult.ok(
            SECTION, "VH-ENGINE-2",
            f"engine-interface conformance suite passed ({len(results)} checks) against config-loaded adapter",
            details=results,
        )
    return CheckResult.fail(
        SECTION, "VH-ENGINE-2", "conformance suite failed", details=failed or results,
    )


def _second_adapter_same_suite(config: RegistryConfig) -> CheckResult:
    """FR-ENGINE-2: a second engine (conftest) is validated by the *same*
    conformance suite with no new harness code. Skips (does not fail) when the
    conftest binary is not installed; the OPA reference stays green."""
    registry = EngineRegistry.from_config(config)
    conftest = registry.get("conftest")
    if conftest is None:
        return CheckResult.skip(
            SECTION, "VH-ENGINE-2:second-adapter", "no second engine adapter configured"
        )
    if not getattr(conftest, "available", False):
        return CheckResult.skip(
            SECTION,
            "VH-ENGINE-2:second-adapter",
            "conftest binary not installed; second-adapter conformance pending "
            "(adapter + config wired; same suite would validate it)",
        )

    results = run_conformance(conftest, _opa_cases(config))
    failed = [r for r in results if not r["ok"]]
    if not failed and len(results) > 1:
        return CheckResult.ok(
            SECTION,
            "VH-ENGINE-2:second-adapter",
            f"second engine (conftest) passed the same conformance suite ({len(results)} checks)",
            details=results,
        )
    return CheckResult.fail(
        SECTION, "VH-ENGINE-2:second-adapter", "second-adapter conformance failed", details=failed,
    )


def _advisory_no_engine(config: RegistryConfig) -> CheckResult:
    bundle = import_sources(config).bundle
    advisory = [c for c in bundle.constraints if c.constraint.is_advisory]
    bound = [c for c in bundle.constraints if not c.constraint.is_advisory]

    adv_engines = required_engines(advisory)
    bound_engines = required_engines(bound)

    # An empty registry (zero adapters) can still cover advisory constraints,
    # because they require no engines at all (FR-ENGINE-4).
    empty_registry = EngineRegistry.from_config(RegistryConfig(engines=[]))
    advisory_covered = adv_engines.issubset(set(empty_registry.names()))  # ∅ ⊆ ∅

    if advisory and adv_engines == set() and bound_engines and advisory_covered:
        return CheckResult.ok(
            SECTION, "VH-ENGINE-3",
            f"{len(advisory)} advisory constraint(s) need zero engines; "
            f"engines are only required for bound constraints ({sorted(bound_engines)})",
        )
    return CheckResult.fail(
        SECTION, "VH-ENGINE-3", "advisory/no-engine handling failed",
        details=[
            {
                "advisory_count": len(advisory),
                "advisory_engines": sorted(adv_engines),
                "bound_engines": sorted(bound_engines),
                "advisory_covered_by_empty_registry": advisory_covered,
            }
        ],
    )


def run(config: RegistryConfig) -> list[CheckResult]:
    return [
        _reference_adapter(config),
        _conformance_suite(config),
        _second_adapter_same_suite(config),
        _advisory_no_engine(config),
    ]
