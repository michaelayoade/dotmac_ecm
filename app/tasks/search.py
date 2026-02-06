import logging

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.search.update_search_index", ignore_result=True)
def update_search_index(
    document_id: str | None = None,
    event_type: str | None = None,
) -> None:
    """Update the search index for a single document."""
    if not document_id:
        return

    from app.db import SessionLocal
    from app.services.search import SearchService

    db = SessionLocal()
    try:
        SearchService.update_document_vector(db, document_id)
    except Exception as e:
        logger.exception("Failed to update search index for %s: %s", document_id, e)
    finally:
        db.close()


@celery_app.task(name="app.tasks.search.reindex_all_documents", ignore_result=True)
def reindex_all_documents() -> None:
    """Periodic task to reindex all active documents."""
    from app.db import SessionLocal
    from app.models.ecm import Document

    db = SessionLocal()
    try:
        docs = db.query(Document).filter(Document.is_active.is_(True)).all()
        from app.services.search import SearchService

        for doc in docs:
            try:
                SearchService.update_document_vector(db, str(doc.id))
            except Exception as e:
                logger.warning("Failed to reindex document %s: %s", doc.id, e)
        logger.info("Reindexed %d documents", len(docs))
    except Exception as e:
        logger.exception("Failed to reindex all documents: %s", e)
    finally:
        db.close()
