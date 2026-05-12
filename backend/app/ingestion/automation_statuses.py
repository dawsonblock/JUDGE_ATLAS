"""Canonical automation status constants for SourceRegistry.automation_status.

These constants drive two enforcement gates:

1. ``check_ingestion_allowed()`` in source_registry_ctl — rejects ingestion
   unless ``automation_status`` is in ``RUNNABLE_STATUSES``.
2. ``enable_source()`` in admin_sources — rejects enable unless
   ``automation_status`` is in ``ENABLEABLE_STATUSES``, then transitions to
   ``MACHINE_READY_ENABLED`` on success.
3. ``disable_source()`` in admin_sources — transitions
   ``MACHINE_READY_ENABLED → MACHINE_READY_DISABLED`` when disabling.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------

MACHINE_READY_DISABLED = "machine_ready_disabled"
MACHINE_READY_ENABLED = "machine_ready_enabled"
ADAPTER_MISSING = "adapter_missing"
PARSER_MISSING = "parser_missing"
NEEDS_ENDPOINT_CONFIGURATION = "needs_endpoint_configuration"
NEEDS_LEGAL_REVIEW = "needs_legal_review"
PORTAL_ONLY = "portal_only"
MANUAL_ONLY = "manual_only"
DISABLED_STUB = "disabled_stub"
QUARANTINED_SOURCE = "quarantined"

# ---------------------------------------------------------------------------
# Gate frozensets
# ---------------------------------------------------------------------------

#: Only a source with this status may transition to enabled via /enable.
ENABLEABLE_STATUSES: frozenset[str] = frozenset({MACHINE_READY_DISABLED})

#: Statuses that permit the scheduler to execute an ingestion run, provided
#: the source also has ``is_active=True``.
RUNNABLE_STATUSES: frozenset[str] = frozenset(
    {
        MACHINE_READY_ENABLED,
    }
)

#: The complete set of recognised automation status values.
ALL_AUTOMATION_STATUSES: frozenset[str] = frozenset(
    {
        MACHINE_READY_DISABLED,
        MACHINE_READY_ENABLED,
        ADAPTER_MISSING,
        PARSER_MISSING,
        NEEDS_ENDPOINT_CONFIGURATION,
        NEEDS_LEGAL_REVIEW,
        PORTAL_ONLY,
        MANUAL_ONLY,
        DISABLED_STUB,
        QUARANTINED_SOURCE,
    }
)
