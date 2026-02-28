# Security Scan Report — Cycle 5
**Date:** 2026-02-27
**Scanner:** Seabone Sentinel
**Files reviewed:** app/services/auth_flow.py, auth.py, audit.py, email.py, webhook.py, search.py, ecm_document.py, ecm_acl.py, ecm_storage.py, avatar.py, secrets.py; app/api/auth.py, auth_flow.py, persons.py, ecm_documents.py, webhooks.py; app/schemas/auth.py, ecm.py, webhook.py; app/main.py, app/config.py, app/errors.py; app/tasks/webhooks.py

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 0     |
| High     | 3     |
| Medium   | 4     |
| Low      | 2     |
| **Total**| **9** |

**Codebase health score: 58 / 100**
**Trend: degrading** (was 63/100 in cycle 2)

---

## New Findings This Cycle

### HIGH

#### security-c5-1 — Persons BOLA (Broken Object Level Authorization)
**File:** `app/api/persons.py:46`
Any authenticated user can `PATCH /people/{person_id}` or `DELETE /people/{person_id}` for ANY person, including other users. The people router is registered with only `require_user_auth` — no ownership check and no admin-role requirement. This allows horizontal privilege escalation: any user can overwrite another user's email, name, or other PII fields, or soft-delete any account.

#### security-c5-2 — Webhook Signing Secret Exposed in Read Responses
**File:** `app/schemas/webhook.py:78`
`WebhookEndpointRead.secret: str | None` includes the raw HMAC signing secret in every GET response. Any authenticated user with access to the webhooks API can retrieve the signing secrets of all other users' webhook endpoints, allowing them to forge webhook payloads that will pass signature verification on external systems.

#### security-c5-3 — SSRF via Webhook DNS Rebinding (Partial Fix Bypass)
**File:** `app/schemas/webhook.py:30-32`
The `_validate_webhook_url` validator blocks IP-literal private addresses but performs no DNS resolution. Any hostname (e.g., `evil.example.com`) that resolves to `127.0.0.1`, `169.254.169.254`, or another private IP bypasses the check entirely. An attacker can register a domain with split-horizon DNS or use a DNS rebinding service to make the Celery worker call internal services.

---

### MEDIUM

#### security-c5-4 — Missing Rate Limit on /auth/reset-password
**File:** `app/api/auth_flow.py:547`
`POST /auth/reset-password` has no rate-limiting dependency. The companion `POST /auth/forgot-password` is rate-limited at 3/min. While reset tokens are JWTs (hard to brute-force), the endpoint is open to denial-of-service and token-grinding attacks with no throttling.

#### security-c5-5 — MFA Token Not Invalidated After Use
**File:** `app/services/auth_flow.py:571`
`mfa_verify()` decodes and validates the mfa_token JWT but never marks it as consumed. The token is valid for 5 minutes. If intercepted (e.g., via a compromised network), the same mfa_token can be replayed with the current TOTP code to create additional sessions within the validity window.

#### security-c5-6 — Missing Content-Security-Policy Header
**File:** `app/main.py:60`
`SecurityHeadersMiddleware` sets X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, and Referrer-Policy but omits `Content-Security-Policy`. Without CSP, any XSS vulnerability in the web_home page or future HTML-rendered content has no browser-level mitigation.

#### security-c5-7 — Audit entity_id Injected via HTTP Header (Ongoing)
**File:** `app/services/audit.py:111`
`entity_id = request.headers.get("x-entity-id")` is still reading entity_id directly from a user-controlled HTTP header with no authentication or validation. This is a companion bug to the actor_id injection that was fixed in c1-1 — any unauthenticated caller can forge the entity_id field in audit log entries, undermining audit trail integrity.

---

### LOW

#### security-c5-8 — Missing Strict-Transport-Security (HSTS) Header
**File:** `app/main.py:60`
`SecurityHeadersMiddleware` does not add a `Strict-Transport-Security` header. Browsers will not upgrade HTTP connections to HTTPS automatically, leaving room for SSL stripping attacks.

#### security-c5-9 — Refresh Cookie Secure Defaults to False (Regression)
**File:** `app/services/auth_flow.py:155`
`_refresh_cookie_secure()` still returns `False` when not configured. The refresh token HttpOnly cookie is sent over plain HTTP in any default deployment. This is a confirmed regression of the c1-10 fix that has now persisted through cycles 2–5.

---

## Comparison With Previous Cycle (Cycle 2, health 63/100)

### Confirmed Fixed Since Cycle 1/2
| Issue | Where Fixed |
|-------|-------------|
| Email HTML injection (c1-14) | `app/services/email.py:96` — `html.escape()` now applied |
| ILIKE wildcard DoS (c1-15) | `app/services/search.py:33` — `%` and `_` now escaped |

### Still Open From Previous Cycles
| Issue | First Reported | Status |
|-------|---------------|--------|
| S3 IDOR via DocumentVersionCreate.storage_key | cycle-2 HIGH | Open — no path validation on storage_key field |
| ACL enforcement gap (DocumentACL / FolderACL never consulted) | cycle-2 HIGH | Open — document ops never check ACL tables |
| Refresh cookie Secure = False (regression) | c1-10 → cycle-2 | Open — re-reported as c5-9 |

### New in Cycle 5
9 new findings: 3 high, 4 medium, 2 low — see above.

---

## Top 3 Priority Fixes

1. **security-c5-1 — Persons BOLA** (HIGH, trivial-small effort)
   Any user can modify any other user. Add ownership check or admin gate to the `/people` PATCH and DELETE endpoints. Highest impact since it directly enables account takeover / PII tampering.

2. **security-c5-2 — Webhook secret plaintext exposure** (HIGH, trivial effort)
   Remove `secret` from `WebhookEndpointRead`. One-line fix; prevents exfiltration of HMAC signing secrets that protect webhook delivery integrity.

3. **security-c5-3 — SSRF DNS rebinding bypass** (HIGH, small effort)
   Add DNS resolution at validation time and apply the private-IP denylist to resolved addresses. Without this, the existing SSRF fix is bypassable with a simple attacker-controlled domain.

---

## Codebase Health

**Score: 58 / 100** (down from 63 in cycle 2)

Scoring penalties:
- 3 open HIGH findings from cycle 2 that weren't fixed (S3 IDOR, ACL enforcement, regression cookie): −15
- 3 new HIGH findings this cycle: −15
- 4 new MEDIUM findings: −12

The net improvement (2 fixes since cycle 2) is outweighed by 9 new findings discovered this cycle.

**Trend: degrading**
