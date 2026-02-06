import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.ecm import (
    Comment,
    CommentStatus,
    Document,
    DocumentSubscription,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowInstanceStatus,
    WorkflowTask,
    WorkflowTaskStatus,
    WorkflowTaskType,
)
from app.models.person import Person


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unique_email() -> str:
    return f"ecm-p3-{uuid.uuid4().hex}@example.com"


def _make_person(db_session: object) -> Person:
    p = Person(first_name="WF", last_name="Tester", email=_unique_email())
    db_session.add(p)
    db_session.flush()
    return p


def _make_document(db_session: object, person: Person) -> Document:
    doc = Document(
        title=f"Doc-{uuid.uuid4().hex[:8]}",
        file_name="test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        created_by=person.id,
    )
    db_session.add(doc)
    db_session.flush()
    return doc


SAMPLE_STATES = {
    "draft": {"transitions": [{"to": "review", "roles": ["author", "editor"]}]},
    "review": {
        "transitions": [
            {"to": "approved", "roles": ["reviewer"]},
            {"to": "draft", "roles": ["reviewer"]},
        ]
    },
    "approved": {"transitions": [{"to": "published", "roles": ["publisher"]}]},
    "published": {"final": True},
}


def _make_workflow_definition(db_session: object) -> WorkflowDefinition:
    wd = WorkflowDefinition(
        name=f"wf-{uuid.uuid4().hex[:8]}",
        description="Test workflow",
        states=SAMPLE_STATES,
    )
    db_session.add(wd)
    db_session.flush()
    return wd


def _make_workflow_instance(
    db_session: object,
    definition: WorkflowDefinition,
    document: Document,
    person: Person,
) -> WorkflowInstance:
    wi = WorkflowInstance(
        definition_id=definition.id,
        document_id=document.id,
        current_state="draft",
        started_by=person.id,
    )
    db_session.add(wi)
    db_session.flush()
    return wi


# ---------------------------------------------------------------------------
# Enum Tests
# ---------------------------------------------------------------------------


class TestPhase3Enums:
    def test_workflow_task_status_values(self) -> None:
        assert WorkflowTaskStatus.pending.value == "pending"
        assert WorkflowTaskStatus.approved.value == "approved"
        assert WorkflowTaskStatus.rejected.value == "rejected"
        assert WorkflowTaskStatus.cancelled.value == "cancelled"
        assert len(WorkflowTaskStatus) == 4

    def test_workflow_task_type_values(self) -> None:
        assert WorkflowTaskType.approval.value == "approval"
        assert WorkflowTaskType.review.value == "review"
        assert WorkflowTaskType.sign_off.value == "sign_off"
        assert len(WorkflowTaskType) == 3

    def test_workflow_instance_status_values(self) -> None:
        assert WorkflowInstanceStatus.active.value == "active"
        assert WorkflowInstanceStatus.completed.value == "completed"
        assert WorkflowInstanceStatus.cancelled.value == "cancelled"
        assert len(WorkflowInstanceStatus) == 3

    def test_comment_status_values(self) -> None:
        assert CommentStatus.active.value == "active"
        assert CommentStatus.deleted.value == "deleted"
        assert len(CommentStatus) == 2


# ---------------------------------------------------------------------------
# WorkflowDefinition Tests
# ---------------------------------------------------------------------------


class TestWorkflowDefinition:
    def test_create_workflow_definition(self, db_session: object) -> None:
        wd = _make_workflow_definition(db_session)
        db_session.refresh(wd)

        assert wd.id is not None
        assert wd.name.startswith("wf-")
        assert wd.states == SAMPLE_STATES
        assert wd.is_active is True
        assert wd.created_at is not None
        assert wd.updated_at is not None

    def test_unique_name_constraint(self, db_session: object) -> None:
        name = f"wf-unique-{uuid.uuid4().hex[:8]}"
        wd1 = WorkflowDefinition(name=name, states=SAMPLE_STATES)
        db_session.add(wd1)
        db_session.flush()

        wd2 = WorkflowDefinition(name=name, states=SAMPLE_STATES)
        db_session.add(wd2)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_description_nullable(self, db_session: object) -> None:
        wd = WorkflowDefinition(
            name=f"wf-{uuid.uuid4().hex[:8]}",
            states={"draft": {"final": True}},
        )
        db_session.add(wd)
        db_session.flush()
        db_session.refresh(wd)

        assert wd.description is None

    def test_instances_relationship(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        wd = _make_workflow_definition(db_session)

        wi = WorkflowInstance(
            definition_id=wd.id,
            document_id=doc.id,
            current_state="draft",
            started_by=person.id,
        )
        db_session.add(wi)
        db_session.flush()
        db_session.refresh(wd)

        assert len(wd.instances) == 1
        assert wd.instances[0].current_state == "draft"


# ---------------------------------------------------------------------------
# WorkflowInstance Tests
# ---------------------------------------------------------------------------


class TestWorkflowInstance:
    def test_create_workflow_instance(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        wd = _make_workflow_definition(db_session)

        wi = _make_workflow_instance(db_session, wd, doc, person)
        db_session.refresh(wi)

        assert wi.id is not None
        assert wi.definition_id == wd.id
        assert wi.document_id == doc.id
        assert wi.current_state == "draft"
        assert wi.status == WorkflowInstanceStatus.active
        assert wi.started_by == person.id
        assert wi.is_active is True
        assert wi.created_at is not None

    def test_default_status_is_active(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        wd = _make_workflow_definition(db_session)

        wi = _make_workflow_instance(db_session, wd, doc, person)
        db_session.refresh(wi)

        assert wi.status == WorkflowInstanceStatus.active

    def test_metadata_field(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        wd = _make_workflow_definition(db_session)

        wi = WorkflowInstance(
            definition_id=wd.id,
            document_id=doc.id,
            current_state="review",
            started_by=person.id,
            metadata_={"priority": "high", "department": "legal"},
        )
        db_session.add(wi)
        db_session.flush()
        db_session.refresh(wi)

        assert wi.metadata_["priority"] == "high"

    def test_relationships(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        wd = _make_workflow_definition(db_session)

        wi = _make_workflow_instance(db_session, wd, doc, person)
        db_session.refresh(wi)

        assert wi.definition.id == wd.id
        assert wi.document.id == doc.id
        assert wi.starter.id == person.id

    def test_tasks_relationship(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        wd = _make_workflow_definition(db_session)
        wi = _make_workflow_instance(db_session, wd, doc, person)

        task = WorkflowTask(
            instance_id=wi.id,
            task_type=WorkflowTaskType.approval,
            assignee_id=person.id,
            from_state="draft",
            to_state="review",
        )
        db_session.add(task)
        db_session.flush()
        db_session.refresh(wi)

        assert len(wi.tasks) == 1
        assert wi.tasks[0].task_type == WorkflowTaskType.approval


# ---------------------------------------------------------------------------
# WorkflowTask Tests
# ---------------------------------------------------------------------------


class TestWorkflowTask:
    def test_create_task(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        wd = _make_workflow_definition(db_session)
        wi = _make_workflow_instance(db_session, wd, doc, person)

        assignee = _make_person(db_session)
        task = WorkflowTask(
            instance_id=wi.id,
            task_type=WorkflowTaskType.review,
            assignee_id=assignee.id,
            from_state="draft",
            to_state="review",
        )
        db_session.add(task)
        db_session.flush()
        db_session.refresh(task)

        assert task.id is not None
        assert task.task_type == WorkflowTaskType.review
        assert task.status == WorkflowTaskStatus.pending
        assert task.assignee_id == assignee.id
        assert task.from_state == "draft"
        assert task.to_state == "review"
        assert task.decision_comment is None
        assert task.decided_at is None
        assert task.due_at is None
        assert task.is_active is True

    def test_task_with_decision(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        wd = _make_workflow_definition(db_session)
        wi = _make_workflow_instance(db_session, wd, doc, person)

        now = datetime.now(timezone.utc)
        task = WorkflowTask(
            instance_id=wi.id,
            task_type=WorkflowTaskType.approval,
            status=WorkflowTaskStatus.approved,
            assignee_id=person.id,
            from_state="review",
            to_state="approved",
            decision_comment="Looks good, approved.",
            decided_at=now,
        )
        db_session.add(task)
        db_session.flush()
        db_session.refresh(task)

        assert task.status == WorkflowTaskStatus.approved
        assert task.decision_comment == "Looks good, approved."
        assert task.decided_at is not None

    def test_task_with_due_date(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        wd = _make_workflow_definition(db_session)
        wi = _make_workflow_instance(db_session, wd, doc, person)

        due = datetime.now(timezone.utc)
        task = WorkflowTask(
            instance_id=wi.id,
            task_type=WorkflowTaskType.sign_off,
            assignee_id=person.id,
            from_state="approved",
            to_state="published",
            due_at=due,
        )
        db_session.add(task)
        db_session.flush()
        db_session.refresh(task)

        assert task.due_at is not None
        assert task.task_type == WorkflowTaskType.sign_off

    def test_all_task_statuses(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        wd = _make_workflow_definition(db_session)
        wi = _make_workflow_instance(db_session, wd, doc, person)

        for status in WorkflowTaskStatus:
            task = WorkflowTask(
                instance_id=wi.id,
                task_type=WorkflowTaskType.approval,
                status=status,
                assignee_id=person.id,
                from_state="draft",
                to_state="review",
            )
            db_session.add(task)
        db_session.flush()

        tasks = (
            db_session.execute(
                select(WorkflowTask).where(WorkflowTask.instance_id == wi.id)
            )
            .scalars()
            .all()
        )
        assert len(tasks) == 4

    def test_instance_relationship(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        wd = _make_workflow_definition(db_session)
        wi = _make_workflow_instance(db_session, wd, doc, person)

        task = WorkflowTask(
            instance_id=wi.id,
            task_type=WorkflowTaskType.review,
            assignee_id=person.id,
            from_state="draft",
            to_state="review",
        )
        db_session.add(task)
        db_session.flush()
        db_session.refresh(task)

        assert task.instance.id == wi.id
        assert task.assignee.id == person.id


# ---------------------------------------------------------------------------
# Comment Tests
# ---------------------------------------------------------------------------


class TestComment:
    def test_create_comment(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)

        comment = Comment(
            document_id=doc.id,
            body="This looks great!",
            author_id=person.id,
        )
        db_session.add(comment)
        db_session.flush()
        db_session.refresh(comment)

        assert comment.id is not None
        assert comment.document_id == doc.id
        assert comment.body == "This looks great!"
        assert comment.author_id == person.id
        assert comment.status == CommentStatus.active
        assert comment.is_active is True
        assert comment.parent_id is None
        assert comment.created_at is not None

    def test_threaded_reply(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)

        parent = Comment(
            document_id=doc.id,
            body="Original comment",
            author_id=person.id,
        )
        db_session.add(parent)
        db_session.flush()

        reply = Comment(
            document_id=doc.id,
            parent_id=parent.id,
            body="Reply to original",
            author_id=person.id,
        )
        db_session.add(reply)
        db_session.flush()
        db_session.refresh(parent)

        assert len(parent.replies) == 1
        assert parent.replies[0].body == "Reply to original"

    def test_reply_parent_relationship(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)

        parent = Comment(
            document_id=doc.id,
            body="Parent comment",
            author_id=person.id,
        )
        db_session.add(parent)
        db_session.flush()

        reply = Comment(
            document_id=doc.id,
            parent_id=parent.id,
            body="Child comment",
            author_id=person.id,
        )
        db_session.add(reply)
        db_session.flush()
        db_session.refresh(reply)

        assert reply.parent.id == parent.id

    def test_comment_status_deleted(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)

        comment = Comment(
            document_id=doc.id,
            body="Will be soft-deleted",
            author_id=person.id,
            status=CommentStatus.deleted,
        )
        db_session.add(comment)
        db_session.flush()
        db_session.refresh(comment)

        assert comment.status == CommentStatus.deleted

    def test_document_comments_relationship(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)

        for i in range(3):
            c = Comment(
                document_id=doc.id,
                body=f"Comment {i}",
                author_id=person.id,
            )
            db_session.add(c)
        db_session.flush()
        db_session.refresh(doc)

        assert len(doc.comments) == 3

    def test_author_relationship(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)

        comment = Comment(
            document_id=doc.id,
            body="Test author rel",
            author_id=person.id,
        )
        db_session.add(comment)
        db_session.flush()
        db_session.refresh(comment)

        assert comment.author.id == person.id


# ---------------------------------------------------------------------------
# DocumentSubscription Tests
# ---------------------------------------------------------------------------


class TestDocumentSubscription:
    def test_create_subscription(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)

        sub = DocumentSubscription(
            document_id=doc.id,
            person_id=person.id,
            event_types=["version_created", "comment_added"],
        )
        db_session.add(sub)
        db_session.flush()
        db_session.refresh(sub)

        assert sub.id is not None
        assert sub.document_id == doc.id
        assert sub.person_id == person.id
        assert sub.event_types == ["version_created", "comment_added"]
        assert sub.is_active is True
        assert sub.created_at is not None

    def test_unique_constraint_doc_person(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)

        sub1 = DocumentSubscription(
            document_id=doc.id,
            person_id=person.id,
            event_types=["version_created"],
        )
        db_session.add(sub1)
        db_session.flush()

        sub2 = DocumentSubscription(
            document_id=doc.id,
            person_id=person.id,
            event_types=["comment_added"],
        )
        db_session.add(sub2)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_different_people_same_document(self, db_session: object) -> None:
        person1 = _make_person(db_session)
        person2 = _make_person(db_session)
        doc = _make_document(db_session, person1)

        sub1 = DocumentSubscription(
            document_id=doc.id,
            person_id=person1.id,
            event_types=["version_created"],
        )
        sub2 = DocumentSubscription(
            document_id=doc.id,
            person_id=person2.id,
            event_types=["comment_added"],
        )
        db_session.add_all([sub1, sub2])
        db_session.flush()

        subs = (
            db_session.execute(
                select(DocumentSubscription).where(
                    DocumentSubscription.document_id == doc.id
                )
            )
            .scalars()
            .all()
        )
        assert len(subs) == 2

    def test_all_event_types(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)

        all_events = [
            "version_created",
            "comment_added",
            "status_changed",
            "checkout",
            "checkin",
        ]
        sub = DocumentSubscription(
            document_id=doc.id,
            person_id=person.id,
            event_types=all_events,
        )
        db_session.add(sub)
        db_session.flush()
        db_session.refresh(sub)

        assert sub.event_types == all_events
        assert len(sub.event_types) == 5

    def test_document_subscriptions_relationship(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)

        sub = DocumentSubscription(
            document_id=doc.id,
            person_id=person.id,
            event_types=["version_created"],
        )
        db_session.add(sub)
        db_session.flush()
        db_session.refresh(doc)

        assert len(doc.subscriptions) == 1
        assert doc.subscriptions[0].person_id == person.id

    def test_person_relationship(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)

        sub = DocumentSubscription(
            document_id=doc.id,
            person_id=person.id,
            event_types=["status_changed"],
        )
        db_session.add(sub)
        db_session.flush()
        db_session.refresh(sub)

        assert sub.person.id == person.id
        assert sub.document.id == doc.id
