# Seabone Memory — dotmac_ecm

## Project Facts

### From README
> # DotMac ECM
> 
> An electronic content management application built on FastAPI with enterprise-grade features including authentication, RBAC, audit logging, background jobs, and full observability.
> 
> ## Features
> 
> - **Authentication & Security**
>   - JWT-based authentication with refresh token rotation
>   - Multi-factor authentication (TOTP, SMS, Email)
>   - API key management with rate limiting

### Stack Detection
- Build: pyproject.toml detected
- App dir: app/ present
- Tests: tests/ present

## Known Patterns

- **S3 IDOR via storage_key:** `DocumentVersionCreate.storage_key` accepts arbitrary paths; combined with the `/download-url` endpoint, any authenticated user can generate presigned URLs for any S3 object.
- **ACL enforcement gap:** DocumentACL and FolderACL models exist but are never consulted in document read/write/delete operations — all document access control is unenforced.
- **Regression pattern:** Three cycle-1 fixes (c1-6 webhook secret, c1-7 CORS, c1-10 cookie secure) did not persist in the codebase; PR merge process requires investigation.
- **Rate-limiting fail-closed:** Redis outage makes all auth endpoints return 503 (login, mfa/verify, refresh, forgot-password). Consider fail-open with warning log.
- **Audit entity_id injection:** `x-entity-id` HTTP header is still read directly into audit log entity_id field (actor was fixed but entity_id was not in c1-1).



- **Auth gating:** ECM routers use `require_user_auth` at `_include_api_router()` call; auth mgmt routes use `require_role("admin")`. Audit router uses its own `require_audit_auth`.
- **Audit actor injection:** `log_request()` in `app/services/audit.py:108-109` reads actor identity from raw HTTP headers — a systemic pattern to watch each cycle.
- **ORM-only queries:** No raw SQL string formatting found. All DB queries use SQLAlchemy ORM with parameterized filters.
- **Config defaults:** Settings in `app/config.py` use `os.getenv()` with fallback defaults — no hardcoded production secrets in app code, but default DB creds exist.
- **Webhook delivery:** Celery task `deliver_single_webhook` sends outbound HTTP POST with no URL denylist — SSRF vector. Endpoint schema accepts any URL string.
- **Crypto:** Passwords use pbkdf2_sha256+bcrypt (passlib). Refresh tokens use `secrets.token_urlsafe(48)`. API keys use unsalted SHA-256. TOTP secrets use Fernet encryption.
- **Refresh cookie:** Secure flag defaults to False (`app/services/auth_flow.py:153`).
- **Email template injection:** `send_password_reset_email` in `app/services/email.py:99` interpolates `person_name` into HTML without `html.escape()` — HTML injection risk.
- **ILIKE wildcard abuse:** `app/services/search.py:30` passes raw user input as ILIKE pattern without escaping `%`/`_` — DoS via expensive table scan.
- **Audit actor_type gap:** Auth dependencies (`require_user_auth`, `require_audit_auth`) set `request.state.actor_id` but not `request.state.actor_type`; audit logs always record `actor_type='system'` for user requests.
- **Common utility drift:** `app.services.common` exports `apply_ordering`/`apply_pagination` but 6 service files (audit, auth, domain_settings, person, rbac, scheduler) define private local copies — `notification.py` correctly imports from common.
- **Test state leakage:** `tests/conftest.py` `db_session` fixture uses a module-scoped `StaticPool` engine and closes without rollback; rows committed in one test persist for subsequent tests in the same session.
- **Celery no-retry pattern:** All Celery tasks use `ignore_result=True` with no `max_retries` or `default_retry_delay`; failures are silently dropped rather than retried.
- **Background task .all() risk:** Three Celery tasks (`reindex_all_documents` in `tasks/search.py:37`, `check_retention_expiry` in `tasks/retention.py:24`, `_find_and_queue` in `tasks/webhooks.py:47`) load unbounded result sets into memory with `.all()`. New periodic tasks must default to batch pagination.
- **Retention commit-per-loop:** `check_retention_expiry()` in `tasks/retention.py:37` calls `db.commit()` inside the for-loop, N times instead of 1 batch commit after the loop.
- **get_db() duplication:** 18 API router files each define an identical `get_db()` generator; should be centralized in `app/db.py` or a new `app/api/deps.py`.
- **get_db() split semantics:** The 18 `get_db()` copies are NOT identical — 9 ECM routers use `try/yield/commit/except rollback/finally close`, while 9 non-ECM routers (auth, rbac, persons, scheduler, notifications, webhooks, settings, audit, search) use `try/finally close` only. Services relying on the dependency to commit will silently lose data in the 9 basic-pattern routers.
- **Double router registration:** `main.py:_include_api_router()` registers every router twice (bare path + `/api/v1` prefix), causing all endpoints to appear twice in OpenAPI. Intentional versioning strategy but bloats docs.
- **Action endpoints lack response_model:** Non-CRUD POST action endpoints (mark-read, mark-all-read, tasks/refresh, tasks/enqueue) consistently lack `response_model` declarations — pattern to check on every new endpoint.
- **Pagination count bug:** Multiple endpoints return `count=len(items)` (page size) instead of total matching record count — found in search.py, ecm_checkouts.py, ecm_documents.py list_versions.
- **Actor-from-body pattern:** Several ECM action endpoints (checkout, dispose) take the acting-person identifier from the request body rather than the auth context — enables IDOR/impersonation. Fix by deriving from require_user_auth.
- **Auth endpoint rate-limit gap:** POST /auth/me/password (change_password) lacks rate limiting; all other sensitive auth endpoints (/login, /mfa/verify, /refresh, /forgot-password) are rate-limited.
- **Audit hard-delete:** DELETE /audit-events/{id} permanently removes rows; audit events should be immutable (soft-delete only).
- **Settings key unvalidated:** PUT /settings/{domain}/{key} accepts any free-form key string; no allowlist against seeded keys.
- **order_by unvalidated:** All 20+ list endpoints accept arbitrary `order_by` strings; invalid column names cause 500 errors potentially revealing DB schema.
- **coerce_uuid() ValueError → 500:** `app/services/common.py:11` raises `ValueError` on malformed UUID path params with no try/except — global handler returns 500 instead of 400 for all service methods.
- **Checkin auth bypass:** `app/api/ecm_checkouts.py:58-62` passes `co.checked_out_by` directly to checkin() bypassing the ownership check — any authenticated user can check in any document.
- **Soft-delete non-cascade:** `Folders.delete()` and `Categories.delete()` soft-delete only the target entity, leaving active children with an inactive parent — orphaned tree state.
- **Silent _compute_path fallback:** Both `Folders._compute_path()` (ecm_folder.py:118) and `Categories._compute_path()` (ecm_metadata.py:334) silently return root path when parent is missing, masking data corruption.

- **Deps fix workflow gap:** All 9 cycle-1 dependency fixes (deps-1 through deps-9) were documentation-only — fix agents wrote changelog entries but `pyproject.toml` was never modified. `git log -- pyproject.toml` confirms the file has not been touched since project initialization. Fix agents for deps upgrades must be instructed to modify pyproject.toml and regenerate the lock file, not just update CHANGELOG.md.
- **SQLAlchemy Session.bind deprecated:** `app/services/search.py:69` uses `db.bind.dialect.name`, using the deprecated `Session.bind` attribute (deprecated in SQLAlchemy 1.4, removal expected in future). Emits `SADeprecationWarning` in 2.0.x.
- **Missing __init__.py packages:** `app/api/` and `app/schemas/` have no `__init__.py` files; both are namespace packages. mypy and coverage tooling may behave unexpectedly.
- **Persons BOLA:** `/people` router uses only `require_user_auth`; any authenticated user can PATCH or DELETE any person record. No ownership or admin-role check in `app/api/persons.py`.
- **Webhook secret plaintext exposure:** `WebhookEndpointRead.secret` field in `app/schemas/webhook.py:78` returns the HMAC signing secret in all GET responses.
- **SSRF DNS rebinding bypass:** `_validate_webhook_url` in `app/schemas/webhook.py:30-32` blocks IP literals but returns any hostname immediately without DNS resolution — domain-based SSRF still possible.
- **MFA token replay:** `mfa_verify()` in `app/services/auth_flow.py:571` does not mark mfa_tokens as used; same token can be replayed within the 5-minute JWT validity window.
- **Missing CSP/HSTS headers:** `SecurityHeadersMiddleware` in `app/main.py:60` sets 4 security headers but omits Content-Security-Policy and Strict-Transport-Security.
- **Settings insufficient auth:** `settings_router` registered with `Depends(require_user_auth)` in `main.py:199` — any authenticated user can PUT to `/settings/auth/{key}` and change `jwt_secret` or `jwt_algorithm`, enabling DoS or algorithm downgrade. Should require `require_role("admin")`.
- **Admin session forging:** `POST /sessions` admin endpoint (app/api/auth.py:167) creates active AuthSession rows with arbitrary token_hash and person_id, enabling impersonation without a login audit trail.
- **Admin password_hash bypass:** `UserCredentialUpdate.password_hash` (app/schemas/auth.py:31) allows admins to set raw hash strings, bypassing hash_password() and enabling credential takeover.
- **Notification IDOR cluster:** Five notification endpoints lack ownership checks — GET /notifications (person_id query param), mark-all-read (person_id from body), mark-read (no ownership on IDs), GET /notifications/{id}, DELETE /notifications/{id}.
- **S3 key path traversal:** `generate_storage_key()` (ecm_storage.py:38) embeds user-supplied file_name directly in the S3 key without sanitizing `..` sequences.
- **MIME type not allowlisted in upload-url:** `UploadURLRequest.mime_type` is passed to S3 ContentType without validation; dangerous types (text/html) could be stored and served.
- **Dead notification email task:** `send_notification_email` in `tasks/notifications.py:94` is registered as a Celery task but is never dispatched from `_dispatch()`; email delivery is silently non-functional.
- **Asymmetric empty-list event matching:** `_matches_event()` (notifications) returns False for empty subscribed_types (subscriber gets nothing), while `_endpoint_matches()` (webhooks) returns True for empty event_types (endpoint gets everything) — opposite semantics.
- **Legal hold hard-delete:** `LegalHoldDocuments.delete()` uses `db.delete(lhd)` (hard delete) while all other ECM entities soft-delete with `is_active=False`.
- **Audit settings thundering herd:** `_load_audit_settings()` in `main.py:115` uses double-check locking incorrectly — releases lock between check and DB query, allowing N concurrent cache-miss threads to all query DB simultaneously.
- **Password reset token race:** `reset_password()` in `auth_flow.py:767` reads and marks the reset token used without a row-level lock, allowing concurrent requests to use the same token twice.
- **Service self-commit pattern:** `notification.py` and `webhook.py` service methods call `db.commit()` directly instead of `db.flush()`, inconsistent with ECM services that rely on router-level commit. This is required because those routers use the basic get_db() with no auto-commit.
- **Workflow task complete auth gap:** `POST /ecm/workflow-tasks/{task_id}/complete` has no assignee ownership check; any authenticated user can approve/reject any task.
- **Empty search DoS:** `search.py:21` allows `q=""` (min_length=0, default=""), which passes as a wildcard ILIKE pattern causing a full-table sequential scan on every request.
- **notification_ids unbounded bulk write:** `MarkReadRequest.notification_ids: list[UUID]` in `schemas/notification.py:29` has no max length — unbounded bulk UPDATE via single authenticated request.
- **status_filter no enum validation:** Multiple list endpoints (collaboration, workflows, retention) accept `status_filter: str | None` without enum validation; invalid values silently return 0 results instead of HTTP 422.
- **list_checkouts no filters:** `GET /ecm/documents/checkouts` accepts only limit/offset with no person_id/document_id/status filter — impossible to query checkouts by owner or document.
- **auth_flow handler direct commit:** Six handlers in `auth_flow.py` (update_me, upload_avatar, delete_avatar, revoke_session, revoke_all_other_sessions, change_password) call `db.commit()` directly in handler code rather than through a service method — mixes persistence into the API layer.

- **Actor-from-body cluster grows:** Cycle 12 found 3 more actor-from-body IDOR endpoints: `WebhookEndpointCreate.created_by`, `CommentCreate.author_id`, `DocumentSubscriptionCreate.person_id`. Pattern now spans 5+ endpoints (checkout, dispose, webhook, comment, subscription). All must be fixed by deriving identity from `require_user_auth` server-side.
- **Avatar upload DoS:** `save_avatar()` in `app/services/avatar.py:52` reads the entire file into memory before the size check; concurrent large uploads can exhaust heap.
- **Notification IDOR extended:** `GET /notifications/unread-count` (notifications.py:26) is a 6th IDOR endpoint not captured in the cycle-8 cluster finding; it takes `person_id` as a required query param with no ownership check.
- **Audit soft-delete confirmed fixed:** `AuditEvents.delete()` now sets `is_active = False` (soft-delete), resolving the cycle-7 hard-delete finding.

- **Undeclared transitive deps used directly:** `app/services/ecm_storage.py:5` imports `from botocore.config import Config` directly, and `python-multipart` is consumed via FastAPI file uploads — both are transitive-only in poetry.lock, not declared in pyproject.toml. Pattern to check for in every feature using AWS SDK or form parsing.
- **pytest.ini warning suppression masking debt:** `pytest.ini` has 3 `filterwarnings = ignore:...` entries silencing python-multipart import-path, passlib crypt deprecation, and utcnow deprecation — these mask real unresolved dependency issues instead of fixing them.
- **Python <3.13 constraint is passlib workaround:** `pyproject.toml` limits to `<3.13` to prevent passlib failure on Python 3.13 (where `crypt` module was removed). This blocks Python 3.13 adoption and must be resolved by migrating away from passlib.
- **typing.List legacy in notification.py:** `app/services/notification.py:5` uses `from typing import List` — a legacy import on Python 3.11+ where built-in `list[X]` should be used.

## Quality Scan History

| Date | Cycle | Findings |
|------|-------|----------|
| 2026-02-27 | quality-cycle2 | 23 (2 critical, 4 high, 10 medium, 7 low) — health: 68/100; trend: stable |
| 2026-02-27 | api-cycle3 | 15 (0 critical, 5 high, 5 medium, 5 low) — health: 65/100; trend: first API scan |
| 2026-02-27 | api-cycle7 | 11 (0 critical, 3 high, 5 medium, 3 low) — health: 58/100; trend: degrading. 26 total open (c3 unresolved). New: change_password no rate-limit, GET /me/sessions unbounded, dispose IDOR, audit hard-delete, search count bug, settings key unvalidated, 404 undocumented. |
| 2026-02-27 | quality-cycle6 | 10 (0 critical, 2 high, 6 medium, 2 low) — health: 62/100; trend: degrading. 11 cycle-2 findings still open. New: checkin bypass, coerce_uuid→500, subscription dup, webhook rollback, mark_all_read unbounded, subtree .all(), non-cascade delete, silent fallback (meta). |
| 2026-02-28 | quality-cycle9 | 11 (0 critical, 2 high, 6 medium, 3 low) — health: 57/100; trend: degrading. No fixes confirmed. New: send_notification_email dead code, workflow task complete no assignee check, _matches_event empty-list asymmetry, legal hold hard-delete, audit settings thundering herd, response_model=dict on checkin, test client missing auth router override, service self-commit pattern, password reset race condition, double flush, bad type annotation. |
| 2026-02-28 | api-cycle10 | 11 (0 critical, 2 high, 6 medium, 3 low) — health: 52/100; trend: degrading. No fixes confirmed. New: empty search q DoS, notification_ids unbounded bulk write, mark-read/mark-all-read no response_model, scheduler action endpoints no response_model, list_checkouts no filters, status_filter no enum validation, auth_flow handler direct db.commit(), list endpoint return type mismatch, mfa-setup person_id in body. |

## Recurring Issues

- Audit actor spoofing (header-based) — first flagged cycle 1
- Missing rate limiting on auth endpoints — first flagged cycle 1
- Webhook SSRF (no URL validation) — first flagged cycle 1

## Deps Scan History

| Date | Cycle | Findings |
|------|-------|----------|
| 2026-02-27 | deps-cycle1 | 9 (1 critical, 2 high, 3 medium, 3 low) — health: ~67/100; first scan |
| 2026-02-27 | deps-cycle4 | 11 (0 critical, 2 high, 5 medium, 4 low) — health: 61/100; trend: degrading. 8 regressions (all fixes documentation-only, pyproject.toml never modified). 4 new: Session.bind deprecated, fastapi outdated, missing __init__.py x2. |
| 2026-02-28 | deps-cycle11 | 7 (0 critical, 0 high, 4 medium, 3 low) — health: 55/100; trend: degrading. No fixes from cycle 4. New: botocore undeclared, python-multipart undeclared, pytest.ini warning suppression masking debt, Python <3.13 constraint passlib workaround, typing.List legacy, missing boto3-stubs, Session unused in email.py. |

## Security Scan History

| Date | Cycle | Findings |
|------|-------|----------|
| 2026-02-27 | cycle1 | 13 (1 critical, 4 high, 5 medium, 3 low) — health: 55/100 |
| 2026-02-27 | cycle1 rescan | 16 total (3 new: c1-14 medium, c1-15 low, c1-16 low); 3 confirmed fixed; health: 67/100; trend: improving |
| 2026-02-27 | cycle2 | 11 (0 critical, 4 high, 5 medium, 2 low) — health: 63/100; trend: degrading. 3 regressions: c1-6 (webhook secret), c1-7 (CORS), c1-10 (cookie secure). |
| 2026-02-27 | cycle5 | 9 (0 critical, 3 high, 4 medium, 2 low) — health: 58/100; trend: degrading. New: Persons BOLA, webhook secret plaintext exposure, SSRF DNS rebinding bypass, missing rate-limit on reset-password, MFA token replay, missing CSP, audit entity_id header injection, HSTS missing, cookie Secure regression. Confirmed fixed: email HTML injection (c1-14), ILIKE wildcard (c1-15). |
| 2026-02-28 | cycle8 | 10 (0 critical, 3 high, 5 medium, 2 low) — health: 53/100; trend: degrading. New: settings any-user PUT (jwt_secret/algorithm), admin session forging, admin password_hash bypass, S3 path traversal via file_name, MIME type not validated, notification IDOR cluster (5 endpoints). No fixes confirmed since cycle5. |
| 2026-02-28 | cycle12 | 8 (0 critical, 1 high, 5 medium, 2 low) — health: 49/100; trend: degrading. No fixes confirmed. New: mfa/confirm no rate-limit, notification unread-count IDOR (6th), webhook created_by body, comment author_id body, subscription person_id body, avatar upload DoS, comment body unbounded, event_types uncapped. Confirmed fixed: audit soft-delete, ILIKE wildcards. |

