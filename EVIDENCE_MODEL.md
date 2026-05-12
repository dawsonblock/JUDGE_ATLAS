# EVIDENCE MODEL

## Canonical Entities
- `SourceSnapshot`: immutable evidence payload and provenance/hash metadata.
- `ChainOfCustodyLog`: explicit custody event logging.
- `AuditLog`: append-only operator/reviewer action records.
- `SourceRegistry`: governed source definitions and policy controls.

## Core Guarantees
- Derived records should always carry snapshot references where applicable.
- Integrity checks must detect hash or immutable-field corruption.
- Review/publication history is recoverable from audit records.

## Constraints
- No derived claim should exist without traceable evidence lineage.
- No publication flow should bypass review authority.
