"""Data access for the messages table."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.message import Message, MessageRole


class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, conversation_id: UUID, role: MessageRole, content: str) -> Message:
        message = Message(
            conversation_id=conversation_id, role=role.value, content=content
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def list_by_conversation(self, conversation_id: UUID) -> list[Message]:
        """All messages in a conversation, oldest first -- the order a
        transcript or a chat prompt actually needs them in.
        """
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .all()
        )
