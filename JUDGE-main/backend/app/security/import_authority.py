"""Import authority dependency — re-exports from app.auth.admin.

``require_import_actor`` is the canonical actor-returning dependency for all
admin import/ingestion mutation routes.  It is aliased here so that routes can
import from ``app.security.import_authority`` if preferred, and so that the
name clearly communicates intent (returns an ``AdminActor``, not ``None``).
"""

from __future__ import annotations

from app.auth.admin import require_admin_imports as require_import_actor

__all__ = ["require_import_actor"]
