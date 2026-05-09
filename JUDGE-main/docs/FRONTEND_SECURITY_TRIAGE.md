# Frontend Security Vulnerability Triage

**Generated for JUDGE_ATLAS alpha gate — manual review required per release.**
**All entries below are triaged for alpha scope. Production release requires remediation or updated upstream fixes.**

---

## Summary

| Severity | Count |
|----------|-------|
| High     | 4     |
| Moderate | 6     |
| **Total**| **10** |

---

## Triage Entries

### 1. `glob` — HIGH — GHSA-5j98-mcp5-4vw2

- **Advisory**: <https://github.com/advisories/GHSA-5j98-mcp5-4vw2>
- **Severity**: High
- **Title**: glob CLI — Command injection via `-c`/`--cmd` flag executes matches as shell commands
- **Affected packages**: `glob` (pulled in by `eslint-config-next`, `@next/eslint-plugin-next`)
- **Triage decision**: **ACCEPTED — alpha scope**
  - `glob` is a devDependency used only during local linting/build on the developer workstation or CI.
  - The vulnerable `-c`/`--cmd` flag is a CLI feature; we do not invoke `glob` as a CLI tool in any script.
  - No user-controlled input reaches `glob` at runtime in this application.
  - Remediation blocked on upstream Next.js `eslint-config-next` releasing a patch.
- **Owner**: security-review-alpha
- **Status**: accepted-for-alpha / remediation-blocked-upstream

---

### 2. `@next/eslint-plugin-next` — HIGH (transitive via `glob`)

- **Severity**: High (transitive)
- **Affected packages**: `@next/eslint-plugin-next`
- **Triage decision**: **ACCEPTED — alpha scope** — same root cause as `glob` entry above; build-time only.
- **Owner**: security-review-alpha
- **Status**: accepted-for-alpha / remediation-blocked-upstream

---

### 3. `eslint-config-next` — HIGH (transitive via `@next/eslint-plugin-next`)

- **Severity**: High (transitive)
- **Affected packages**: `eslint-config-next`
- **Triage decision**: **ACCEPTED — alpha scope** — same root cause as `glob` entry above; build-time only.
- **Owner**: security-review-alpha
- **Status**: accepted-for-alpha / remediation-blocked-upstream

---

### 4. `next` — HIGH — GHSA-9g9p-9gw9-jx7f

- **Advisory**: <https://github.com/advisories/GHSA-9g9p-9gw9-jx7f>
- **Severity**: High
- **Title**: Next.js self-hosted applications vulnerable to DoS via Image Optimization
- **Affected packages**: `next`
- **Triage decision**: **ACCEPTED — alpha scope / NOT self-hosted image optimization in production**
  - JUDGE_ATLAS alpha does not expose the Next.js Image Optimization endpoint to the public internet.
  - Alpha deployments run behind an authenticated API gateway; the image route is not publicly reachable
    without authentication.
  - Remediation: upgrade `next` to patched version when available.
- **Owner**: security-review-alpha
- **Status**: accepted-for-alpha / track-upstream-patch

---

### 5. `postcss` — MODERATE — GHSA-qx2v-qp2m-jg93

- **Advisory**: <https://github.com/advisories/GHSA-qx2v-qp2m-jg93>
- **Severity**: Moderate
- **Title**: PostCSS — XSS via unescaped `</style>` in CSS Stringify output
- **Affected packages**: `postcss`
- **Triage decision**: **ACCEPTED — alpha scope**
  - PostCSS is used at build time to process CSS files only.
  - User input does not flow into PostCSS at runtime in JUDGE_ATLAS.
- **Owner**: security-review-alpha
- **Status**: accepted-for-alpha / remediation-blocked-upstream

---

### 6. `vitest` — MODERATE (transitive via Vite toolchain)

- **Severity**: Moderate (transitive)
- **Affected packages**: `vitest`
- **Triage decision**: **ACCEPTED — alpha scope**
  - Used only for local/CI contract tests (`npm run test:contracts`).
  - Not part of production runtime bundle.
  - Remediation tracked by routine dependency updates.
- **Owner**: security-review-alpha
- **Status**: accepted-for-alpha / dev-tooling-only

---

### 7. `vite` — MODERATE (transitive via Vitest)

- **Severity**: Moderate (transitive)
- **Affected packages**: `vite`
- **Triage decision**: **ACCEPTED — alpha scope**
  - Build/test infrastructure dependency only.
  - No direct user input path in production runtime.
- **Owner**: security-review-alpha
- **Status**: accepted-for-alpha / dev-tooling-only

---

### 8. `vite-node` — MODERATE (transitive via Vitest)

- **Severity**: Moderate (transitive)
- **Affected packages**: `vite-node`
- **Triage decision**: **ACCEPTED — alpha scope**
  - Executed only in local/CI test runs.
  - Not exposed as a network-facing runtime service.
- **Owner**: security-review-alpha
- **Status**: accepted-for-alpha / dev-tooling-only

---

### 9. `esbuild` — MODERATE (transitive build dependency)

- **Severity**: Moderate (transitive)
- **Affected packages**: `esbuild`
- **Triage decision**: **ACCEPTED — alpha scope**
  - Used by frontend build/test toolchain only.
  - No production endpoint executes esbuild directly.
- **Owner**: security-review-alpha
- **Status**: accepted-for-alpha / dev-tooling-only

---

### 10. `@vitest/mocker` — MODERATE (transitive via Vitest)

- **Severity**: Moderate (transitive)
- **Affected packages**: `@vitest/mocker`
- **Triage decision**: **ACCEPTED — alpha scope**
  - Testing-only helper package.
  - Not loaded in deployed application runtime.
- **Owner**: security-review-alpha
- **Status**: accepted-for-alpha / dev-tooling-only

---

## Attestation

All 10 vulnerabilities above have been reviewed for JUDGE_ATLAS alpha scope.
None of the affected packages process user input at runtime in JUDGE_ATLAS.
All are build-time devDependencies or are blocked by upstream package release schedules.

**This triage is valid for alpha only. Before any beta/production release, a full re-audit is required.**

---

*This file is required by `backend/scripts/check_npm_audit_triage.py` when `npm audit` reports vulnerabilities.*
