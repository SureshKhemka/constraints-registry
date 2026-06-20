"""Single-source integrity / anti-drift checks (FR-INTEGRITY-1/2/3).

Cross-checks each constraint's enforcement binding against the constraint's own
claims, so guidance and enforcement cannot silently drift apart:

* the bound engine's policy must resolve/load (else: broken/orphaned binding);
* the ``pass`` fixture must evaluate to pass and the ``fail`` fixture to fail.

This never re-encodes policy logic — it runs the real engine via its adapter.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from .bundle import Bundle
from .config import RegistryConfig
from .engine.interface import Verdict
from .engine.registry import EngineRegistry


@dataclass(frozen=True)
class IntegrityIssue:
    kind: str
    constraint: str
    message: str
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "constraint": self.constraint,
            "message": self.message,
            "detail": self.detail,
        }


@dataclass
class IntegrityReport:
    issues: list[IntegrityIssue] = field(default_factory=list)
    cross_checked: int = 0  # number of fixture evaluations performed

    @property
    def ok(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "cross_checked": self.cross_checked,
            "issues": [i.to_dict() for i in self.issues],
        }


def check_integrity(bundle: Bundle, config: RegistryConfig, registry: EngineRegistry) -> IntegrityReport:
    report = IntegrityReport()

    for ic in bundle.constraints:
        c = ic.constraint
        for binding in c.enforcement:
            eid = ic.effective_id
            adapter = registry.for_binding(binding)
            if adapter is None:
                report.issues.append(
                    IntegrityIssue(
                        "no-engine-adapter",
                        eid,
                        f"no configured engine adapter handles binding engine {binding.engine!r}",
                        {"engine": binding.engine, "policy": binding.policy},
                    )
                )
                continue

            policy_path = config.resolved_policy_path(ic.source, binding.policy)
            if policy_path is None or not policy_path.exists():
                # FR-INTEGRITY-2/3: referenced policy does not resolve.
                report.issues.append(
                    IntegrityIssue(
                        "policy-unresolved",
                        eid,
                        f"enforcement policy could not be located: {binding.policy}",
                        {"engine": binding.engine, "policy": str(policy_path or binding.policy)},
                    )
                )
                continue

            if c.fixtures is None:
                continue

            for kind, locator, expected in (
                ("pass", c.fixtures.pass_, Verdict.passed),
                ("fail", c.fixtures.fail, Verdict.failed),
            ):
                if not locator:
                    continue
                fpath = config.resolved_policy_path(ic.source, locator)
                if fpath is None or not fpath.exists():
                    report.issues.append(
                        IntegrityIssue(
                            "fixture-missing",
                            eid,
                            f"{kind} fixture not found: {locator}",
                            {"fixture": str(fpath or locator)},
                        )
                    )
                    continue

                artifact = json.loads(fpath.read_text())
                verdict = adapter.evaluate(artifact, str(policy_path))
                report.cross_checked += 1
                if verdict.verdict is Verdict.error:
                    report.issues.append(
                        IntegrityIssue(
                            "evaluation-error",
                            eid,
                            f"engine error evaluating {kind} fixture: {verdict.error}",
                            {"fixture": locator},
                        )
                    )
                elif verdict.verdict is not expected:
                    # FR-INTEGRITY-1/3: fixture contradicts bound engine behavior.
                    report.issues.append(
                        IntegrityIssue(
                            "fixture-mismatch",
                            eid,
                            f"{kind} fixture expected {expected.value} but engine returned {verdict.verdict.value}",
                            {"fixture": locator, "violations": [v.to_dict() for v in verdict.violations]},
                        )
                    )

    report.issues.sort(key=lambda i: (i.constraint, i.kind))
    return report
