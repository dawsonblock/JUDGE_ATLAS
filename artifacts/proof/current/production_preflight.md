# Production Preflight

- generated_at: 2026-05-13T00:09:22.940311+00:00
- checks_total: 10
- checks_passed: 2
- checks_failed: 8
- production_preflight_passed: false

## Checks

- FAIL production_environment_selected: ENVIRONMENT=dev
- FAIL strong_jwt_secret: JTA_JWT_SECRET must be set and >= 32 chars, non-default
- PASS legacy_admin_token_disabled: JTA_ENABLE_LEGACY_ADMIN_TOKEN must be false in production
- FAIL redis_rate_limit_configured: REDIS_URL must be configured
- FAIL evidence_store_root_configured: EVIDENCE_STORE_ROOT=unset
- FAIL cors_allowlist_not_wildcard: CORS_ALLOWLIST=unset
- FAIL egress_proxy_configured: JTA_FETCH_EGRESS_PROXY required unless JTA_ALLOW_DIRECT_FETCH_IN_NON_PROD=true
- FAIL database_url_configured: DATABASE_URL must be set
- PASS debug_mode_disabled: DEBUG must be false
- FAIL backup_policy_configured: BACKUP_POLICY must be documented/configured
