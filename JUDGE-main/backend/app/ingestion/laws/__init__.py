"""Canadian law ingestion adapters.

Adapters for official Canadian legal sources:
1. Federal: Justice Laws Website XML
2. Saskatchewan: King's Printer / Freelaw
3. CanLII: Case law and legislation browser

All adapters store:
- jurisdiction (CA-FED, CA-SK, etc.)
- source_url
- consolidation_date
- raw_hash for audit trail

.. warning::
   This package is a STUB.  Coverage is incomplete and some adapters make
   direct ``httpx`` calls that bypass the SSRF-safe fetcher.  Do not import
   from general runtime code; tests must not invoke functional network calls.
"""

# Sentinel consumed by scripts/check_no_direct_ingestion_network_clients.py
# and the check_repo_boundaries guard.
NOT_RUNTIME: bool = True
