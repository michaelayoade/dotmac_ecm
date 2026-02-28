# Quality Scan Report — Cycle 9
**Date:** 2026-02-28
**Scanner:** Seabone Sentinel
**Focus:** Dead code, missing error handling, type mismatches, long functions, duplicate logic, broken tests, inconsistent patterns, resource cleanup

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High     | 2 |
| Medium   | 6 |
| Low      | 3 |
| **Total**| **11** |

**Health Score:** 57/100
**Trend:** Degrading (was 62/100 in quality-cycle6; no fixes confirmed since then)

---

## Findings

### HIGH

#### quality-c9-1 — Dead Code: `send_notification_email` never dispatched
**File:** `app/tasks/notifications.py:94`
The `send_notification_email` Celery task is defined and registered with the Celery app but is never called from `_dispatch()`. The placeholder log prints "Would send email to person %s" but the task is never enqueued. Email delivery for subscription events is completely non-functional. Effort: **small**.

#### quality-c9-2 — Missing Assignee Check on Workflow Task Completion
**File:** `app/api/ecm_workflows.py:252`
`POST /ecm/workflow-tasks/{task_id}/complete` has no ownership check — any authenticated user can approve or reject any workflow task. The service `WorkflowTasks.complete()` only checks that the task is in `pending` status; it does not verify the caller is the assigned reviewer. This bypasses the entire approval workflow. Effort: **small**.

---

### MEDIUM

#### quality-c9-3 — Asymmetric Empty-List Semantics in Event Matching
**File:** `app/tasks/notifications.py:85`
`_matches_event()` returns `False` for an empty `subscribed_types` list (subscriber receives nothing), but `_endpoint_matches()` in `tasks/webhooks.py:87` returns `True` for an empty list (webhook endpoint receives everything). Subscribers with no event types configured silently receive zero notifications, which is counterintuitive and inconsistent. Effort: **trivial**.

#### quality-c9-4 — `LegalHoldDocuments.delete()` Hard-Deletes Instead of Soft-Deletes
**File:** `app/services/ecm_legal_hold.py:181`
`LegalHoldDocuments.delete()` calls `db.delete(lhd)` while the parent `LegalHolds.delete()` and all other ECM entities use `is_active = False` soft deletes. Hard-deleting a legal hold document association permanently destroys evidence of what was placed under hold, violating the audit-trail requirement of legal hold management. Effort: **small**.

#### quality-c9-5 — Thundering Herd in `_load_audit_settings` Cache
**File:** `app/main.py:115`
`_load_audit_settings()` uses double-checked locking incorrectly: the lock is released after the cache-hit check, then re-acquired only for the cache write. On a cold or expired cache, N concurrent requests all bypass the first guard in parallel and each issue a redundant DB query. Under high load this creates a thundering herd every 30 seconds. Effort: **trivial**.

#### quality-c9-6 — `response_model=dict` Disables Validation on Checkin Endpoint
**File:** `app/api/ecm_checkouts.py:52`
The POST `/{document_id}/checkin` endpoint uses `response_model=dict` which disables Pydantic response validation, omits the response body schema from OpenAPI docs, and makes the endpoint contract opaque to generated API clients. Effort: **trivial**.

#### quality-c9-7 — Test Client Missing `auth.py` Router DB Override
**File:** `tests/conftest.py:196`
The `client` fixture overrides `get_db` for all routers except `app.api.auth` (the admin management router for `/user-credentials`, `/sessions`, `/mfa-methods`, `/api-keys`). Any test calling these endpoints through the TestClient will silently connect to the production database instead of the in-memory test database. Effort: **trivial**.

#### quality-c9-8 — Service Methods Self-Commit Instead of Using `db.flush()`
**File:** `app/services/notification.py:67`
`Notifications.mark_read()`, `mark_all_read()`, and `dismiss()` call `db.commit()` directly inside service methods. Similarly, `WebhookEndpoints.create/update/delete()` self-commit. This is inconsistent with all ECM service methods that use `db.flush()` and rely on the router's `get_db()` to commit. If the router pattern is ever upgraded to auto-commit, these will double-commit. Effort: **small**.

#### quality-c9-9 — Password Reset Token Race Condition
**File:** `app/services/auth_flow.py:767`
`reset_password()` reads a PasswordResetToken with `used_at IS NULL` and marks it used later in the same transaction, without a row-level lock. Two concurrent requests with the same token can both read `used_at IS NULL` before either commits, allowing a single-use token to be consumed twice and the password reset to happen twice. Effort: **small**.

---

### LOW

#### quality-c9-10 — Redundant `db.flush()` in `Checkouts.checkout()`
**File:** `app/services/ecm_checkout.py:44`
`Checkouts.checkout()` calls `db.flush()` twice in succession — once inside the try block (line 38) and again unconditionally at line 44 after the try/except. The second call is redundant. Effort: **trivial**.

#### quality-c9-11 — Incorrect Type Annotation in Test Helper
**File:** `tests/conftest.py:228`
`_create_access_token` has `roles: list[str] = None` and `scopes: list[str] = None` which are invalid type annotations. `None` is not assignable to `list[str]`. Should be `list[str] | None = None`. Mypy would flag these as type errors. Effort: **trivial**.

---

## Comparison with Previous Scans

### New vs. Previous Cycle (quality-cycle6, 10 findings)
All 10 cycle-6 findings appear unresolved:
- Checkin auth bypass (also has a service-layer check now — PARTIALLY addressed in service layer but API still passes wrong person_id)
- coerce_uuid → 500, subscription dup, webhook rollback (missing rollback), mark_all_read unbounded, subtree .all(), non-cascade delete, silent _compute_path fallback

The cycle-2 findings (23) also remain largely open based on no confirmed fixes.

### What's New in Cycle 9
1. Dead code: `send_notification_email` task (functional impact — emails never sent)
2. Workflow task completion missing ownership check (authorization gap)
3. Asymmetric event-matching empty-list semantics (silent data loss)
4. Legal hold hard-delete inconsistency (audit trail risk)
5. Cache thundering herd in audit settings loader (performance)
6. `response_model=dict` on checkin (type safety)
7. Missing DB override in test client (test reliability)
8. Service self-commit pattern (consistency/future correctness)
9. Password reset token race condition (correctness under concurrency)
10. Double flush (code quality)
11. Wrong type annotation in test helper (type safety)

### What Was Fixed
**No fixes confirmed since quality-cycle6.** Zero findings have been verified as resolved.

---

## Top 3 Priority Fixes

1. **quality-c9-2** — Workflow task completion has no assignee check. Any user can approve any task. Fix by adding `auth['person_id'] == task.assignee_id` check in the complete endpoint.

2. **quality-c9-1** — Email notifications are silently broken. The `send_notification_email` task is registered but never called from `_dispatch()`. Wire it in or remove it.

3. **quality-c9-9** — Password reset token race condition allows double-use under concurrent requests. Add a `SELECT FOR UPDATE` or atomic UPDATE approach.

---

## Codebase Health Score

**57/100** — Degrading

| Factor | Assessment |
|--------|-----------|
| Security posture | 8 open security findings (c8), multiple unresolved c5/c2 |
| Code consistency | get_db split semantics, self-commit services, utility drift |
| Test quality | DB override gap, state leakage, module-scope engine |
| Dead code | send_notification_email, some placeholder tasks |
| Authorization gaps | Workflow task completion, checkin bypass |
| Pattern adherence | response_model=dict, hard delete in legal holds |

The codebase health has declined from 62 (cycle-6) to 57 due to accumulation of unresolved findings across quality, security, and API scan cycles without confirmed fixes.
