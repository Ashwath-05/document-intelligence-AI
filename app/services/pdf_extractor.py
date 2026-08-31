"""PDF text extraction.

Isolated in its own module rather than inline in document_service -- this is
the piece most likely to need swapping or extending later (OCR for scanned
PDFs, DOCX/TXT/CSV support in later phases). Keeping it behind one function
means adding a new format is a new function here, not a rewrite of the
service that calls it.
"""

from pypdf import PdfReader


class PDFExtractionError(Exception):
    """Raised when a PDF can't be read, or contains no extractable text."""


def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from a PDF's text layer.

    Only reads text that exists as actual text in the PDF (typed/exported
    documents). A scanned/image-based PDF has no text layer at all -- this
    will correctly raise PDFExtractionError for those, since OCR is out of
    scope for v1.
    """
    try:
        reader = PdfReader(file_path)
    except Exception as e:
        raise PDFExtractionError(f"Could not read PDF: {e}") from e

    pages_text = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(pages_text).strip()

    if not text:
        raise PDFExtractionError(
            "No extractable text found -- this may be a scanned/image-based "
            "PDF (OCR not yet supported in v1)."
        )

    return text
