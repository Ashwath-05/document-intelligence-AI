"""Document upload business logic.

Owns "what happens when a document is uploaded" -- validation, saving the
file, recording it in the database. Knows nothing about HTTP (no FastAPI
imports) and nothing about SQL directly (talks only to the repository).
"""

import uuid
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

from app.core.config import Settings
from app.models.document import Document
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.providers.embedding.base import EmbeddingProvider
from app.services.chunking import chunk_text
from app.services.pdf_extractor import PDFExtractionError, extract_text_from_pdf


class InvalidFileError(Exception):
    """Raised when an uploaded file fails validation (type or size)."""


class DocumentNotFoundError(Exception):
    """Raised when a requested document id doesn't exist."""


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
        chunk_repository: ChunkRepository,
        embedding_provider: EmbeddingProvider,
        settings: Settings,
    ):
        self.repository = repository
        self.chunk_repository = chunk_repository
        self.embedding_provider = embedding_provider
        self.settings = settings

    def upload_document(self, file: UploadFile) -> Document:
        """Validate, save to disk, and record a new uploaded document.

        file.file is the underlying SpooledTemporaryFile -- read/seek work
        synchronously on it, which is why this whole call chain can stay
        `def` rather than `async def` (same blocking-work rule from
        Phase 1/2: plain def gets threadpool-offloaded by FastAPI
        automatically).
        """
        self._validate_extension(file.filename)
        contents = file.file.read()
        self._validate_size(len(contents))

        upload_dir = Path(self.settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Prefix with a UUID so two uploads named "invoice.pdf" never collide
        # on disk -- the DB row keeps the original filename separately for
        # display, storage_path is purely an internal lookup key.
        stored_name = f"{uuid.uuid4()}_{file.filename}"
        storage_path = str(upload_dir / stored_name)

        with open(storage_path, "wb") as f:
            f.write(contents)

        document = self.repository.create(
            filename=file.filename, storage_path=storage_path
        )

        # Extraction runs synchronously, right in the upload request -- v1
        # has no background job queue (explicitly out of scope), so this is
        # the whole pipeline: save file, create row, extract, update status.
        # Trade-off: a large PDF makes the upload response slower. That's
        # the exact problem background task processing (a later phase)
        # exists to solve -- we're feeling the limitation before fixing it,
        # which is the right order to learn it in.
        try:
            extracted_text = extract_text_from_pdf(storage_path)
            chunks = chunk_text(
                extracted_text,
                chunk_size=self.settings.chunk_size_tokens,
                overlap=self.settings.chunk_overlap_tokens,
            )
            # One batched call for every chunk this document produced --
            # not one embed() call per chunk. See EmbeddingProvider.embed's
            # docstring for why batching matters here.
            vectors = self.embedding_provider.embed([c["text"] for c in chunks])
            for chunk, vector in zip(chunks, vectors):
                chunk["embedding"] = vector
            self.chunk_repository.create_many(document.id, chunks)
            document = self.repository.mark_ready(document.id, extracted_text)
        except PDFExtractionError as e:
            document = self.repository.mark_failed(document.id, str(e))

        return document

    def get_document(self, document_id: UUID) -> Document:
        document = self.repository.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError(f"No document with id={document_id}")
        return document

    def _validate_extension(self, filename: str | None) -> None:
        if not filename:
            raise InvalidFileError("Uploaded file has no filename")
        ext = Path(filename).suffix.lower()
        if ext not in self.settings.allowed_extensions:
            raise InvalidFileError(
                f"'{ext}' not supported -- allowed: {self.settings.allowed_extensions}"
            )

    def _validate_size(self, size_bytes: int) -> None:
        max_bytes = self.settings.max_upload_size_mb * 1024 * 1024
        if size_bytes > max_bytes:
            raise InvalidFileError(
                f"File exceeds {self.settings.max_upload_size_mb}MB limit"
            )
        if size_bytes == 0:
            raise InvalidFileError("Uploaded file is empty")
