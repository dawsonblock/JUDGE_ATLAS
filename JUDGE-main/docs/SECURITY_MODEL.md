# Security Model

**Status: alpha — not ready for production use**

## Overview

THE-JUDGE uses a layered, evidence-first security model. All mutation endpoints require authentication, authorization, and audit logging. No record is published without reviewer approval.

---

## Authentication

### JWT Authentication (primary, preferred)

- Access tokens: short-lived (30 minutes by default)
- Refresh tokens: longer-lived (7 days), **server-side revocable** via `UserSession`
- Refresh token hashes stored in `user_sessions` table — raw tokens are never persisted
- Login creates a `UserSession`; logout revokes it; logout-all revokes all user sessions
- Expired or revoked sessions are rejected at `/api/auth/refresh`

### Legacy Shared-Token Admin (deprecated, disabled by default)

- Controlled by `JTA_ENABLE_LEGACY_ADMIN_TOKEN` (default: `false`)
- Must never be enabled in production
- Will emit a `DeprecationWarning` at runtime if enabled
- Emits a startup warning when enabled
- Will be removed in a future release

---

## Roles

| Role         | Rank | Can view | Can review | Can manage sources | Can administer | Can create owners |
|--------------|------|----------|------------|-------------------|----------------|-------------------|
| viewer       | 0    | ✅        | ❌          | ❌                 | ❌              | ❌                 |
| reviewer     | 1    | ✅        | ✅          | ❌                 | ❌              | ❌                 |
| source_admin | 2    | ✅        | ✅          | ✅                 | ❌              | ❌                 |
| admin        | 3    | ✅        | ✅          | ✅                 | ✅              | ❌                 |
| owner        | 4    | ✅        | ✅          | ✅                 | ✅              | ✅                 |

Role enforcement uses `enforce_min_role()` in `app/auth/admin.py`. All mutation endpoints require at minimum `reviewer` role.

---

## RBAC Enforcement

Every mutation endpoint must:
1. Authenticate the actor (JWT Bearer or legacy shared-token if explicitly enabled)
2. Enforce minimum role via `enforce_min_role()`
3. Write an `AuditLog` entry with `actor_id`, `actor_type`, `actor_role`, and IP

Unauthenticated requests to mutation endpoints receive `403` or `401`.

---

## Audit Logging

All state changes are written to the `audit_logs` table with:
- `action`: the operation performed (e.g. `user.login`, `review.decision`)
- `actor_id`: email or stable label (never raw token value)
- `actor_type`: `user` | `shared_token`
- `actor_role`: the role at time of action
- `actor_ip`: client IP address
- `entity_type` / `entity_id`: what was changed
- `payload`: before/after state (no PII or secrets)

---

## Evidence Requirements

- No record may be published without at least one evidence snapshot
- No record may be public while `review_status = pending_review`
- Evidence snapshots are immutable — hashes cannot be silently overwritten
- Chain-of-custody events are written for every state change

---

## AI Constraints

AI modules are restricted to reviewer-assistance tasks only. See `AI_LIMITATIONS.md`.

AI output must not:
- Assign guilt
- Reach legal conclusions as facts
- Auto-publish records
- Score criminality
- Make unsourced accusations
- Infer identities

---

## Known Limitations (Alpha)

- Shared-token mode is available for local development only (`JTA_ENABLE_LEGACY_ADMIN_TOKEN=true`)
- MFA is not yet implemented
- OIDC/external IdP is not yet integrated
- Session management does not support concurrent device limits
