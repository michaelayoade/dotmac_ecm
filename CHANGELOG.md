# Changelog

All notable changes to dotmac_ecm are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased] — 2026-02-28

### Added

- [Added] GitHub Actions CI workflow: runs on push/PR to `main`; steps include dependency install, `ruff` lint, `mypy` type-check, and `pytest` test suite with PostgreSQL service container (commit b34e907)

---

## [Unreleased] — 2026-02-27

### Security

- [Security] Exclude `.env.agent-swarm` from version control to prevent live API credentials from being committed (PR #1)
- [Security] Fix audit log actor spoofing: actor identity now sourced from `request.state` instead of client-controlled HTTP headers `x-actor-type` / `x-actor-id` (PR #2)
- [Security] Fix webhook SSRF: `WebhookEndpointCreate.url` now rejects non-HTTP(S) schemes, loopback addresses, link-local ranges, and RFC 1918 private IP ranges using stdlib `ipaddress` + `urllib.parse` (PR #4)
- [Security] Fix refresh cookie `Secure` flag: `_refresh_cookie_secure()` now defaults to `True`; set `REFRESH_COOKIE_SECURE=false` to override for local development (PR #3)
- [Security] Add per-IP rate limiting to auth endpoints via slowapi/Redis: `POST /auth/login` 5/min, `POST /auth/forgot-password` 3/min, `POST /auth/mfa/verify` 5/min, `POST /auth/refresh` 10/min (PR #5)
- [Security] Fix password reset token reuse: token record is deleted immediately after a successful password reset, preventing replay attacks if a token is intercepted post-use (PR #11)
- [Security] Fix webhook signing secret exposure: `WebhookEndpointRead` no longer returns the raw `secret` field; replaced with a boolean `has_secret` indicator (PR #6)
- [Security] Add CORS middleware: `CORSMiddleware` configured via `CORS_ALLOW_ORIGINS` env var (comma-separated); `allow_credentials=True` is set only when origins list does not contain a wildcard (PR #10)
- [Security] Fix API key hashing: replaced unsalted SHA-256 with HMAC-SHA256 keyed by `HMAC_SECRET` env var; lookup uses `hmac.compare_digest` for constant-time comparison (PR #9)
- [Security] Fix avatar upload type spoofing: magic-byte validation added after file receipt — accepts JPEG (FF D8 FF), PNG (89 50 4E 47), GIF (47 49 46 38), WebP (52 49 46 46 … 57 45 42 50); returns HTTP 415 on mismatch (PR #7)
- [Security] Add HTTP security response headers middleware: every response now includes `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin` (PR #8)
- [Security] Protect `/metrics` endpoint: requires `Authorization: Bearer <METRICS_API_KEY>` header; returns 403 when `METRICS_API_KEY` env var is not configured (PR #14)
- [Security] Remove hardcoded default database credentials: `DATABASE_URL` with embedded `postgres:postgres` credentials is replaced — non-development environments now raise `ValueError` at startup if `DATABASE_URL` is unset (PR #12)
- [Security] Fix HTML injection in password reset email: `person_name`/`display_name` is now wrapped with `html.escape()` before interpolation into the HTML email body, preventing phishing via crafted display names (PR #13)
- [Security] Fix ILIKE wildcard abuse in document search: `%` and `_` characters in the search query are now escaped before being passed to the ILIKE pattern, preventing expensive full-table scans via wildcard injection (PR #15)
- [Security] Fix audit log actor_type gap: `require_user_auth` now sets `request.state.actor_type = "user"` and the API-key branch of `require_audit_auth` sets `request.state.actor_type = "api_key"`, so audit records correctly identify non-system actors (PR #16)

### Dependencies

- [Security] Replace python-jose 3.3.0 with joserfc >=0.12.0: fixes CVE-2024-33664 and CVE-2024-33663 (algorithm confusion attack allowing JWT signature bypass via algorithm switching); all JWT encode/decode paths migrated to joserfc with explicit `algorithms` kwarg to reject `none` algorithm (PR #24)
- [Security] Upgrade jinja2 from 3.1.4 to >=3.1.6: fixes CVE-2024-56201 and CVE-2024-56326 (sandbox escape via `__init__.__globals__` and `|attr` filter) (PR #19)
- [Changed] Upgrade cryptography from 42.0.8 to >=46.0.0: picks up 4 major versions of security patches for certificate validation and memory safety (PR #18)
- [Changed] Upgrade OpenTelemetry instrumentation packages from beta 0.47b0 to >=0.50b0: moves `opentelemetry-instrumentation-fastapi`, `-sqlalchemy`, and `-celery` from beta to stable releases (PR #17)
- [Changed] Upgrade httpx from 0.27.0 to >=0.28.0: includes security hardening around redirect handling and SSL certificate verification defaults (PR #20)
- [Changed] Upgrade pydantic from 2.7.4 to >=2.10.0 and pydantic-core accordingly: picks up validation fixes and performance improvements from the 2.10.x series (PR #22)
- [Changed] Upgrade python-dotenv from 1.0.1 to >=1.2.1: aligns with current release and picks up latest fixes (PR #23)
