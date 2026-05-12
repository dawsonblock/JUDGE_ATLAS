# Dependency Remediation Plan (Frontend Audit)

## Scope

This plan converts alpha triage outcomes into explicit remediation tasks for frontend dependency vulnerabilities.

## Current State

- `npm audit` currently reports 10 vulnerabilities.
- Vulnerabilities are triaged for alpha scope in `docs/FRONTEND_SECURITY_TRIAGE.md`.
- Triage is not production remediation.

## Production Gate Rule

No production-readiness claim is allowed while high vulnerabilities remain unresolved, unless a formal security exception is documented and approved.

## Remediation Task Matrix

| Package/Class | Severity | Dependency Path | Alpha Acceptance Reason | Affected Surface | Remediation Option | Owner | Target Date/Release | Production Gate Status |
|---|---|---|---|---|---|---|---|---|
| glob | High | eslint-config-next -> @next/eslint-plugin-next -> glob | build-time toolchain only, no runtime CLI `--cmd` usage | lint/build tooling | upgrade via upstream Next.js ecosystem updates | owner-tbd | before beta gate | blocked until remediated/exception |
| @next/eslint-plugin-next | High | transitive via eslint-config-next | build-time only | lint tooling | upgrade to patched upstream | owner-tbd | before beta gate | blocked until remediated/exception |
| eslint-config-next | High | direct dev dependency | build-time only | lint tooling | upgrade to patched version | owner-tbd | before beta gate | blocked until remediated/exception |
| next (image optimization DoS advisory) | High | direct dependency | alpha deployment posture, non-public image optimization path | frontend server runtime | upgrade to patched Next.js release and re-verify exposure | owner-tbd | before beta gate | blocked until remediated/exception |
| postcss | Moderate | transitive build dependency | build-time css processing only | build pipeline | upgrade transitives via lockfile refresh | owner-tbd | next dependency refresh window | tracked |
| vitest | Moderate | dev test dependency | CI/local contracts only | test tooling | upgrade vitest and peer deps | owner-tbd | next dependency refresh window | tracked |
| vite | Moderate | transitive via test/build tooling | tooling only | test/build tooling | upgrade vite ecosystem | owner-tbd | next dependency refresh window | tracked |
| vite-node | Moderate | transitive via vitest | tooling only | test tooling | upgrade via vitest/vite updates | owner-tbd | next dependency refresh window | tracked |
| esbuild | Moderate | transitive build dependency | tooling only | build tooling | pin/upgrade to patched range | owner-tbd | next dependency refresh window | tracked |
| @vitest/mocker | Moderate | transitive via vitest | tooling only | test tooling | upgrade vitest stack | owner-tbd | next dependency refresh window | tracked |

## Required Update Cadence

- Re-audit `npm audit` at least once per release cycle.
- Update this matrix when advisories change.
- Record remediation completion in PRs that bump dependencies.

## Notes

- This plan does not suppress findings.
- This plan does not imply production-readiness or legal authority.
