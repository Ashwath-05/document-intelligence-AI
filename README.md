# AI Document Intelligence Platform

Upload a PDF, then search it, chat with it across multiple turns, and revisit
past conversations later — with every answer grounded in the actual document
content and cited back to the source chunk.

**Live demo:** [documentintel.netlify.app](https://documentintel.netlify.app)

**Backend API docs:** [documentintelligence-176651909902.europe-west1.run.app/docs](https://documentintelligence-176651909902.europe-west1.run.app/docs)

> The free-tier backend spins down after inactivity — the first request after
> a quiet period can take 30-60 seconds to wake up. After that it's instant.

---

## What it does

- **Upload** a PDF — text is extracted, split into overlapping chunks, and
  embedded into a vector store.
- **Search** raw chunks by semantic similarity, no generation involved.
- **Chat** with a document (or across all of them) using retrieval-augmented
  generation — answers are grounded in retrieved chunks and cite their
  sources. Follow-up questions are reformulated against conversation history
  before retrieval, so "what about X?" actually finds the right chunks
  instead of searching for those three words literally.
- **Browse history** — every conversation is saved; pick one up again where
  you left off.

## Architecture

```
+--------------+        HTTPS         +--------------------+
|   Frontend   | --------------------> |      Backend       |
| React + Vite | <-------------------- |  FastAPI (Python)  |
|   (Netlify)  |        JSON           |  (Google Cloud Run)|
+--------------+                       +----------+---------+
                                                   |
                          +------------------------+------------------------+
                          v                         v                         v
                +--------------------+   +------------------+   +---------------------+
                | PostgreSQL +       |   | sentence-        |   |  Groq API            |
                | pgvector           |   | transformers     |   | (openai/gpt-oss-120b,|
                | (Supabase)         |   | (embeddings)     |   |  LLM)                 |
                +--------------------+   +------------------+   +---------------------+
```

Frontend and backend are deployed completely independently — they only
know about each other through a URL (the frontend's `VITE_API_BASE_URL`)
and a CORS allowlist entry on the backend.

## Tech stack

**Backend**
- FastAPI (Python 3.12), Uvicorn
- PostgreSQL + `pgvector` (hosted on Supabase), SQLAlchemy, Alembic migrations
- `sentence-transformers` (`multi-qa-MiniLM-L6-cos-v1`) for embeddings — a
  retrieval-tuned model chosen after real testing showed it outperformed a
  general-purpose one for question-to-passage search
- Groq (`openai/gpt-oss-120b`) for generation
- `pypdf` for text extraction, `tiktoken` for token-aware chunking
- Docker (CPU-only PyTorch build — the default GPU build would otherwise
  pull in several GB of unused CUDA libraries)
- Deployed on Google Cloud Run

**Frontend**
- React + Vite, React Router
- Hand-written CSS (no framework) — a deliberate cyberpunk theme, not a
  default component-library look
- Deployed on Netlify

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/documents` | Upload a PDF (extract, chunk, embed) |
| GET | `/api/v1/documents/{id}` | Get one document by id |
| POST | `/api/v1/search` | Raw vector search over chunks |
| POST | `/api/v1/generate` | One-shot RAG answer, no conversation state |
| POST | `/api/v1/chat` | Multi-turn RAG chat with query reformulation |
| GET | `/api/v1/conversations` | List past conversations |
| GET | `/api/v1/conversations/{id}` | Full transcript of one conversation |

Full interactive docs (request/response schemas, try-it-now) are auto-generated
at `/docs` on the live backend URL above.

## Project structure

```
document-intelligence-AI/
├── app/                    # FastAPI backend
│   ├── api/routes/          # HTTP endpoints
│   ├── services/             # Business logic (extraction, chunking, RAG, chat)
│   ├── repositories/         # Database access
│   ├── providers/            # Swappable embedding/LLM providers
│   ├── models/                # SQLAlchemy models
│   ├── schemas/               # Pydantic request/response contracts
│   └── core/                   # Config, DB connection
├── alembic/                 # Database migrations
├── frontend/                 # React + Vite frontend
│   └── src/
│       ├── pages/              # Upload, Search, Chat, History views
│       ├── components/          # Sidebar, shared UI
│       └── context/              # Client-side document tracking
├── Dockerfile
└── requirements.txt
```

## Running locally

### Backend

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # fill in DATABASE_URL and GROQ_API_KEY
alembic upgrade head               # create the database tables

uvicorn app.main:app --reload
```

Runs on `http://localhost:8000` — interactive docs at `/docs`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env               # point VITE_API_BASE_URL at your backend
npm run dev
```

Runs on `http://localhost:5173` — already in the backend's CORS allowlist
for local development.

## Deployment

**Backend** ships as a Docker container. The `Dockerfile` reads the `PORT`
environment variable at runtime rather than a hardcoded port, so the same
image works unmodified across platforms (currently Google Cloud Run;
previously tested on Render). Required environment variables:
`DATABASE_URL`, `GROQ_API_KEY`.

**Frontend** builds to static files (`npm run build` -> `dist/`) and deploys
to Netlify. Build settings: base directory `frontend`, build command
`npm run build`, publish directory `frontend/dist`. Requires one environment
variable: `VITE_API_BASE_URL`, pointing at wherever the backend is live —
Vite bakes this in at build time, so changing it always requires a fresh
build, not just a settings change.

Whichever platform hosts the frontend, its domain needs to be added to the
backend's CORS allowlist in `app/main.py`, or every request from it will be
silently blocked by the browser.

## Notable engineering decisions

A few things worth knowing if you're reading the code, not just running it:

- **Cosine distance, not similarity.** pgvector reports `<=>` as a distance
  (lower = more similar), the opposite of the intuitive "higher score is
  better" — the RAG threshold (`0.75`) was tuned from real query testing, not
  guessed.
- **Query reformulation is a separate step from generation.** A follow-up
  like "what about X?" gets rewritten into a standalone question *before*
  retrieval — handing raw follow-ups to the vector search would return
  irrelevant chunks even if the final LLM prompt has perfect conversation
  history.
- **The backend migrated from Render to Cloud Run mid-project** after
  document uploads were reliably OOM-crashing on Render's free 512MB RAM
  tier — `torch` plus the embedding model alone consume a large share of
  that before a single request is even processed. Cloud Run's free tier
  allows configuring real memory headroom (2GB here) while staying free at
  low traffic.
- **No OCR.** Scanned/image-only PDFs are explicitly rejected with a clear
  error rather than silently returning nothing — text extraction only reads
  a PDF's real text layer.
