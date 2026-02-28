# Security Scan Report — Cycle 2
**Date:** 2026-02-27
**Scanner:** Seabone Sentinel
**Scope:** Full application security review (all Python source files)

---

## Summary

| Severity | Count |
|----------|-------|
| High     | 4     |
| Medium   | 5     |
| Low      | 2     |
| **Total**| **11**|

**Codebase Health Score: 63/100** *(down from 67/100 at last rescan — trend: degrading)*

The dominant finding of this cycle is **regressions**: three issues that were triaged, assigned to agents, and marked as merged in cycle 1 are still present in the codebase. Either the PRs were merged without actually applying the changes, or subsequent merges reverted them. Additionally, two new high-severity authorization issues were discovered in the ECM document layer.

---

## Detailed Findings

### HIGH — security-c2-1
**File:** `app/services/auth_flow.py:155`
**REGRESSION (c1-10):** `_refresh_cookie_secure()` still returns `False` by default. Fix was supposedly merged but code is unchanged. Refresh tokens transmitted over HTTP in any environment where `REFRESH_COOKIE_SECURE` is not explicitly set.

### HIGH — security-c2-2
**File:** `app/schemas/webhook.py:77`
**REGRESSION (c1-6):** `WebhookEndpointRead` still exposes the `secret` field in full. The HMAC signing secret is returned to any authenticated user who reads or lists webhook endpoints. Fix agent was supposedly merged but schema unchanged.

### HIGH — security-c2-3
**File:** `app/schemas/ecm.py:103` / `app/services/ecm_document.py:216`
**NEW — S3 Storage Key IDOR:** `DocumentVersionCreate.storage_key` accepts any string (up to 1024 chars) with no path-prefix validation. An authenticated user can POST `/ecm/documents/{id}/versions` with `storage_key = "other-tenant/private.pdf"` and then call `GET /ecm/documents/{id}/versions/{vid}/download-url` to obtain a presigned S3 URL for any object in the bucket. This bypasses all document ownership controls.

### HIGH — security-c2-4
**File:** `app/api/ecm_documents.py:41`
**NEW — ACL Enforcement Gap:** The document router authenticates users via `require_user_auth` but performs zero ACL checks during get, list, update, delete, or download-url operations. The `DocumentACL` / `FolderACL` tables are populated by the ACL management API but their rules are never consulted. Any authenticated user can read, modify, or delete any document in the system.

### MEDIUM — security-c2-5
**File:** `app/main.py:49`
**REGRESSION (c1-7):** No `CORSMiddleware` is registered. The API has no cross-origin resource sharing policy. Malicious browser-based pages can make credentialed cross-origin requests to all API endpoints.

### MEDIUM — security-c2-6
**File:** `app/services/audit.py:111`
**NEW — Audit entity_id Header Injection:** `log_request()` reads `entity_id` from the `x-entity-id` HTTP header. Any client can forge arbitrary entity IDs in audit log entries, falsely associating audit events with documents/folders they never accessed. (Actor identity injection was fixed in c1-1, but entity_id injection was not.)

### MEDIUM — security-c2-7
**File:** `app/api/auth_flow.py:87`
**NEW — Rate Limit Fail-Closed DoS:** `_rate_limit_dependency` raises HTTP 503 when Redis is unreachable. A Redis outage or targeted disruption makes login, MFA verify, token refresh, and forgot-password completely inaccessible system-wide — an authentication DoS with an easily triggered vector.

### MEDIUM — security-c2-8
**File:** `app/schemas/webhook.py:30`
**NEW — SSRF via DNS Rebinding:** The `_validate_webhook_url` validator only checks IP-literal hostnames against the RFC-1918 blocklist. Domain names (e.g., `internal.corp.example.com`) bypass all IP checks even if they resolve to `192.168.x.x`. DNS rebinding and internal DNS records remain viable SSRF vectors despite the partial fix from c1-2.

### MEDIUM — security-c2-9
**File:** `app/api/auth_flow.py:511`
**NEW — No Password Complexity Enforcement:** `change_password` and `reset_password` endpoints apply no minimum length or character-class requirements. A user can set a single-character password.

### LOW — security-c2-10
**File:** `app/services/ecm_storage.py:39`
**NEW — Unsanitized file_name in S3 Key:** `generate_storage_key` embeds `file_name` directly into the S3 object key without stripping path separators or traversal sequences. A crafted `file_name` such as `../../tenant2/secret.pdf` creates an S3 key outside the expected namespace.

### LOW — security-c2-11
**File:** `app/api/auth_flow.py:536`
**NEW — Timing Oracle for Email Enumeration:** `forgot_password` skips `send_password_reset_email` for unknown emails, adding SMTP latency only for known addresses. A timing attack reveals whether an email is registered despite the uniform 200 response.

---

## Comparison with Previous Scans

| Status | Count | Notes |
|--------|-------|-------|
| Newly fixed since rescan | 0 confirmed | Could not verify any cycle-1 fixes actually landed |
| Regressions detected | 3 | c1-6, c1-7, c1-10 show unchanged code despite "merged" status |
| New findings | 8 | ECM layer mostly unscanned until now |
| Still open from cycle 1 (unverified) | 13 | c1-3,4,8,9,11,12,13,14,15,16 + variants |

**Critical concern:** Three separate findings (c2-1, c2-2, c2-5) correspond to issues that were supposedly fixed in cycle 1. The merge history shows PRs were created, but the live code does not reflect those changes. This indicates either a broken merge workflow, a rebase/reset that lost changes, or the auto-fix agents produced PRs against stale branches.

---

## Top 3 Priority Fixes

### 1. Fix ACL enforcement (security-c2-4) — HIGH / medium effort
The entire document access control system is inoperative. Every document in the ECM is accessible to any authenticated user. This should be the highest priority as it renders all ACL management useless.

### 2. Fix storage_key IDOR (security-c2-3) — HIGH / small effort
An authenticated user can generate presigned download URLs for any S3 object in the bucket. Add a path-prefix validator on `DocumentVersionCreate.storage_key`. Trivially exploitable by any authenticated user.

### 3. Confirm and re-apply regressed fixes (security-c2-1, c2-2, c2-5) — HIGH / trivial effort (×3)
Three previously-triaged fixes did not land. Re-applying them is trivial (single-line changes each). The merge/integration process needs investigation to prevent future regressions.

---

## Codebase Health Score

**63 / 100** *(previous: 67/100)*

| Factor | Assessment |
|--------|-----------|
| Auth system | Good — rate limiting, refresh rotation, MFA all functional |
| Authorization | Poor — ACL model exists but unenforced |
| Secrets handling | Acceptable — HMAC in place, Fernet TOTP encryption |
| Input validation | Fair — ORM parameterized, some gaps in ECM layer |
| Regression rate | Concerning — 3/16 cycle-1 fixes did not persist |
| New attack surface | Moderate — ECM S3 layer and audit injection are new vectors |

**Trend: Degrading** — The regression discovery drops the score below the previous rescan level. While the auth layer improved significantly in cycle 1, the ECM document layer introduced new high-severity authorization gaps that were not present in scope before.

---

*Generated by Seabone Sentinel v2 · 2026-02-27*
