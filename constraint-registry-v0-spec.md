# Constraint Registry — V0 Specification

**Audience:** Claude Code (implementation agent)
**Document type:** Requirements specification. This document states *what* the system must do. It deliberately does **not** prescribe implementation architecture (language, frameworks, storage, module layout), with a single explicit exception called out in **FR-ENGINE** (enforcement-engine extensibility). Where an external interface is specified (MCP methods, constraint fields), treat it as a contract requirement, not an internal design instruction.

**Implementation discipline:** Build strictly to the requirements below. Do not add capabilities listed under *Out of Scope*. If a requirement is ambiguous, stop and ask rather than inventing behavior.

---

## 1. Purpose

The Constraint Registry is a single, queryable source of engineering constraints (infrastructure, organizational, and architectural) that coding agents (e.g. Claude, Codex, Cursor) consult at code-generation time, and that downstream deterministic checks bind to. It does **not** enforce constraints itself; it provides guidance to generators and exposes a validation surface that delegates to existing enforcement engines. The registry aggregates constraints authored across many source repositories and exposes them over a single MCP server.

---

## 2. Definitions

- **Constraint** — A single governance rule with human-readable intent, scope, severity, optional enforcement binding(s), and optional fixtures.
- **Source repository** — A repository owned by a team (platform, security, an architecture group, a domain) that declares one or more constraints in the registry's constraint format.
- **Enforcement engine** — An external deterministic tool that evaluates an artifact against a policy (e.g. Conftest/OPA, Checkov, an architecture linter). The registry integrates engines via a stable interface; it does not reimplement them.
- **Enforcement binding** — A reference from a constraint to a specific engine + policy that enforces it. The registry references the policy; it does not copy the policy logic.
- **Fixture** — A sample artifact paired with an expected verdict (`pass` / `fail`) used to cross-check that a constraint's enforcement binding behaves as the constraint claims.
- **Bundle** — An immutable, versioned, aggregated snapshot of all imported constraints, produced by the import process and served to consumers.
- **Consumer** — An agent or tool that queries the registry over MCP.
- **Advisory constraint** — A constraint with no enforcement binding (judgment/architectural guidance), surfaced to agents and humans but not deterministically checkable.

---

## 3. Goals (V0)

- G1. Let teams declare infrastructure, organizational, and architectural constraints in a single shared format.
- G2. Aggregate constraints from multiple source repositories into one versioned, queryable index.
- G3. Expose constraints to coding agents over an MCP server, scoped to what is relevant to a request.
- G4. Let an agent validate a candidate artifact against relevant constraints by delegating to existing enforcement engines.
- G5. Keep constraint guidance and enforcement from drifting apart, without re-encoding enforcement logic in the registry.
- G6. Support adding new enforcement engines without significant code changes.
- G7. Ship a validation harness that proves the registry and its constraints are internally consistent.

## 4. Non-Goals (Out of Scope for V0)

- N1. Generating/compiling enforcement policies (Rego, SCPs, Config rules) from declarative constraints.
- N2. Generating static rules-file artifacts (e.g. `CLAUDE.md`, `.cursorrules`) for non-MCP agents.
- N3. Runtime backstops (AWS SCP / Config / admission controllers) of any kind.
- N4. A web UI, dashboard, or authoring GUI.
- N5. Authentication, authorization, or multi-tenant access control beyond what is required to read source repositories.
- N6. Auto-remediation of artifacts (the registry reports violations; it does not rewrite code).

---

## 5. Functional Requirements

### FR-CONSTRAINT — Constraint model

- FR-CONSTRAINT-1. A constraint MUST be declared in a structured, version-controllable text format. Each constraint MUST support the following fields:
  - `id` — stable identifier, unique within its source.
  - `title` — short human-readable name.
  - `intent` — prose explaining *why* the constraint exists.
  - `category` — one of `infrastructure`, `organizational`, `architectural`.
  - `scope` — selectors that determine when the constraint is relevant. The scope model MUST support at minimum: provider/platform tags, resource or component types, environments, and repo/team tags. The scope model MUST additionally support **relationship-style** selectors for architectural constraints (e.g. a source component, a target component, a boundary or layer), not only single-resource attribute selectors.
  - `severity` — one of `hard`, `soft`, `advisory`.
  - `enforcement` — zero or more enforcement bindings (see FR-ENGINE). A constraint with zero bindings is an advisory constraint and MUST still be importable and queryable.
  - `guidance` — agent-facing content. MUST support, at minimum: `do` rules, `dont` rules, and at least one `example_compliant` snippet. SHOULD support an `example_noncompliant` snippet.
  - `owner` — the responsible team/group.
  - `fixtures` — optional `pass` and `fail` fixture references (see FR-INTEGRITY).
  - `version` — semantic version of this constraint (see FR-VERSION).
- FR-CONSTRAINT-2. The registry MUST reject, at import time, any constraint that fails schema validation, and MUST report which constraint and which field failed. A single invalid constraint MUST NOT prevent valid constraints from other sources being imported.
- FR-CONSTRAINT-3. Enforcement bindings MUST reference an external policy (engine + policy locator). The registry MUST NOT contain a second copy of the enforcement logic itself.

### FR-SOURCE — Sources and import/aggregation

- FR-SOURCE-1. The registry MUST import constraints from a configurable set of source repositories.
- FR-SOURCE-2. The import process MUST validate every constraint (FR-CONSTRAINT-2), aggregate all valid constraints into a single index, and produce a versioned bundle (FR-VERSION).
- FR-SOURCE-3. The import process MUST be re-runnable and deterministic: the same set of sources at the same revisions MUST produce an equivalent bundle.
- FR-SOURCE-4. The registry MUST record, per constraint, which source it came from.

### FR-NAMESPACE — Namespacing and precedence

- FR-NAMESPACE-1. Imported constraints MUST be namespaced by source so that identical `id`s from different sources do not collide (effective identifier = source namespace + `id`).
- FR-NAMESPACE-2. When two constraints from different sources target the same scope, the registry MUST resolve precedence by a configurable policy. The default policy MUST be: a `hard` constraint outranks a non-`hard` constraint; a downstream/team source MAY add constraints but MUST NOT relax (override to weaker severity) a constraint from a higher-precedence source.
- FR-NAMESPACE-3. Precedence conflicts that cannot be resolved MUST be surfaced as errors at import time, identifying the conflicting constraints and sources.

### FR-VERSION — Versioning

- FR-VERSION-1. Each constraint MUST carry a semantic version.
- FR-VERSION-2. Each produced bundle MUST be immutable and carry its own version/identifier.
- FR-VERSION-3. The MCP server MUST allow a consumer to request constraints from a specific bundle version, and MUST default to the latest bundle when no version is requested.
- FR-VERSION-4. A constraint MUST support being marked `deprecated` with an optional successor reference; deprecated constraints MUST still be returned by queries but MUST be flagged as deprecated in responses.

### FR-ENGINE — Enforcement-engine extensibility *(the one mandated architectural requirement)*

- FR-ENGINE-1. The registry MUST integrate enforcement engines through a single, stable, documented engine interface.
- FR-ENGINE-2. Adding support for a new enforcement engine MUST require only implementing that interface (an engine adapter). It MUST NOT require changes to: the constraint schema, the import/aggregation process, the MCP server, or the validation harness.
- FR-ENGINE-3. The engine interface MUST, at minimum, expose the operations needed to: (a) identify whether the engine can handle a given enforcement binding, and (b) evaluate a supplied artifact against a referenced policy and return a structured verdict (`pass`/`fail`) with violation details.
- FR-ENGINE-4. V0 MUST ship at least one working engine adapter (Conftest/OPA) as the reference implementation that exercises the full interface. Advisory constraints (no binding) MUST be supported with zero engine adapters involved.
- FR-ENGINE-5. The set of available engine adapters MUST be discoverable/configurable without code changes to the core (e.g. via configuration), consistent with FR-ENGINE-2.

### FR-VALIDATE — Artifact validation

- FR-VALIDATE-1. The registry MUST provide an operation that takes a candidate artifact plus a scope, selects the relevant constraints (FR-QUERY-2), and evaluates the artifact against each relevant constraint that has an enforcement binding, by delegating to the appropriate engine adapter.
- FR-VALIDATE-2. The result MUST be a structured report listing, per constraint: the constraint identifier, severity, verdict, and violation details where applicable.
- FR-VALIDATE-3. Advisory constraints in scope MUST be included in the report as informational items (not pass/fail), so an agent can still see and honor them.
- FR-VALIDATE-4. Validation MUST NOT modify the artifact.

### FR-QUERY — Query / scoping

- FR-QUERY-1. The registry MUST return constraints filtered by a supplied scope, returning only constraints whose selectors match.
- FR-QUERY-2. Scope matching MUST support all selector dimensions defined in FR-CONSTRAINT-1 (`scope`), including relationship-style selectors.
- FR-QUERY-3. Query responses MUST include each matched constraint's intent, guidance, severity, deprecation status, and (where present) the fact that it is enforced downstream and by which stage/engine — so an agent knows which constraints are hard downstream gates.

### FR-MCP — MCP server interface

- FR-MCP-1. The registry MUST expose its capabilities as an MCP server.
- FR-MCP-2. The server MUST expose at least two operations:
  - `get_constraints(scope, [version])` — returns the scoped set of constraints per FR-QUERY.
  - `validate(artifact, scope, [version])` — returns the validation report per FR-VALIDATE.
- FR-MCP-3. Each operation's inputs and outputs MUST be documented as a stable contract.
- FR-MCP-4. The MCP server MUST fail **open** for guidance: if the registry/index is unavailable or a query cannot be served, `get_constraints` MUST fail in a way that allows the calling agent to proceed without constraints rather than blocking it. (`validate` MAY surface an explicit error, since it is an active check rather than passive guidance.)

### FR-INTEGRITY — Single-source integrity (anti-drift)

- FR-INTEGRITY-1. For any constraint that declares both an enforcement binding and fixtures, the registry MUST be able to cross-check the binding against the fixtures: the `pass` fixture MUST be evaluated as `pass` by the bound engine, and the `fail` fixture MUST be evaluated as `fail`.
- FR-INTEGRITY-2. An enforcement binding that references a policy which cannot be located or loaded MUST be reported as an integrity error (orphaned/broken binding).
- FR-INTEGRITY-3. The registry MUST be able to report any enforcement policy referenced by a binding that does not resolve, and any constraint whose fixtures contradict its bound engine's behavior.

---

## 6. Non-Functional Requirements

- NFR-1. **Determinism.** Given fixed inputs (sources at fixed revisions, fixed artifact), import and validation MUST produce equivalent results across runs.
- NFR-2. **Isolation of failure.** A malformed constraint, a missing policy, or an unavailable single engine adapter MUST NOT crash import or the MCP server; such conditions MUST be reported and the rest of the system MUST continue to serve.
- NFR-3. **Scoping efficiency.** `get_constraints` MUST return only in-scope constraints; it MUST NOT return the entire catalog when a scope is supplied.
- NFR-4. **Observability.** Import results, integrity-check results, and validation results MUST be reportable in a machine-readable structured form suitable for CI consumption.
- NFR-5. **Extensibility boundary.** The only component expected to change when adding an engine is a new engine adapter (restates FR-ENGINE-2 as an acceptance condition).

---

## 7. Validation Harness Specification

The validation harness is a separate, runnable component that proves the registry and its constraint set are internally consistent. It is intended to run in CI. It tests the registry; it is distinct from `FR-VALIDATE` (which validates user artifacts).

### VH-SCHEMA — Schema conformance
- VH-SCHEMA-1. The harness MUST verify that every constraint in every configured source conforms to the constraint schema (FR-CONSTRAINT-1), and MUST fail with a per-constraint, per-field report on any violation.

### VH-IMPORT — Import and aggregation
- VH-IMPORT-1. The harness MUST verify that import is deterministic (FR-SOURCE-3): two runs over identical inputs produce equivalent bundles.
- VH-IMPORT-2. The harness MUST verify that a deliberately malformed constraint is rejected while valid constraints from other sources still import (FR-CONSTRAINT-2, NFR-2).

### VH-NAMESPACE — Namespacing and precedence
- VH-NAMESPACE-1. The harness MUST verify that colliding `id`s from different sources are disambiguated by namespace (FR-NAMESPACE-1).
- VH-NAMESPACE-2. The harness MUST verify the default precedence policy: a `hard` constraint outranks a weaker one, and a lower-precedence source cannot relax a higher-precedence constraint (FR-NAMESPACE-2), and that unresolvable conflicts are reported as errors (FR-NAMESPACE-3).

### VH-VERSION — Versioning
- VH-VERSION-1. The harness MUST verify that a consumer can request a specific bundle version and receives that version's constraints, and that omitting the version yields the latest bundle (FR-VERSION-3).
- VH-VERSION-2. The harness MUST verify that deprecated constraints are still returned and are flagged as deprecated (FR-VERSION-4).

### VH-ENGINE — Engine-interface conformance
- VH-ENGINE-1. The harness MUST verify that the shipped reference engine adapter (Conftest/OPA) satisfies the engine interface operations defined in FR-ENGINE-3.
- VH-ENGINE-2. The harness MUST include a **conformance test suite for the engine interface itself**, runnable against any adapter, so that a future engine can be validated against the same contract without new harness code (supports FR-ENGINE-2).
- VH-ENGINE-3. The harness MUST verify that advisory constraints (no binding) are handled with no engine adapter involved (FR-ENGINE-4).

### VH-INTEGRITY — Fixture cross-check (anti-drift)
- VH-INTEGRITY-1. For every constraint that declares an enforcement binding and fixtures, the harness MUST evaluate the `pass` fixture and assert a `pass` verdict, and evaluate the `fail` fixture and assert a `fail` verdict, via the bound engine (FR-INTEGRITY-1). Any mismatch MUST fail the harness and identify the constraint.
- VH-INTEGRITY-2. The harness MUST detect and fail on any enforcement binding whose referenced policy does not resolve (FR-INTEGRITY-2/3).

### VH-MCP — MCP contract
- VH-MCP-1. The harness MUST verify that `get_constraints` and `validate` honor their documented input/output contracts (FR-MCP-2/3).
- VH-MCP-2. The harness MUST verify scoping: `get_constraints` with a scope returns only in-scope constraints and never the full catalog (NFR-3).
- VH-MCP-3. The harness MUST verify fail-open behavior of `get_constraints` under an unavailable index (FR-MCP-4).

### VH-OUTPUT — Harness output
- VH-OUTPUT-1. The harness MUST emit a structured, machine-readable result suitable for CI (NFR-4), and MUST return a non-zero exit status if any check fails.
- VH-OUTPUT-2. The harness MUST run end-to-end against a small, self-contained set of sample sources and fixtures included with the project (so it is runnable without external repositories).

---

## 8. V0 Acceptance Criteria (Definition of Done)

The V0 is complete when:

1. Constraints across all three categories — infrastructure, organizational, **and** architectural (including at least one relationship-style architectural constraint and at least one advisory constraint with no binding) — can be authored, imported, namespaced, versioned, and queried. *(FR-CONSTRAINT, FR-SOURCE, FR-NAMESPACE, FR-VERSION, FR-QUERY)*
2. The Conftest/OPA reference engine adapter works through the stable engine interface, and a documented procedure exists to add another engine by implementing only an adapter. *(FR-ENGINE)*
3. The MCP server exposes `get_constraints` and `validate` per their contracts, scopes results, and fails open on `get_constraints`. *(FR-MCP, FR-VALIDATE, FR-QUERY)*
4. Fixture cross-checks pass for all bound constraints, and broken bindings are detected. *(FR-INTEGRITY)*
5. The validation harness runs end-to-end against the bundled sample sources, covers every `VH-*` section, and exits non-zero on any failure. *(Section 7)*
6. No capability listed under *Non-Goals* has been implemented.

---

## 9. Illustrative constraint (non-normative)

Provided only to disambiguate the field semantics in FR-CONSTRAINT-1. The serialization format is illustrative, not mandated.

```yaml
id: aws.s3.no-public-access
title: "S3 buckets must not be publicly accessible"
intent: >
  Public buckets are the top source of data-exposure incidents. All buckets
  are private; sharing is via signed URLs or CloudFront OAC.
category: infrastructure
scope:
  providers: [aws]
  resource_types: [aws_s3_bucket, aws_s3_bucket_public_access_block]
  environments: [all]
  repos: [tag:data-plane]
severity: hard
enforcement:
  - { engine: conftest, policy: policies/s3_public.rego }
guidance:
  dont: ["Never set acl = 'public-read' or 'public-read-write'"]
  example_compliant: |
    resource "aws_s3_bucket_public_access_block" "this" {
      bucket                  = aws_s3_bucket.this.id
      block_public_acls       = true
      block_public_policy     = true
      ignore_public_acls      = true
      restrict_public_buckets = true
    }
owner: platform-security
version: 1.0.0
fixtures:
  pass: fixtures/s3_private.tf
  fail: fixtures/s3_public.tf
```

Example of an architectural, relationship-style, advisory constraint (no enforcement binding):

```yaml
id: arch.no-sync-cross-domain
title: "No synchronous calls across domain boundaries"
intent: >
  Cross-domain synchronous coupling creates cascading-failure risk and blocks
  independent deploys. Prefer asynchronous/event-driven integration across domains.
category: architectural
scope:
  relationship:
    source: { layer: domain-service }
    target: { layer: domain-service, different_domain: true }
    interaction: synchronous
severity: advisory
guidance:
  dont: ["Avoid direct synchronous HTTP/gRPC calls from one domain's service into another's"]
  example_compliant: |
    # Emit a domain event; the consuming domain subscribes.
owner: architecture-guild
version: 1.0.0
```
