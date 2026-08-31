"""Data access for the documents table.

Repository pattern: this is the ONLY place in the codebase that writes
SQLAlchemy queries for Document. Routes and services call these methods and
never touch a Session or write SQL themselves -- same layering rule from
Phase 1, now with a real implementation behind it.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus


class DocumentRepository:
    """CRUD operations for Document, scoped to one request's session."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, filename: str, storage_path: str) -> Document:
        """Insert a new document row with status defaulting to 'uploaded'.

        No status parameter here on purpose: the Document model's `status`
        column already has default="uploaded" (see app/models/document.py).
        Accepting a status argument here would let a caller create a
        document that's already "ready" with no extracted text -- exactly
        the kind of invalid state mark_ready/mark_failed exist to prevent.
        Creation only ever starts one place in the lifecycle.
        """
        document = Document(filename=filename, storage_path=storage_path)
        self.db.add(document)
        self.db.commit()
        # refresh() re-reads the row from Postgres after commit. Needed
        # because several fields aren't set by our Python code at all --
        # `id` (server default via uuid.uuid4, but only bound at flush),
        # `created_at`/`updated_at` (DB-computed timestamps). Without
        # refresh(), this Document object would have stale/unset values
        # for anything the database itself filled in.
        self.db.refresh(document)
        return document

    def get_by_id(self, document_id: UUID) -> Document | None:
        """Fetch one document by id, or None if it doesn't exist.

        Returning None (not raising) on a miss is deliberate -- "does this
        document exist" is a normal, expected outcome for a route to check,
        not an exceptional one. The caller decides whether a miss is a 404
        or something else; the repository shouldn't make that call.
        """
        return self.db.query(Document).filter(Document.id == document_id).first()

    def mark_ready(self, document_id: UUID, extracted_text: str) -> Document:
        """Transition a document to 'ready' with its extracted text.

        Raises ValueError on a missing id rather than returning None --
        unlike get_by_id, callers of mark_ready already have a specific id
        they expect to exist (it came from their own earlier create() call
        or a route parameter that was already validated). A None here would
        almost always be a bug, not a normal case, so failing loudly is more
        useful than a silent no-op.
        """
        document = self.get_by_id(document_id)
        if document is None:
            raise ValueError(f"No document found with id={document_id}")

        document.extracted_text = extracted_text
        document.status = DocumentStatus.READY.value
        document.error_message = None  # clear any stale failure from a retry
        self.db.commit()
        self.db.refresh(document)
        return document

    def mark_failed(self, document_id: UUID, error_message: str) -> Document:
        """Transition a document to 'failed' and record why."""
        document = self.get_by_id(document_id)
        if document is None:
            raise ValueError(f"No document found with id={document_id}")

        document.status = DocumentStatus.FAILED.value
        document.error_message = error_message
        self.db.commit()
        self.db.refresh(document)
        return document