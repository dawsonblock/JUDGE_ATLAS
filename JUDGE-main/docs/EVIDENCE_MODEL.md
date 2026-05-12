# Evidence Model

**Status: alpha — immutable evidence lineage enforced**

---

## Overview

Every record in THE-JUDGE must be backed by an immutable evidence snapshot. No public record exists without a verified evidence chain.

---

## Evidence Snapshot (SourceSnapshot)

Each evidence snapshot stores:

| Field | Description |
|-------|-------------|
| `source_url` | URL from which evidence was fetched |
| `source_key` | Registry key of the source |
| `content_hash` | SHA-256 hash of the raw content |
| `original_content_hash` | Hash of original fetched content (never truncated) |
| `stored_content_hash` | Hash of what is actually stored (must equal original) |
| `fetched_at` | Timestamp when content was fetched |
| `extractor_name` | Parser/extractor that processed the content |
| `extractor_version` | Version of the parser used |
| `http_status` | HTTP status code of the fetch |
| `storage_backend` | Where raw content is stored (`db` or `file`) |
| `is_truncated` | Must always be `False` after successful write |

---

## Chain of Custody

Every state change to an evidence snapshot writes a `ChainOfCustodyLog` entry:

| Field | Description |
|-------|-------------|
| `snapshot_id` | Which snapshot was changed |
| `event_type` | Type of custody event (e.g. `created`, `verified`, `flagged`) |
| `actor_id` | Who performed the action |
| `actor_role` | Role at time of action |
| `note` | Description of the change |
| `created_at` | Timestamp |

Chain-of-custody events are **append-only** — no deletion is allowed.

---

## Visibility Rules

| Condition | Can be public |
|-----------|---------------|
| `review_status = pending_review` | ❌ Never |
| `review_status = approved` AND evidence present | ✅ Yes (reviewer must grant) |
| No evidence snapshot linked | ❌ Never |
| `public_visibility = False` | ❌ Never |

Only a reviewer (or higher role) can set `public_visibility = True`.

---

## Hash Integrity

- `content_hash` cannot be silently overwritten once set
- If `stored_content_hash != original_content_hash`, the snapshot is marked as corrupted
- The `/api/admin/snapshots/<id>/verify` endpoint checks hash integrity
- Mismatches raise an alert and are logged to the chain of custody

---

## ReviewItem Lifecycle

```
Ingested → ReviewItem(status=pending, public_visibility=False)
         → Reviewer decision → approved | rejected
         → If approved: Event/CrimeIncident created, still not public
         → Second gate: reviewer explicitly sets public_visibility=True
```

Two explicit gates are required before any record becomes public:
1. Review approval
2. Explicit public visibility grant

---

## Alpha Limitations

- Snapshot storage is in-database (`raw_content` column) by default; file-based storage available but not required
- Chain-of-custody log exists but replay/verification UI is not yet complete
- Duplicate detection between snapshots is partial (hash-based only; semantic dedup in AI module)
