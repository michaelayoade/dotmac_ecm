import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.models.ecm import (
    DispositionAction,
    DispositionStatus,
    Document,
    DocumentRetention,
    RetentionPolicy,
)


class TestCheckRetentionExpiry:
    def _make_retention(
        self, db_session, person, folder, *, expires_delta_days, status, is_active=True
    ):
        doc = Document(
            title=f"ret_test_{uuid.uuid4().hex[:8]}",
            file_name="ret.pdf",
            file_size=100,
            mime_type="application/pdf",
            created_by=person.id,
            folder_id=folder.id,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        policy = RetentionPolicy(
            name=f"policy_{uuid.uuid4().hex[:8]}",
            retention_days=1,
            disposition_action=DispositionAction.destroy,
        )
        db_session.add(policy)
        db_session.commit()
        db_session.refresh(policy)

        retention = DocumentRetention(
            document_id=doc.id,
            policy_id=policy.id,
            retention_expires_at=datetime.now(timezone.utc)
            + timedelta(days=expires_delta_days),
            disposition_status=status,
            is_active=is_active,
        )
        db_session.add(retention)
        db_session.commit()
        db_session.refresh(retention)
        return retention

    def test_marks_expired_as_eligible(self, db_session, person, folder) -> None:
        retention = self._make_retention(
            db_session,
            person,
            folder,
            expires_delta_days=-1,
            status=DispositionStatus.pending,
        )

        with patch("app.db.SessionLocal", return_value=db_session):
            with patch.object(db_session, "close"):
                with patch("app.services.event.publish_event"):
                    from app.tasks.retention import check_retention_expiry

                    check_retention_expiry()

        db_session.refresh(retention)
        assert retention.disposition_status == DispositionStatus.eligible

    def test_skips_non_expired(self, db_session, person, folder) -> None:
        retention = self._make_retention(
            db_session,
            person,
            folder,
            expires_delta_days=365,
            status=DispositionStatus.pending,
        )

        with patch("app.db.SessionLocal", return_value=db_session):
            with patch.object(db_session, "close"):
                with patch("app.services.event.publish_event"):
                    from app.tasks.retention import check_retention_expiry

                    check_retention_expiry()

        db_session.refresh(retention)
        assert retention.disposition_status == DispositionStatus.pending

    def test_skips_already_eligible(self, db_session, person, folder) -> None:
        retention = self._make_retention(
            db_session,
            person,
            folder,
            expires_delta_days=-1,
            status=DispositionStatus.eligible,
        )

        with patch("app.db.SessionLocal", return_value=db_session):
            with patch.object(db_session, "close"):
                with patch("app.services.event.publish_event"):
                    from app.tasks.retention import check_retention_expiry

                    check_retention_expiry()

        db_session.refresh(retention)
        assert retention.disposition_status == DispositionStatus.eligible

    def test_skips_inactive_retentions(self, db_session, person, folder) -> None:
        retention = self._make_retention(
            db_session,
            person,
            folder,
            expires_delta_days=-1,
            status=DispositionStatus.pending,
            is_active=False,
        )

        with patch("app.db.SessionLocal", return_value=db_session):
            with patch.object(db_session, "close"):
                with patch("app.services.event.publish_event"):
                    from app.tasks.retention import check_retention_expiry

                    check_retention_expiry()

        db_session.refresh(retention)
        assert retention.disposition_status == DispositionStatus.pending

    def test_publishes_retention_expired_event(
        self, db_session, person, folder
    ) -> None:
        self._make_retention(
            db_session,
            person,
            folder,
            expires_delta_days=-1,
            status=DispositionStatus.pending,
        )

        with patch("app.db.SessionLocal", return_value=db_session):
            with patch.object(db_session, "close"):
                with patch("app.services.event.publish_event") as mock_publish:
                    from app.tasks.retention import check_retention_expiry

                    check_retention_expiry()

        assert mock_publish.called
        from app.services.event import EventType

        call_args = mock_publish.call_args
        assert call_args[0][0] == EventType.retention_expired

    def test_handles_empty_results(self, db_session) -> None:
        with patch("app.db.SessionLocal", return_value=db_session):
            with patch.object(db_session, "close"):
                with patch("app.services.event.publish_event"):
                    from app.tasks.retention import check_retention_expiry

                    # Should not raise when no expired retentions exist
                    check_retention_expiry()
