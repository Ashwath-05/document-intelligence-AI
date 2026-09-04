"""Application entrypoint.

Composition root: the one place that knows about every layer and wires them
together. Keeping assembly here means no module has to reach out and
construct its own dependencies.

Run with:  uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, conversations, documents, generation, health, search
from app.core.config import get_settings


def create_app() -> FastAPI:
    """Build and configure the FastAPI application.

    A factory rather than a module-level `app = FastAPI()` because tests can
    then build a fresh, independently-configured instance instead of importing
    whatever global the import system happened to initialise first.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        description=(
            "Upload documents, generate summaries, and ask questions about "
            "their contents."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # The React frontend runs on a different origin than the API, so the
    # browser blocks requests by default without this. localhost entries
    # cover local dev; the netlify.app entry is the real deployed frontend
    # -- add any future frontend domain (a custom domain, a second Netlify
    # preview URL, etc.) here too, or requests from it will be silently
    # blocked with no server-side error to point at.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "https://documentintel.netlify.app",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers are registered here, not self-registered on import, so the set of
    # live endpoints is readable in one place.
    app.include_router(health.router, prefix=settings.api_v1_prefix)
    app.include_router(documents.router, prefix=settings.api_v1_prefix)
    app.include_router(search.router, prefix=settings.api_v1_prefix)
    app.include_router(generation.router, prefix=settings.api_v1_prefix)
    app.include_router(chat.router, prefix=settings.api_v1_prefix)
    app.include_router(conversations.router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
