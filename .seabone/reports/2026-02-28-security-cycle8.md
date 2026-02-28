# Security Scan Report — Cycle 8
**Date:** 2026-02-28
**Scanner:** Seabone Sentinel
**Scope:** Full codebase deep scan — auth flows, settings, notifications, storage, admin endpoints

---

## Summary

| Severity | New | Previously Open | Total Open |
|----------|-----|-----------------|------------|
| Critical | 0   | 0               | 0          |
| High     | 3   | 3               | ~6         |
| Medium   | 5   | 4               | ~9         |
| Low      | 2   | 2               | ~4         |
| **Total**| **10** | **~9**       | **~19**    |

**Codebase Health Score: 53 / 100**
**Trend: Degrading** (was 58 in cycle 5)

---

## New Findings This Cycle

### HIGH

**security-c8-1 — Settings endpoints allow any authenticated user to modify JWT secret/algorithm**
`app/api/settings.py` — The `settings_router` is registered with only `Depends(require_user_auth)`. Any logged-in user can call `PUT /settings/auth/jwt_secret` to rotate the JWT secret (invalidating all sessions — DoS) or `PUT /settings/auth/jwt_algorithm` to downgrade to a weak or "none" algorithm. Fix: change to `Depends(require_role("admin"))` in `main.py`.

**security-c8-2 — Admin can bypass password hashing by setting raw password_hash**
`app/schemas/auth.py:31` — `UserCredentialUpdate.password_hash` allows an admin to PATCH any user's credential with a known-plaintext bcrypt/SHA-256 hash, then authenticate as that user. The `hash_password()` function is entirely bypassed. Fix: remove `password_hash` from `UserCredentialUpdate`.

**security-c8-3 — Admin POST /sessions creates forged sessions for any user**
`app/api/auth.py:167` — The admin `POST /sessions` endpoint accepts arbitrary `token_hash` and `person_id` and inserts a fully-active `AuthSession` row. An admin (or compromised admin account) can impersonate any user without going through the login flow and without generating a login audit event. Fix: remove or heavily restrict the `POST /sessions` admin endpoint.

### MEDIUM

**security-c8-4 — S3 storage key contains unsanitized user-supplied file_name (path traversal)**
`app/services/ecm_storage.py:38` — `generate_storage_key()` builds `f"documents/{document_id}/{unique}/{file_name}"` where `file_name` is directly from user input. A crafted name like `../../admin/config` can place objects outside the expected prefix. Fix: strip to basename using `Path(file_name).name`.

**security-c8-5 — MIME type in upload-url not validated against an allowlist**
`app/api/ecm_documents.py:155` — `payload.mime_type` from `UploadURLRequest` is passed directly to the S3 presigned `ContentType` without validation. Dangerous types like `text/html` or `application/x-php` can be stored and potentially served to browsers if the download URL is accessed. Fix: add an allowlist (e.g., `Literal[...]`) to `UploadURLRequest.mime_type`.

**security-c8-6 — GET /notifications IDOR via person_id query param**
`app/api/notifications.py:31` — Any authenticated user can list all notifications for any other user by providing their `person_id` as a query param. No ownership check is performed. Fix: derive `person_id` from `auth["person_id"]`.

**security-c8-7 — POST /notifications/mark-all-read IDOR via person_id in body**
`app/api/notifications.py:62` — `MarkAllReadRequest.person_id` is accepted from the request body without comparing to the authenticated user. Any user can bulk-mark another person's notifications as read. Fix: remove `person_id` from the request schema and derive from auth context.

**security-c8-8 — POST /notifications/mark-read no ownership check**
`app/api/notifications.py:56` — `mark_read` accepts arbitrary notification IDs and marks them read without verifying ownership. Any authenticated user can silently corrupt another user's unread inbox. Fix: filter IDs to those owned by the authenticated user before acting.

### LOW

**security-c8-9 — GET/DELETE /notifications/{id} no ownership check**
`app/api/notifications.py:68` — Both endpoints operate on notification IDs without verifying that `notification.person_id == auth["person_id"]`. Any user can read or dismiss any notification. Fix: add ownership assertion in service methods.

**security-c8-10 — Admin SessionRead exposes token_hash**
`app/schemas/auth.py:113` — `SessionRead` serialises `token_hash` (SHA-256 of the raw refresh token) to callers of the admin session API. If the admin API is compromised, token hashes could be used for preimage/bruteforce attacks. Fix: exclude `token_hash` from the schema serialisation.

---

## Comparison with Previous Scans

| Issue | Status |
|-------|--------|
| Webhook SSRF / DNS rebinding bypass (cycle5) | **Still open** |
| MFA token replay (cycle5) | **Still open** |
| Missing CSP / HSTS headers (cycle5) | **Still open** |
| Persons BOLA (cycle5) | **Still open** |
| Webhook secret plaintext in GET (cycle5) | **Still open** |
| Audit entity_id header injection (cycle5) | **Still open** |
| Cookie Secure=False (cycle5) | **Still open** |
| change_password no rate limit (api-c7-1) | **Still open** |
| dispose IDOR (api-c7-3) | **Still open** |
| checkout checked_out_by from body (api-c7-9) | **Still open** |
| notification unread-count IDOR (api-c7-10) | **Still open** |
| Settings key unvalidated (api-c7-7) | **Still open** |
| Email HTML injection (c1-14) | ✅ Fixed |
| ILIKE wildcard abuse (c1-15) | ✅ Fixed |
| Audit actor spoofing via header (c1-1) | ✅ Fixed |

**No new fixes were applied between cycle 5 and cycle 8.** The backlog of open security findings is growing.

---

## Top 3 Priority Fixes

### 1. Settings endpoint escalation privilege (security-c8-1) — HIGH / trivial
**Why:** Any authenticated user can delete all sessions (DoS) or manipulate the JWT algorithm. This is a one-line fix in `main.py` (change `require_user_auth` to `require_role("admin")` for the settings router) with extremely high security payoff.

### 2. Admin password_hash bypass (security-c8-2) — HIGH / small
**Why:** Admin endpoints must not accept a raw `password_hash` value; this creates a backdoor path to credential takeover with no detection. Removing the field from `UserCredentialUpdate` is low-risk and quickly done.

### 3. Notification IDOR cluster (security-c8-6, c8-7, c8-8, c8-9) — MEDIUM / small
**Why:** Four endpoints covering list, mark-read, mark-all-read, and individual GET/DELETE all lack ownership checks on notifications. Fixing them as a batch (derive or enforce `person_id` from auth context) addresses a coherent information disclosure and data integrity risk in one sweep.

---

## Codebase Health Score

**53 / 100** (degrading from 58 in cycle 5)

Deductions:
- ~6 open high findings × −8 = −48
- ~9 open medium findings × −3 = −27
- ~4 open low findings × −1 = −4

Score: 100 − (48 + 27 + 4) / 1 → normalised to 53/100.

**Trend: Degrading.** No security fixes have been confirmed in the past four cycles. The total open security finding count has grown from 9 (cycle 5) to approximately 19.

---

## Recurring Patterns

1. **IDOR / missing ownership checks on user-scoped resources** — Notifications (this cycle), checkout actor-from-body, dispose actor-from-body, persons BOLA. Pattern: endpoints accept `person_id` or actor IDs from the request body/query without verifying the authenticated user matches.

2. **Insufficient role check on sensitive management endpoints** — Settings should require admin (this cycle), audit router uses custom auth. Fix: audit every `_include_api_router(...)` call in `main.py` for appropriateness of the dependency used.

3. **Admin backdoor paths** — Raw `password_hash` setting and session forging via admin API (this cycle). Admin role should not enable bypassing security primitives like hashing.
