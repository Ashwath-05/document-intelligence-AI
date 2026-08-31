"""Data access for the conversations table.

Same repository-pattern rule as every other repository in this codebase:
this is the only place that writes SQLAlchemy queries for Conversation.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.conversation import Conversation


class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, document_id: UUID | None = None) -> Conversation:
        conversation = Conversation(document_id=document_id)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        """Fetch one conversation by id, or None if it doesn't exist.

        Same None-not-raise reasoning as DocumentRepository.get_by_id --
        "does this conversation exist" is a normal thing for a caller to
        check, not exceptional.
        """
        return (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )

    def list_all(
        self,
        document_id: UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversation]:
        """Most recently active first. "Active" means touch() has actually
        been called (see below) -- ordering here is only as meaningful as
        callers keep updated_at genuinely current.
        """
        query = self.db.query(Conversation)
        if document_id is not None:
            query = query.filter(Conversation.document_id == document_id)
        return (
            query.order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def touch(self, conversation_id: UUID) -> None:
        """Bump updated_at to now.

        Nothing else in this class issues an UPDATE against an EXISTING
        conversation row -- create() sets updated_at once, and without an
        explicit touch() it would sit frozen there forever, no matter how
        many messages get added to the conversation afterward. Set
        directly rather than relying on the model's onupdate= to fire on
        its own: onupdate only triggers when SOME column changes as part
        of a flush, and nothing else here ever modifies this row.
        """
        conversation = self.get_by_id(conversation_id)
        if conversation is None:
            return
        conversation.updated_at = datetime.now(timezone.utc)
        self.db.commit()

