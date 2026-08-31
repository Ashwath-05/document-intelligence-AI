"""Response contracts for the documents API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    """What the API returns for a document -- never the raw ORM object.

    model_config with from_attributes=True lets this be built directly from
    a SQLAlchemy Document instance (response = DocumentResponse.model_validate(doc))
    instead of manually copying each field across.
    """

    model_config = {"from_attributes": True}

    id: UUID
    filename: str
    status: str
    extracted_text: str | None
    summary: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
