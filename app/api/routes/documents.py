"""Document upload and retrieval endpoints.

Both routes are plain `def`, not `async def` -- they touch the sync DB
session and do blocking file I/O. FastAPI runs blocking `def` handlers in a
threadpool automatically; an `async def` here would block the event loop on
every upload. Same rule from Phase 1, now applied for real.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.repositories.chunk_repository import ChunkRepository
from app.providers.embedding.sentence_transformer_provider import (
    SentenceTransformerProvider,
)
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import DocumentResponse
from app.services.document_service import (
    DocumentNotFoundError,
    DocumentService,
    InvalidFileError,
)

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DocumentService:
    """Assemble a DocumentService for this request.

    Same Depends(...) shape as get_settings/get_db -- FastAPI resolves this
    chain automatically: get_db() runs, get_settings() runs, both get
    injected here, and the resulting service gets injected into the route
    below. Nothing above manually wires anything together.
    """
    repository = DocumentRepository(db)
    chunk_repository = ChunkRepository(db)
    embedding_provider = SentenceTransformerProvider()
    return DocumentService(repository, chunk_repository, embedding_provider, settings)


@router.post("", response_model=DocumentResponse, status_code=201)
def upload_document(
    file: UploadFile,
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    try:
        document = service.upload_document(file)
    except InvalidFileError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return DocumentResponse.model_validate(document)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: UUID,
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    try:
        document = service.get_document(document_id)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return DocumentResponse.model_validate(document)
