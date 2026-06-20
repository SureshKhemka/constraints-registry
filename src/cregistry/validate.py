"""Artifact validation orchestrator (FR-VALIDATE-1/2/3/4).

Selects the constraints relevant to a scope, evaluates each *bound* constraint by
delegating to the appropriate engine adapter, and assembles a structured report.
This is *layer 2* of the result schema: it wraps the engine's EngineVerdict
(layer 1) with constraint-level facts (severity, deprecation, guidance) the
engine never sees. Advisory (unbound) constraints are reported as informational,
never pass/fail (FR-VALIDATE-3). The artifact is never modified (FR-VALIDATE-4).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from .bundle import Bundle, ImportedConstraint
from .config import RegistryConfig
from .engine.interface import Verdict, Violation
from .engine.registry import EngineRegistry
from .model import Scope
from .query import select


@dataclass
class ConstraintResult:
    constraint: str
    title: str
    severity: str
    kind: str  # "enforced" | "advisory"
    verdict: str  # pass | fail | error | informational
    deprecated: bool
    successor: str | None
    enforced_by: list[dict]
    violations: list[dict]
    guidance: dict

    def to_dict(self) -> dict:
        return {
            "constraint": self.constraint,
            "title": self.title,
            "severity": self.severity,
            "kind": self.kind,
            "verdict": self.verdict,
            "deprecated": self.deprecated,
            "successor": self.successor,
            "enforced_by": self.enforced_by,
            "violations": self.violations,
            "guidance": self.guidance,
        }


@dataclass
class ValidationReport:
    bundle_id: str
    results: list[ConstraintResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """No hard/soft constraint failed. Advisory/informational never fail."""
        return not any(r.verdict in ("fail", "error") for r in self.results)

    def to_dict(self) -> dict:
        return {
            "bundle_id": self.bundle_id,
            "passed": self.passed,
            "results": [r.to_dict() for r in self.results],
        }


def _remediation_from_guidance(ic: ImportedConstraint) -> str | None:
    g = ic.constraint.guidance
    if g.do:
        return "; ".join(g.do)
    if g.dont:
        return "; ".join(g.dont)
    return None


def _evaluate_bound(
    ic: ImportedConstraint, artifact: Any, registry: EngineRegistry, config: RegistryConfig
) -> tuple[str, list[dict]]:
    """Evaluate every binding of a bound constraint; combine into one verdict."""
    verdicts: list[Verdict] = []
    violations: list[dict] = []
    remediation = _remediation_from_guidance(ic)

    for binding in ic.constraint.enforcement:
        adapter = registry.for_binding(binding)
        policy_path = config.resolved_policy_path(ic.source, binding.policy)
        if adapter is None:
            verdicts.append(Verdict.error)
            violations.append(
                Violation(
                    message=f"no engine adapter for binding engine {binding.engine!r}",
                    rule=binding.engine,
                ).to_dict()
            )
            continue
        if policy_path is None or not policy_path.exists():
            verdicts.append(Verdict.error)
            violations.append(
                Violation(message=f"policy not found: {binding.policy}", rule=binding.engine).to_dict()
            )
            continue

        verdict = adapter.evaluate(artifact, str(policy_path))
        verdicts.append(verdict.verdict)
        for v in verdict.violations:
            d = v.to_dict()
            if d.get("remediation") is None:
                d["remediation"] = remediation
            violations.append(d)

    if any(v is Verdict.error for v in verdicts):
        combined = "error"
    elif any(v is Verdict.failed for v in verdicts):
        combined = "fail"
    else:
        combined = "pass"
    return combined, violations


def validate(
    bundle: Bundle,
    artifact: Any,
    scope: Scope,
    registry: EngineRegistry,
    config: RegistryConfig,
) -> ValidationReport:
    # FR-VALIDATE-4: never modify the artifact. We pass a deep copy to engines so
    # an adapter cannot mutate the caller's object.
    safe_artifact = copy.deepcopy(artifact)

    report = ValidationReport(bundle_id=bundle.bundle_id)
    for ic in select(bundle, scope):
        c = ic.constraint
        guidance = c.guidance.model_dump(mode="json", exclude_none=True)
        enforced_by = [{"engine": b.engine, "policy": b.policy} for b in c.enforcement]

        if c.is_advisory:
            # FR-VALIDATE-3: advisory constraints are informational, no engine.
            report.results.append(
                ConstraintResult(
                    constraint=ic.effective_id,
                    title=c.title,
                    severity=c.severity.value,
                    kind="advisory",
                    verdict="informational",
                    deprecated=c.deprecated,
                    successor=c.successor,
                    enforced_by=[],
                    violations=[],
                    guidance=guidance,
                )
            )
            continue

        verdict, violations = _evaluate_bound(ic, safe_artifact, registry, config)
        report.results.append(
            ConstraintResult(
                constraint=ic.effective_id,
                title=c.title,
                severity=c.severity.value,
                kind="enforced",
                verdict=verdict,
                deprecated=c.deprecated,
                successor=c.successor,
                enforced_by=enforced_by,
                violations=violations,
                guidance=guidance,
            )
        )
    return report
