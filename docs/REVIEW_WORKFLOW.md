# Review Workflow

**Status: alpha — human reviewer required for all publication**

---

## Overview

No record in THE-JUDGE becomes publicly visible without an explicit reviewer decision. This is a mandatory two-gate process:

1. **Review gate**: A reviewer approves or rejects the record
2. **Visibility gate**: A reviewer explicitly grants public visibility

---

## Review Queue

All ingested records enter the `ReviewItem` queue with:
- `status = pending`
- `public_visibility = False`
- `reviewer_status = unreviewed`

The queue is accessible via:
- UI: `/admin/review`
- API: `GET /api/admin/review-queue`

---

## Reviewer Roles

| Role | Can review | Can grant public visibility | Can reject |
|------|------------|----------------------------|------------|
| viewer | ❌ | ❌ | ❌ |
| reviewer | ✅ | ✅ | ✅ |
| source_admin | ✅ | ✅ | ✅ |
| admin | ✅ | ✅ | ✅ |
| owner | ✅ | ✅ | ✅ |

---

## Review Decision Actions

| Action | Status After | Public After |
|--------|-------------|--------------|
| `approve` | approved | Still private (requires explicit visibility grant) |
| `reject` | rejected | No |
| `flag_for_edit` | flagged | No |
| `grant_visibility` | approved | Yes |

---

## Evidence Requirements for Approval

A reviewer cannot approve a record that:
- Has no linked `SourceSnapshot`
- Has a corrupted evidence hash
- Has `is_truncated = True` on its snapshot

---

## Audit Trail

Every review action writes:
- `ReviewActionLog` entry (before/after state, actor, timestamp)
- `AuditLog` entry (action, actor_id, actor_role, entity)

---

## Bulk Review

Bulk approval is not permitted. Each record must be individually reviewed to prevent mass errors.

---

## Alpha Limitations

- Reviewer UI exists but is not fully production-hardened
- Email notifications on queue items are not yet implemented
- SLA / review-time tracking is not yet implemented
- Dispute workflow exists in the model but is not fully surfaced in the UI
