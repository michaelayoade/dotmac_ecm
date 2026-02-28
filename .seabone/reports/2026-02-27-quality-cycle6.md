# Quality Scan Report — Cycle 6
**Date:** 2026-02-27
**Scan type:** Deep quality scan
**Files reviewed:** ~40 app/ and tests/ files

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 0     |
| High     | 2     |
| Medium   | 6     |
| Low      | 2     |
| **Total**| **10**|

**Codebase health score: 62/100**
**Trend: degrading** (down from 68/100 in quality-cycle2)

---

## New Findings vs Previous Cycles

### New in Cycle 6 (10 findings)

| ID | Severity | File | Issue |
|----|----------|------|-------|
| quality-c6-1 | HIGH | `app/api/ecm_checkouts.py:58` | Checkin auth bypass — any user can check in any document |
| quality-c6-2 | HIGH | `app/services/common.py:11` | `coerce_uuid()` raises ValueError → 500 on bad UUID path params |
| quality-c6-3 | MEDIUM | `app/services/ecm_collaboration.py:164` | No duplicate check in DocumentSubscriptions.create() → unhandled 500 |
| quality-c6-4 | MEDIUM | `app/tasks/webhooks.py:29` | No db.rollback() on exception in `_find_and_queue()` |
| quality-c6-5 | MEDIUM | `app/services/notification.py:76` | `mark_all_read()` loads all rows into memory then iterates |
| quality-c6-6 | MEDIUM | `app/services/ecm_folder.py:127` | `_recompute_subtree_paths()` unbounded `.all()` (Folders + Categories) |
| quality-c6-7 | MEDIUM | `app/services/ecm_folder.py:104` | Soft-delete doesn't cascade to descendant folders/categories |
| quality-c6-8 | MEDIUM | `app/services/ecm_metadata.py:334` | `Categories._compute_path()` silent fallback masking data corruption |
| quality-c6-9 | LOW | `app/services/webhook.py:45` | Legacy `db.query()` API used in non-ECM services |
| quality-c6-10 | LOW | `app/api/ecm_checkouts.py:58` | Stale TODO comment open since initial implementation |

### Still-Open from Cycle 2 (not yet fixed)

The following cycle-2 findings remain unresolved based on direct code inspection:

- **quality-c2-2** (critical): Test accepts HTTP 500 as valid — `tests/test_api_scheduler.py:185,193`
- **quality-c2-3** (high): N+1 in `Notifications.mark_read()` — `app/services/notification.py:61`
- **quality-c2-5** (high): `assert status_code in [401, 404]` in 7 test assertions — `tests/test_api_auth_flow.py`
- **quality-c2-6** (high): `reindex_all_documents` unbounded `.all()` — `app/tasks/search.py:37`
- **quality-c2-7** (medium): `_apply_ordering`/`_apply_pagination` duplicated across 6 service files
- **quality-c2-9** (medium): Test state leakage — `tests/conftest.py:131`
- **quality-c2-12** (medium): `count=len(items)` in search, versions, checkouts endpoints
- **quality-c2-19** (medium): `db.commit()` inside retention per-record loop — `app/tasks/retention.py:37`
- **quality-c2-21** (medium): `_find_and_queue()` unbounded `.all()` — `app/tasks/webhooks.py:47`
- **quality-c2-22** (low): `get_db()` defined in 18 router files (partially addressed but still present)
- **quality-c2-23** (low): Redundant `db.flush()` in checkout service — `app/services/ecm_checkout.py:44`

### Confirmed Fixed Since Cycle 2

- **quality-c2-15 area** (ILIKE wildcard): `app/services/search.py:30` — ILIKE wildcards are now escaped (lines 33-34)

---

## Top 3 Priority Fixes

### 1. `quality-c6-1` — Checkin Authorization Bypass (HIGH)
**File:** `app/api/ecm_checkouts.py:58-62`

The `checkin_document` endpoint extracts `co.checked_out_by` from the existing checkout record and passes it directly to the service's ownership check. This means the service's `str(checkout.checked_out_by) != str(person_uuid)` guard is always satisfied — any authenticated user can check in documents they did not check out. The code even acknowledges this with a TODO comment ("person_id should come from auth context").

**Fix:** Use `request.state.actor_id` (already set by `require_user_auth`) as the `person_id`, so the service's ownership check is actually enforced.

### 2. `quality-c6-2` — Invalid UUID Path Parameters Return 500 (HIGH)
**File:** `app/services/common.py:11`

`coerce_uuid()` propagates a raw `ValueError` on any malformed UUID string. Because this function is called from every service method that accepts an ID path parameter, requests like `GET /ecm/documents/not-a-uuid` return `{"code": "internal_error", "message": "Internal server error"}` instead of a 400/422. This is confusing to API consumers and could be used to probe the API.

**Fix:** Wrap `uuid.UUID()` in try/except and raise `HTTPException(400, detail="Invalid UUID format")`.

### 3. `quality-c6-7` — Soft-Delete Doesn't Cascade to Folder/Category Children (MEDIUM)
**File:** `app/services/ecm_folder.py:104`, `app/services/ecm_metadata.py:322`

Deleting a folder marks only that folder as `is_active=False`, leaving all child folders and grandchildren active with an inactive ancestor. Any code that traverses the hierarchy using `is_active=True` will behave inconsistently. The `_recompute_subtree_paths()` logic already knows how to find descendants — the same SQL predicate can be reused in delete.

---

## Codebase Health Score

**62/100** (down from 68/100 in quality-cycle2)

### Scoring rationale
- **Open cycle-2 findings (11):** −22 points (each deferred finding represents unresolved technical debt)
- **New cycle-6 findings (10):** −16 points
- **Base score 100** minus deductions = 62

### Trend: Degrading
- Cycle 2: 68/100 (23 findings)
- Cycle 6: 62/100 (10 new + 11 still-open from cycle 2)
- Root cause: Fix cycle has been addressing security issues but quality debt is accumulating without dedicated quality-fix cycles
- ILIKE escaping was the only quality fix confirmed since cycle 2

---

## Patterns to Watch

1. **Authorization gap in action endpoints**: The checkin bypass (c6-1) follows the same pattern as the BOLA finding in persons (security-c5-1) — action endpoints that operate on behalf of a user but derive the user identity from request body/record instead of auth context.

2. **Unbounded `.all()` spread**: The `.all()` pattern now confirmed in retention tasks, search reindex task, webhook endpoints, mark_all_read, and _recompute_subtree_paths — 6+ locations. Every new background task and list operation should default to paginated/batched reads.

3. **Silent fallback pattern**: Both `Folders._compute_path()` and `Categories._compute_path()` silently fall back to a root path when a declared parent is missing, masking data corruption. This should be a logged warning or a hard failure.
