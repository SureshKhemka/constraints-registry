# MCP Contract (FR-MCP-2/3)

The Constraint Registry exposes an MCP server (`cregistry-mcp`, stdio transport)
with two tools. Inputs/outputs below are the stable contract.

## Common types

```
Scope = {
  providers?: string[],        # e.g. ["aws"]
  resource_types?: string[],   # e.g. ["aws_s3_bucket"]
  environments?: string[],     # e.g. ["prod"]; constraint "all" matches any
  repos?: string[],            # repo/team tags, e.g. ["tag:data-plane"]
  relationship?: {             # relationship-style selector (architectural)
    source?:  { layer?, component?, domain?, different_domain? },
    target?:  { layer?, component?, domain?, different_domain? },
    interaction?: string,      # e.g. "synchronous", "data-access"
    boundary?: string
  }
}
Violation = { message, rule?, resource?, path?, raw?, remediation? }
```

A constraint is selected when, for every dimension it restricts, the query
supplies a matching value; a relationship-scoped constraint is only selected by a
query with a matching relationship. Unscoped queries do not return the full
catalog (NFR-3).

## `get_constraints(scope, version?) -> object`

Returns the constraints relevant to `scope` (FR-QUERY).

**Input:** `scope: Scope`, `version?: string` (bundle id; defaults to latest).

**Output:**
```
{
  available: boolean,          # false => fail-open (see below)
  bundle_id: string | null,
  constraints: [
    {
      constraint,              # effective id "<source>/<id>"
      source, id, title, intent, category, severity,
      scope, guidance, owner, version,
      deprecated: boolean, successor: string | null,   # FR-VERSION-4
      advisory: boolean,
      enforced: boolean,                                # FR-QUERY-3
      enforced_by: [ { engine, policy } ]               # which engine/stage gates it
    }
  ]
}
```

**Fail-open (FR-MCP-4):** if the index is unavailable or the query cannot be
served, `get_constraints` never raises and returns
`{ available: false, reason, bundle_id: null, constraints: [] }` so the calling
agent can proceed without constraints rather than being blocked.

## `validate(artifact, scope, version?) -> object`

Selects in-scope constraints and evaluates each *bound* one against `artifact` by
delegating to the appropriate engine adapter (FR-VALIDATE). The artifact is never
modified (FR-VALIDATE-4).

**Input:** `artifact: object`, `scope: Scope`, `version?: string`.

**Output:**
```
{
  bundle_id: string,
  passed: boolean,             # false if any constraint verdict is fail/error
  results: [
    {
      constraint, title, severity,
      kind: "enforced" | "advisory",
      verdict: "pass" | "fail" | "error" | "informational",
      deprecated, successor,
      enforced_by: [ { engine, policy } ],
      violations: [ Violation ],
      guidance
    }
  ]
}
```

Advisory constraints in scope appear as `kind: "advisory"`, `verdict:
"informational"` with no engine involved (FR-VALIDATE-3). Unlike
`get_constraints`, `validate` MAY surface an explicit error (e.g. no servable
bundle) since it is an active check, returning `{ error, ... }`.
