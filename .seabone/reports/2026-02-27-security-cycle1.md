# Security Scan Report — 2026-02-27 (Cycle 1, Rescan)

## Summary

Security rescan of the dotmac_ecm codebase following the first round of fixes. Three confirmed
fixes have landed on main (PRs #2 and #4 merged), seven more are in active worktrees, and three
new findings were discovered.

| Severity | Open on main | In-progress (worktrees) | Fixed (merged) |
|----------|-------------|-------------------------|----------------|
| Critical | 0           | 0                       | 1 (c1-1)       |
| High     | 1           | 1 (c1-3)                | 2 (c1-2, c1-5) |
| Medium   | 2 (+ 1 new) | 4 + 1 (c1-10)           | 0              |
| Low      | 2 (+ 2 new) | 1 (c1-11)               | 0              |
| **Total**| **8**       | **7**                   | **3**          |

---

## Comparison with Previous Findings

### Fixed since last scan (confirmed merged to main)

| ID | Severity | Fix |
|----|----------|-----|
| security-c1-1 | **Critical** | Audit actor spoofing: `log_request()` now reads from `request.state` instead of raw headers. PR #2 merged. |
| security-c1-2 | **High** | Webhook SSRF: `WebhookEndpointCreate` now validates URLs via `_validate_webhook_url()`, rejecting RFC-1918/loopback targets and non-HTTP(S) schemes. PR #4 merged. |
| security-c1-5 | **High** | `.env.agent-swarm` added to `.gitignore` (confirmed present at line 40). |

### In progress (worktrees created, not yet merged)

`c1-3` (rate limiting), `c1-6` (webhook secret in schema), `c1-7` (CORS), `c1-8` (unsalted API keys),
`c1-9` (avatar magic-bytes), `c1-10` (refresh cookie secure), `c1-11` (security headers).

### Still open — no worktree

- `security-c1-4` (high): Password reset token reuse
- `security-c1-12` (low): `/metrics` unauthenticated
- `security-c1-13` (low): Hardcoded DB default credentials

### New findings (3)

| ID | Severity | File | Issue |
|----|----------|------|-------|
| security-c1-14 | **Medium** | app/services/email.py:99 | HTML injection in password-reset email via unescaped `person_name` |
| security-c1-15 | **Low** | app/services/search.py:30 | ILIKE wildcard not escaped — authenticated users can trigger expensive table scans |
| security-c1-16 | **Low** | app/services/auth_dependencies.py:157 | `request.state.actor_type` never set; audit logs record `system` for all user requests |

---

## Top 3 Priority Fixes

### 1. `security-c1-4` — Password Reset Token Reuse (High)
**File:** `app/services/auth_flow.py:756`

`reset_password()` decodes and validates the JWT, then immediately updates the credential — but never
records that the token was consumed. Within the 60-minute default TTL window, the same link can be
used repeatedly to change the password again. An attacker who intercepts a reset email link can
exploit it any number of times until expiry.

Fix: Persist the token's `jti` (or SHA-256 hash) to a Redis key with the token's remaining TTL,
and reject any token whose hash already appears in the blacklist before processing.

---

### 2. `security-c1-12` — Unauthenticated `/metrics` Endpoint (Low → operational priority)
**File:** `app/main.py:221`

`GET /metrics` returns full Prometheus output — request rates per route, error counts, latency
histograms — with zero authentication. This exposes internal route names, traffic patterns, and
error rates to any anonymous client. Easily fixed with a single shared-secret dependency.

Fix: Add a Bearer-token check (shared secret from env var `METRICS_TOKEN`) to the `/metrics`
handler; deny with 401 if missing or incorrect.

---

### 3. `security-c1-14` — HTML Injection in Password Reset Email (Medium, New)
**File:** `app/services/email.py:99`

```python
body_html = (
    f"<p>Hi {name},</p>"          # name is person.display_name or first_name — unescaped
    "<p>Use the link below …</p>"
    f'<p><a href="{reset_link}">Reset password</a></p>'
)
```

If a user's `display_name` contains HTML (e.g., `</p><script>…</script>`), it is injected verbatim
into the outgoing email body. While script execution is blocked by most email clients, it enables
link injection, spoofed content, and phishing via forged-looking emails.

Fix: `import html` and wrap the name with `html.escape(name)` before interpolation. Trivial one-liner.

---

## All Open Findings

| ID | Severity | File | Status | Issue |
|----|----------|------|--------|-------|
| security-c1-4  | **High**   | app/services/auth_flow.py:756     | Open       | Password reset token not invalidated after use |
| security-c1-6  | **Medium** | app/schemas/webhook.py:77         | Worktree   | Signing secret exposed in webhook read schema |
| security-c1-7  | **Medium** | app/main.py:46                    | Worktree   | No CORS middleware |
| security-c1-8  | **Medium** | app/services/auth.py:55           | Worktree   | API keys hashed with unsalted SHA-256 |
| security-c1-9  | **Medium** | app/services/avatar.py:15         | Worktree   | Avatar type validated by Content-Type header only |
| security-c1-10 | **Medium** | app/services/auth_flow.py:153     | Worktree   | Refresh cookie secure flag defaults to False |
| security-c1-14 | **Medium** | app/services/email.py:99          | **New**    | HTML injection in password-reset email |
| security-c1-11 | **Low**    | app/main.py:54                    | Worktree   | No HTTP security response headers |
| security-c1-12 | **Low**    | app/main.py:221                   | Open       | /metrics endpoint unauthenticated |
| security-c1-13 | **Low**    | app/config.py:13                  | Open       | Default database credentials in config fallback |
| security-c1-15 | **Low**    | app/services/search.py:30         | **New**    | ILIKE wildcard abuse enables expensive table scans |
| security-c1-16 | **Low**    | app/services/auth_dependencies.py:157 | **New** | audit actor_type always recorded as 'system' |

---

## What the Codebase Does Well

- **Password hashing:** pbkdf2_sha256 (primary) + bcrypt (legacy) via passlib — strong choices.
- **Refresh token rotation:** Detects and revokes on token reuse — good security practice.
- **Account lockout:** 5 failed attempts → 15-minute lock per credential.
- **TOTP secret encryption:** MFA secrets stored encrypted with Fernet (AES-128-CBC).
- **JWT session validation:** Access tokens are validated against a live session record in DB (not just signature).
- **Secure token generation:** `secrets.token_urlsafe(48)` for refresh tokens — correct.
- **Webhook SSRF (fixed):** URL denylist now covers RFC-1918, loopback, link-local, and non-HTTP(S) schemes.
- **Audit integrity (fixed):** Actor identity now sourced from `request.state`, not spoofable HTTP headers.
- **RBAC coverage:** All ECM endpoints gated behind `require_user_auth`; admin routes behind `require_role("admin")`.

---

## Codebase Health Score

**67 / 100** (up from 55 / 100 at last scan)

Scoring delta:
- Critical eliminated (c1-1 fixed): +15
- 2 high findings fixed (c1-2, c1-5): +8
- 7 more fixes in progress: +5 projected
- 3 new findings discovered: −6

---

## Trend

**Improving** — The most severe finding (critical audit integrity) has been eliminated and two highs
were merged. Seven more fixes are actively in-progress in worktrees. Three new low/medium issues
were found, but all are trivial-to-small effort to fix.

---

## Notes

- Worktree branches confirm PM has already dispatched agents for c1-3, c1-6, c1-7, c1-8, c1-9, c1-10, c1-11.
- `c1-4` (password reset token reuse) has a worktree log (`fix-security-c1-4.log`) but no visible worktree — verify PM status.
- The `deliver_single_webhook` task correctly uses `hmac.new(secret, body, sha256)` for HMAC signing — no issues there.
- The OpenBao/Vault secret resolver (`app/services/secrets.py`) uses env-controlled addresses only — no SSRF risk.
- No raw SQL string formatting found anywhere in the codebase — ORM parameterization is consistent.
