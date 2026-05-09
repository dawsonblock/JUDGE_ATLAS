# CURRENT LIMITATIONS

## Product Limits
- Source quality depends on upstream source stability and legality of access.
- Not all jurisdictions/sources are machine-ingestable.
- Some ingestion paths remain manual or portal-reference only.

## Technical Limits
- Audit chain verification is currently replay-based from append-only ordering; full persisted block-link columns are not yet implemented.
- Verification tools are CLI-driven and must be wired into CI as required gates.
- Legacy admin shared-token compatibility exists for non-mutation routes; mutation hardening favors JWT roles.

## Operational Limits
- Publication throughput is bounded by reviewer capacity.
- False positives/ambiguity can still occur in extraction and must be handled in review.
- Proof artifacts can become stale; they must be regenerated for each release candidate.
