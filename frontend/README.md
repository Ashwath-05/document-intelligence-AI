# DOC/INTEL — Frontend

React + Vite frontend for the AI Document Intelligence Platform backend.

## Setup

```bash
npm install
cp .env.example .env
```

Edit `.env` and set `VITE_API_BASE_URL` to your backend's URL (Render or
Cloud Run, whichever is currently live).

## Run locally

```bash
npm run dev
```

Opens on `http://localhost:5173` — this exact origin is already in the
backend's CORS allowlist, so no backend changes are needed for local dev.

## Build for production

```bash
npm run build
```

Outputs static files to `dist/` — deployable to Vercel, Netlify, or any
static host (this frontend, unlike the Python backend, is exactly what
Vercel is built for).

## Pages

- **Upload** — upload a PDF, tracked client-side in this browser (the
  backend has no "list all documents" endpoint by design)
- **Search** — raw vector search over chunks, no generation
- **Chat** — multi-turn conversation with query reformulation on follow-ups
- **History** — browse past conversations, resume any of them in Chat
