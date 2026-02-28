# Security Scan Report — Cycle 12
**Date:** 2026-02-28
**Scan type:** Security
**Files examined:** app/api/auth_flow.py, app/api/auth.py, app/main.py, app/services/auth_flow.py, app/services/auth_dependencies.py, app/services/avatar.py, app/services/audit.py, app/services/search.py, app/services/email.py, app/services/webhook.py, app/services/ecm_storage.py, app/services/secrets.py, app/api/ecm_documents.py, app/api/ecm_checkouts.py, app/api/ecm_legal_holds.py, app/api/ecm_workflows.py, app/api/ecm_retention.py, app/api/ecm_collaboration.py, app/api/ecm_acl.py, app/api/notifications.py, app/api/webhooks.py, app/api/search.py, app/api/audit.py, app/api/deps.py, app/schemas/auth_flow.py, app/schemas/ecm_collaboration.py, app/schemas/webhook.py, app/config.py, app/errors.py

---

## Summary

**8 new findings** (0 critical, 1 high, 5 medium, 2 low)

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 1 |
| Medium | 5 |
| Low | 2 |

**Codebase health score: 49/100** (down from 53/100 in cycle 8)
**Trend: Degrading** — no fixes confirmed since cycle 5; backlog continues to grow.

---

## New Findings

### HIGH

**security-c12-1 — `/mfa/confirm` no rate limiting (brute-forceable TOTP)**
`app/api/auth_flow.py:177`
`POST /auth/mfa/confirm` carries no `_rate_limit_dependency`. An attacker who obtains a valid `method_id` UUID can issue rapid requests to brute-force the 6-digit TOTP confirmation code (10^6 possibilities) within a 30-second window. Fix: add `dependencies=[Depends(_rate_limit_dependency('mfa_confirm', 5))]`.

---

### MEDIUM

**security-c12-2 — Notification unread-count IDOR (6th endpoint)**
`app/api/notifications.py:26`
`GET /notifications/unread-count` requires a `person_id` query parameter with no ownership check, letting any authenticated user probe any other user's unread count. This extends the cycle-8 "Notification IDOR cluster" finding from 5 to 6 endpoints.

**security-c12-3 — Webhook `created_by` from request body (actor-from-body IDOR)**
`app/schemas/webhook.py:48`
`WebhookEndpointCreate.created_by` is a user-controlled UUID field. Any authenticated user can register a webhook endpoint attributed to an arbitrary other person. Fix: derive `created_by` from `require_user_auth` on the server side.

**security-c12-4 — Comment `author_id` from request body (actor-from-body IDOR)**
`app/schemas/ecm_collaboration.py:17`
`CommentCreate.author_id` is user-supplied, allowing any authenticated user to post ECM comments appearing to come from another user — content forgery, audit log pollution, and reputational damage. Fix: inject `author_id` from auth context.

**security-c12-5 — DocumentSubscription `person_id` from request body (actor-from-body IDOR)**
`app/schemas/ecm_collaboration.py:48`
`DocumentSubscriptionCreate.person_id` is user-controlled. Any user can subscribe documents on behalf of any other person, causing unsolicited notification delivery. Fix: inject `person_id` from auth context.

**security-c12-6 — Avatar upload reads full file into memory before size check (DoS)**
`app/services/avatar.py:52`
`save_avatar()` calls `await file.read()` to load the entire upload into memory before the `len(content) > avatar_max_size_bytes` check. With default 2 MB limit, concurrent requests from an attacker could allocate hundreds of MB of heap space before being rejected. Fix: stream content in chunks or enforce Content-Length at the middleware layer.

---

### LOW

**security-c12-7 — Comment body unbounded**
`app/schemas/ecm_collaboration.py:16`
`CommentBase.body: str` has no `max_length` constraint, enabling DB bloat and memory pressure on list queries.

**security-c12-8 — Webhook event_types list uncapped**
`app/schemas/webhook.py:47`
`WebhookEndpointCreate.event_types: list[str]` has no per-item `max_length` or max list size; an attacker can register thousands of event type strings, bloating DB rows and forcing O(N) matching per event.

---

## Comparison with Previous Security Scans

| Cycle | New | Open (cumulative) | Health |
|-------|-----|-------------------|--------|
| cycle1 (rescan) | 16 | 13 | 67 |
| cycle2 | 11 | ~14 open | 63 |
| cycle5 | 9 | ~16 open | 58 |
| cycle8 | 10 | ~18 open | 53 |
| **cycle12** | **8** | **~26 open** | **49** |

### Still open (unresolved from previous cycles)
- **c1-16**: Refresh cookie `Secure` flag defaults False (regression)
- **c5**: Persons BOLA (`/people` PATCH/DELETE no ownership check)
- **c5**: Webhook secret plaintext in GET response
- **c5**: SSRF DNS rebinding bypass on webhook URL validation
- **c5**: MFA token replay (mfa_verify does not mark token used)
- **c5**: Missing CSP / HSTS headers
- **c5**: Audit entity_id injection via `x-entity-id` header
- **c5**: Rate limit missing on `POST /auth/reset-password`
- **c8**: Settings PUT insufficient auth (any user can write jwt_secret)
- **c8**: Admin session forging (`POST /sessions` admin endpoint)
- **c8**: Admin `password_hash` bypass
- **c8**: S3 key path traversal via `file_name`
- **c8**: MIME type not allowlisted in upload-url
- **c8**: Notification IDOR cluster (5 endpoints)
- **Actor-from-body pattern**: checkout `checked_out_by`, dispose `disposed_by` (cycles 6/7)
- **Checkin auth bypass** (cycle 6)
- **Workflow task complete no assignee check** (cycle 9)

### Confirmed fixed since cycle 8
- Audit hard-delete: `AuditEvents.delete()` now soft-deletes with `is_active = False` ✓
- ILIKE wildcard injection: `search.py:33` now escapes `%` and `_` ✓
- Email HTML injection: `html.escape(name)` is present in `send_password_reset_email` ✓

---

## Top 3 Priority Fixes

1. **`/mfa/confirm` brute-force** (security-c12-1, High, trivial effort)
   One-line fix: add a rate-limit dependency to the route decorator. Prevents TOTP brute-force during MFA setup.

2. **Actor-from-body cluster** (c12-3, c12-4, c12-5 + existing c8/c9 instances, Medium)
   The pattern now spans 5+ endpoints: checkout, dispose, webhook create, comment create, subscription create. A single sweep to replace body-sourced actor IDs with auth-derived ones would close all of them.

3. **Notification IDOR cluster** (c12-2 + c8's 5 endpoints = 6 total, Medium, trivial)
   Six notification endpoints accept user-supplied `person_id` without ownership checks. All can be fixed by comparing against `require_user_auth` output.

---

## Codebase Health Score

**49 / 100**

Deductions:
- 3 High-severity open issues (−15)
- ~15 Medium-severity open issues (−30)
- ~6 Low-severity open issues (−6)
- Recurring unfixed patterns (actor-from-body, notification IDOR, no rate-limit) (−0, already counted)

**Trend: Degrading** — cycle 8 was 53, cycle 12 is 49. No security fixes have been deployed since cycle 5 (email HTML injection and ILIKE wildcard). The backlog of open security findings has grown from ~13 (cycle 1) to ~26 (cycle 12 estimate). Immediate action on the three priority items above is recommended.
