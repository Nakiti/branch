# Branch

Branch is a conversational AI app built on an infinite canvas. Each chat thread is a node on the canvas. You can fork any message into a new independent thread — a new node appears connected to its parent by a bezier edge. Both threads continue independently with their own context. You can also "merge back" — synthesizing insights from a branch into the parent thread as a special merge artifact message.

## Features

- **Infinite canvas** — chat threads rendered as draggable nodes via React Flow
- **Fork at any message** — split a conversation at any assistant reply; the branch inherits full parent context up to the fork point without copying messages
- **Merge synthesis** — trigger a merge to have Claude summarize the branch's key insight and inject it into the parent thread as a merge artifact
- **Streaming responses** — chat completions stream token-by-token via SSE
- **Auth** — Supabase email/password auth; all threads and messages are scoped per user

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, React Flow, Tailwind CSS, Zustand |
| Backend | FastAPI (Python 3.11+), Anthropic Python SDK |
| Database | Supabase (Postgres + Auth) |
| AI | claude-sonnet-4-20250514 |
| Deploy | Vercel (frontend), Railway (backend) |

## Repository Structure

```
/
├── frontend/          # Next.js app
│   ├── app/           # App router pages (auth, canvas)
│   ├── components/    # React Flow nodes, sidebar, chat UI
│   ├── lib/           # API client, Supabase client, stream helpers
│   ├── store/         # Zustand store
│   └── types/         # Shared TypeScript types
├── backend/           # FastAPI app
│   ├── routes/        # chat, fork, tree, merge, threads
│   ├── services/      # Context Reconstructor, merge synthesizer, auth
│   ├── models/        # Pydantic schemas
│   └── eval/          # LLM-as-judge eval harness
└── supabase/
    └── schema.sql     # Database schema + RLS policies
```

## Running Locally

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Supabase project with the schema from `supabase/schema.sql` applied
- An Anthropic API key

### Environment Variables

Create `backend/.env`:
```
ANTHROPIC_API_KEY=your_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_key
FRONTEND_URL=http://localhost:3000
```

Create `frontend/.env.local`:
```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

### Apply the Database Schema

In the Supabase SQL editor (or via the CLI), run the contents of `supabase/schema.sql`. This creates the `threads` and `messages` tables, indexes, and RLS policies.

### Start the Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Sign up for an account, create a conversation, and start branching.
