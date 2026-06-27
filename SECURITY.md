# Security Policy

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

If you believe you have found a security vulnerability in Constraint Registry,
report it privately so we can fix it before it is widely known. Use either:

- GitHub's **[Private vulnerability reporting](https://github.com/SureshKhemka/constraints-registry/security/advisories/new)**
  (Security → Report a vulnerability), or
- email **sureshkhemka@gmail.com** with the details.

Please include, where possible:

- a description of the issue and its impact,
- the version / commit you tested,
- step-by-step reproduction (a minimal proof of concept is ideal),
- any suggested remediation.

We will acknowledge your report within a few business days, keep you updated on
progress, and credit you in the release notes unless you prefer to remain
anonymous.

## Scope and threat model notes

Constraint Registry **invokes external policy engines** (OPA, Conftest, Checkov,
Semgrep) as subprocesses and evaluates artifacts supplied to the `validate` tool.
When assessing a report, the following are useful to keep in mind:

- Adapters run engine binaries with argument **lists** (never `shell=True`) and
  enforce timeouts; the artifact under test is written to a temp file/tree and is
  **never executed**.
- A constraint's `policy` locator is resolved **relative to its owning source
  directory**; report any path-traversal that escapes that boundary.
- The MCP `get_constraints` path is designed to **fail open** so an agent is
  never blocked; report any input that can crash the server or cause it to serve
  a stale/incorrect bundle silently.

## Supported versions

This project is pre-1.0 and moves quickly. Security fixes are applied to `main`
and released from there. Please test against the latest `main` before reporting.
