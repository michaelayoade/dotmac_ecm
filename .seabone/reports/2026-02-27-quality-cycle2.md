# Seabone Quality Scan — Cycle 2 (Refreshed)
**Date:** 2026-02-27
**Scan type:** quality
**Files scanned:** ~90 Python files (app/, tests/)
**Previous scan:** 2026-02-27 08:05 (18 findings); this refresh adds 5 new findings

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 2 |
| High | 4 |
| Medium | 10 |
| Low | 7 |
| **Total** | **23** |

**Codebase health score: 68/100**
**Trend: stable** (vs. 72/100 at previous quality scan; 5 additional findings, no new criticals)

The application logic remains solid. This refresh surfaces additional memory-efficiency issues in background tasks (retention, webhook fan-out), a commit-per-record pattern in the retention task, an 18-way duplication of `get_db()` across router files, and a redundant `db.flush()` in the checkout service. All new findings are medium or low severity.

---

## Top 3 Priority Fixes

### 1. SMTP Connection Resource Leak (`app/services/email.py:67`) — CRITICAL
The SMTP server object is created inside `try:` but `server.quit()` is only on the success path. Any exception after connection creation (STARTTLS failure, login failure, send failure) leaks the socket. Fix is a one-liner `finally:` block.

### 2. Scheduler Tests Accept HTTP 500 (`tests/test_api_scheduler.py:185`) — CRITICAL
`test_refresh_schedule` and `test_enqueue_scheduled_task` accept 500 as a valid response. This means Celery/broker errors silently pass CI. Mock the Celery broker and assert exact status codes.

### 3. `_apply_ordering`/`_apply_pagination` Duplicated Across 6 Services — MEDIUM
Identical implementations exist in `audit.py`, `auth.py`, `domain_settings.py`, `person.py`, `rbac.py`, and `scheduler.py`. `app.services.common` already exports `apply_ordering` and `apply_pagination` — `notification.py` already uses them correctly. The 6 other files just need their local copies deleted and an import added.

---

## All Findings

### Critical

| ID | File | Line | Issue |
|----|------|------|-------|
| quality-c2-1 | app/services/email.py | 67 | SMTP socket leak on exception path |
| quality-c2-2 | tests/test_api_scheduler.py | 185 | Tests accept HTTP 500 as passing |

### High

| ID | File | Line | Issue |
|----|------|------|-------|
| quality-c2-3 | app/services/notification.py | 61 | N+1: mark_read issues one SELECT per notification ID |
| quality-c2-4 | app/tasks/notifications.py | 8 | Celery tasks have no retry config — failures silently dropped |
| quality-c2-5 | tests/test_api_auth_flow.py | 62 | 7 tests accept `status_code in [401, 404]` — masks wrong error codes |
| quality-c2-6 | app/tasks/search.py | 37 | reindex_all_documents loads entire Document table into memory |

### Medium

| ID | File | Line | Issue |
|----|------|------|-------|
| quality-c2-7 | app/services/audit.py (×6 files) | 10 | _apply_ordering/_apply_pagination duplicated in 6 files |
| quality-c2-8 | app/api/auth_flow.py | 380 | list_sessions endpoint unbounded — no limit/offset |
| quality-c2-9 | tests/conftest.py | 131 | db_session fixture no rollback — test state leaks between tests |
| quality-c2-10 | app/services/ecm_folder.py | 118 | _compute_path silently masks orphaned-folder corruption |
| quality-c2-11 | app/api/auth_flow.py | 338 | upload_avatar no error handling around save_avatar() |
| quality-c2-12 | app/api/search.py | 42 | search count = len(page) not total match count |
| quality-c2-13 | tests/test_api_ecm_acl.py | 65 | No 403 tests for ACL enforcement |
| quality-c2-19 ★ NEW | app/tasks/retention.py | 37 | db.commit() called per-record inside loop — N round-trips instead of 1 |
| quality-c2-20 ★ NEW | app/tasks/retention.py | 24 | check_retention_expiry loads all expired retentions into memory |
| quality-c2-21 ★ NEW | app/tasks/webhooks.py | 47 | _find_and_queue loads all active endpoints into memory before filtering |

### Low

| ID | File | Line | Issue |
|----|------|------|-------|
| quality-c2-14 | tests/test_ecm_acl_services.py | 23 | Duplicate test helpers shadow conftest fixtures |
| quality-c2-15 | tests/test_api_ecm_acl.py | 13 | Duplicate test helpers shadow conftest fixtures |
| quality-c2-16 | app/services/notification.py | 37 | Legacy `List[Notification]` type hint |
| quality-c2-17 | tests/test_event_services.py | 13 | Hardcoded EventType count == 25 breaks on additions |
| quality-c2-18 | app/services/auth_flow.py | 436 | login() has 4 concerns — extract lockout/MFA helpers |
| quality-c2-22 ★ NEW | app/api/ecm_documents.py (×18 files) | 24 | get_db() defined identically in 18 router files |
| quality-c2-23 ★ NEW | app/services/ecm_checkout.py | 44 | Redundant db.flush() call after IntegrityError guard |

---

## Comparison with Previous Findings

### What's New (5 findings added in refresh)

| ID | Description |
|----|-------------|
| quality-c2-19 | `tasks/retention.py` — commit-per-record in retention expiry loop |
| quality-c2-20 | `tasks/retention.py` — all expired retentions loaded into memory |
| quality-c2-21 | `tasks/webhooks.py` — all active endpoints loaded into memory |
| quality-c2-22 | `get_db()` duplicated across 18 API router files |
| quality-c2-23 | `ecm_checkout.py` — redundant `db.flush()` after IntegrityError guard |

### Pattern: Background Task Memory Risk (c2-6, c2-20, c2-21)
Three Celery tasks (`reindex_all_documents`, `check_retention_expiry`, `_find_and_queue`) all use `.all()` to load an unbounded set of ORM objects. This is a systemic pattern — any new periodic task should default to batch pagination.

### Pattern: Commit Efficiency (c2-19)
The retention expiry task issues N `db.commit()` calls in a loop. This is a distinct sub-pattern from the existing N+1 query finding (c2-3) — it's N write transactions instead of 1.

### Pattern: get_db() Duplication (c2-22)
18 API router files each define an identical `get_db()` generator. This is the same duplication disease as `_apply_ordering` (c2-7) but broader and simpler to fix.

### Still Open from Previous Cycle
- All 18 previous quality findings remain open (no fixes observed for quality issues yet)
- Security cycle-2 fixes in progress: c2-1 (cookie secure), c2-2 (webhook secret), c2-5 (CORS), c2-7 (rate-limit), c2-10 (storage key)

### Confirmed Fixed (security/deps before this cycle)
- All cycle-1 security findings (c1-1 through c1-16) confirmed merged
- deps-2 (jinja2), deps-4 (cryptography), deps-5 (OTel), deps-6 (httpx) upgraded
- Email HTML injection escaped in `email.py:96` (now uses `html.escape`)

---

## Effort Distribution

| Effort | Count | Auto-fixable |
|--------|-------|-------------|
| trivial | 8 | 7 |
| small | 14 | 1 |
| medium | 1 | 0 |

---

## Health Score Rationale

**68/100** — Down from 72/100 (5 new findings discovered in refresh).

Deductions from 100:
- −10 for 2 criticals (test reliability + SMTP leak)
- −8 for 4 high findings (N+1, no retries, ambiguous test assertions, memory risk)
- −10 for 10 medium findings
- −4 for 7 low findings

The codebase retains its strong structural foundation — no SQL injection, no major auth flaws, and broad test coverage. Primary quality debt remains test reliability, service-layer inefficiencies, and growing background-task memory risk.

---

## Trend

**Stable** vs. previous quality scan (72/100 → 68/100). The 4-point drop reflects incremental discoveries in areas not previously inspected (retention task, webhooks task, checkout service), not new regressions. No new criticals or highs introduced.
