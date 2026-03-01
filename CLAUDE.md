# DotMac ECM — Claude Agent Guide

FastAPI + SQLAlchemy 2.0 + PostgreSQL + S3-compatible storage. Electronic Content Management.
Python 3.11+. OpenTelemetry instrumentation. No web UI — API-only.

## Commands
```bash
poetry run ruff check app/ tests/ --fix
poetry run ruff format app/ tests/
poetry run mypy app/ --ignore-missing-imports
poetry run pytest tests/ -x -q --tb=short
```
Always use `poetry run`. No Makefile.

## Non-Negotiable Rules
- SQLAlchemy 2.0: `select()` + `scalars()`, never `db.query()`
- `db.flush()` in services, `db.commit()` in routes/tasks
- Routes are thin wrappers — no business logic
- Manager singleton pattern: static methods on class, singleton exported lowercase
- Services raise `HTTPException(404)` for missing entities (API-only app)

## Key Services
| Service | Purpose |
|---------|---------|
| `ecm_storage.py` — `StorageService` | S3 uploads/downloads. Always check `is_configured()` first. Static methods only. S3 client via `_get_client()`. |
| `ecm_document.py` | Document CRUD, versioning, checkout |
| `ecm_folder.py` | Folder hierarchy, ACL |
| `ecm_acl.py` | Access control lists |
| `ecm_workflow.py` | Approval workflows |
| `ecm_metadata.py` | Custom metadata schemas |
| `ecm_retention.py` | Retention policies |
| `ecm_legal_hold.py` | Legal holds |
| `ecm_checkout.py` | Document checkout/checkin |
| `ecm_collaboration.py` | Comments, annotations |
| `auth_flow.py` | JWT auth + refresh token rotation |
| `domain_settings.py` | Per-domain config |

## StorageService Usage
```python
from app.services.ecm_storage import StorageService

if not StorageService.is_configured():
    raise RuntimeError("S3 not configured")

# Upload
key = StorageService.generate_storage_key(document_id, filename)
StorageService.upload_file(file_data, key, content_type)

# Download
url = StorageService.generate_presigned_url(key, expires=3600)
```
Never use boto3 directly in domain services — always go through `StorageService`.

## S3 Client typing
`_get_client()` returns an untyped boto3 client. Use `Any` for the type, not `object`:
```python
from typing import Any
def _upload(self, client: Any, key: str) -> None: ...
```

## Search — LIKE pattern escaping
The ILIKE pattern must escape both `%` and `_` AND pass `escape='\'`:
```python
escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
stmt = select(Model).where(Model.name.ilike(f"%{escaped}%", escape="\\"))
```
Without the escape clause, `_` acts as a wildcard and `test_basic` returns 0 results.

## Test Setup
- SQLite in-memory for tests
- `conftest.py` has `db_session`, auth fixtures
- External services mocked in `tests/mocks.py`
- `test_search_basic` expects at least 1 result — ensure test data is seeded BEFORE search

## Ruff
Standard rules. Check `pyproject.toml` for any project-specific ignores.
Common issues in tests: unused `result =` assignments (prefix with `_`), post-mock imports (add `# noqa: E402`).

## Common Mistakes
- `object` type for boto3 client (use `Any`)
- ILIKE without `escape` param (returns 0 results for underscore patterns)
- Missing `is_configured()` check before S3 operations
- `db.query()` instead of `select()` + `scalars()`
- Unused `result = ` in tests (ruff E741 — prefix with `_`)
