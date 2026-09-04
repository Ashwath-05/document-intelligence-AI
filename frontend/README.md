# DOC/INTEL — Frontend

React + Vite frontend for the [AI Document Intelligence Platform](../README.md)
— upload documents, search them, chat with them across multiple turns, and
browse past conversations. Cyberpunk-themed UI, hand-written CSS, no
component framework.

**Live:** [documentintel.netlify.app](https://documentintel.netlify.app)

## Setup

```bash
npm install
cp .env.example .env
```

Edit `.env` and set `VITE_API_BASE_URL` to your backend's URL.

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

Outputs static files to `dist/`, deployable to Netlify, Vercel, or any static
host. Currently deployed on Netlify with:
- Base directory: `frontend`
- Build command: `npm run build`
- Publish directory: `frontend/dist`
- Environment variable: `VITE_API_BASE_URL`

`VITE_API_BASE_URL` is baked into the build at compile time (that's how Vite
env vars work) — changing it always requires a fresh build, not just an
updated setting.

## Pages

- **Upload** — upload a PDF, tracked client-side in this browser (the
  backend has no "list all documents" endpoint by design)
- **Search** — raw vector search over chunks, no generation
- **Chat** — multi-turn conversation with query reformulation on follow-ups,
  sources cited under each answer
- **History** — browse past conversations, resume any of them in Chat

## Stack

React, React Router, Vite. No CSS framework — theme tokens and layout live in
`src/theme.css` and `src/layout.css`.
