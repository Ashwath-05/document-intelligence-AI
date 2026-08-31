# AI Document Intelligence Platform

Upload documents, generate AI summaries, and ask questions about their contents.

**Status: Phase 1 — backend skeleton.** No document logic, no database, no LLM
calls yet. Those arrive in later phases, and the structure below is built so
each addition is additive rather than a rewrite.

---

## Setup

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # .env is gitignored; edit as needed

uvicorn app.main:app --reload
```

Then open:

- http://127.0.0.1:8000/docs — interactive Swagger UI
- http://127.0.0.1:8000/api/v1/health — liveness check

Expected response:

```json
{
  "status": "ok",
  "app_name": "AI Document Intelligence Platform",
  "version": "0.1.0"
}
```

---

## Structure

```
app/
├── main.py              composition root — builds the app, wires routers
├── core/config.py       env-driven settings (Pydantic Settings)
├── api/routes/          HTTP layer: parse request, delegate, shape response
├── schemas/             Pydantic request/response contracts
├── services/            business logic (empty until Phase 3)
├── repositories/        data access (empty until Phase 2)
└── providers/llm/       external service adapters
    └── base.py          LLMProvider interface — no implementation yet
```

**Dependencies point one direction only: inward.**

```
routers → services → repository & provider interfaces
```

A router never contains business logic. A service never imports FastAPI, and
never imports a concrete provider — only the `LLMProvider` interface. A
repository never calls an LLM.

That single rule is what makes the roadmap work: adding RAG in Phase 10 changes
service internals but leaves routers untouched, and adding OpenAI in Phase 18
is a new class in `providers/llm/` with nothing else edited.

The test for whether the layering is real, not just folders: **could you call a
service from a plain CLI script with no web server running?** If not, logic has
leaked upward into the router.

---

## Design decisions

**`async def` for `/health`** — the handler does no blocking work, so it runs
directly on the event loop with no threadpool hop. General rule: `async def`
when the function is non-blocking or awaits async I/O; plain `def` when it does
blocking work (sync DB driver, sync SDK), because FastAPI then offloads it to a
threadpool and keeps the loop free. An `async def` with a blocking call inside
is the worst case — it stalls every other request.

**`get_settings()` as a dependency, not a global** — injecting settings via
`Depends` lets tests override them. Importing a module-level `settings` object
into a service makes that service untestable.

**`@lru_cache` on `get_settings`** — the `.env` file is read and parsed once per
process; every caller gets the same object.

**`groq_api_key` has no default** — required as of Phase 8, once
GenerationService actually calls Groq. Before that it defaulted to `""` so
the app could boot with no provider wired up; now a missing key fails fast
at startup instead of surfacing as a confusing error on the first real
`/generate` request.

**`LLMProvider.generate` is async** — an async contract can wrap a sync SDK, but
a sync contract can't become async later without touching every caller.

**`create_app()` factory** — tests can build a fresh, independently-configured
instance instead of importing whatever global initialised first.

**CORS is development-only** — the allowlist must be narrowed to real origins
before deployment.

---

## Next: Phase 2

PostgreSQL via Supabase — schema design for documents, SQLAlchemy models,
Alembic migrations, and the repository layer that fills the currently-empty
`repositories/` package.