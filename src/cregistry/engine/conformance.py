"""Engine-interface conformance suite (VH-ENGINE-2, FR-ENGINE-2).

A reusable, engine-agnostic test of the ``EngineAdapter`` contract. It is driven
entirely by data (``ConformanceCase``s), so a future engine is validated against
the same contract by supplying its own cases — no new harness code is required.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..model import EnforcementBinding
from .interface import EngineAdapter, Verdict

_FOREIGN_ENGINE = "__definitely_not_a_real_engine__"


@dataclass(frozen=True)
class ConformanceCase:
    name: str
    policy: str  # resolved locator
    artifact: Any
    expected: Verdict  # passed or failed


def run_conformance(adapter: EngineAdapter, cases: list[ConformanceCase]) -> list[dict]:
    """Run the contract checks against an adapter. Returns one result dict per
    check with an ``ok`` boolean, so the harness can aggregate uniformly."""
    results: list[dict] = []

    # FR-ENGINE-3a: can_handle accepts its own engine, rejects a foreign one.
    own = adapter.can_handle(EnforcementBinding(engine=adapter.name, policy="x"))
    foreign = adapter.can_handle(EnforcementBinding(engine=_FOREIGN_ENGINE, policy="x"))
    results.append(
        {"check": "can_handle", "ok": bool(own) and not bool(foreign), "own": own, "foreign": foreign}
    )

    # NFR-2: an unrunnable (missing) policy yields an error verdict, never a crash.
    try:
        mv = adapter.evaluate({}, "/no/such/policy/__conformance_missing__.policy")
        results.append(
            {"check": "missing_policy_error", "ok": mv.verdict is Verdict.error, "verdict": mv.verdict.value}
        )
    except Exception as exc:  # noqa: BLE001
        results.append({"check": "missing_policy_error", "ok": False, "error": repr(exc)})

    # FR-ENGINE-3b: structured pass/fail verdicts + determinism (NFR-1).
    for case in cases:
        v1 = adapter.evaluate(case.artifact, case.policy)
        v2 = adapter.evaluate(case.artifact, case.policy)
        shape_ok = isinstance(v1.verdict, Verdict)
        verdict_ok = v1.verdict is case.expected
        deterministic = v1.to_dict() == v2.to_dict()
        if case.expected is Verdict.failed:
            viol_ok = len(v1.violations) >= 1
        else:
            viol_ok = len(v1.violations) == 0
        results.append(
            {
                "check": f"case:{case.name}",
                "ok": shape_ok and verdict_ok and deterministic and viol_ok,
                "verdict": v1.verdict.value,
                "expected": case.expected.value,
                "violations": len(v1.violations),
                "deterministic": deterministic,
            }
        )

    return results
