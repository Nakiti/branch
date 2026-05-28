# Branch — Project CLAUDE.md

## What this project is
Branch is a conversational AI app built on an infinite canvas. Each chat thread is a node on the canvas. Users can fork any message into a new independent thread — a new node appears on the canvas connected to the parent by a bezier line. Both threads continue independently with their own context. Users can also "merge back" — synthesizing insights from a branch into the parent thread as a special merge artifact message.

The core technical insight: a branch does NOT copy messages. It stores a pointer (`fork_source_message_id`) to the message it branched from. Context is reconstructed at query time by walking the fork chain up to the root.

## Monorepo structure
```
/
├── frontend/          # Next.js app (React, React Flow, Tailwind)
├── backend/           # FastAPI (Python)
│   ├── routes/        # chat.py, fork.py, tree.py, merge.py
│   ├── services/      # context.py (Context Reconstructor), merge.py
│   └── main.py
├── supabase/
│   └── schema.sql     # source of truth for DB schema
└── CLAUDE.md
```

## Tech stack
- **Frontend:** Next.js 14, React, React Flow (canvas/nodes/edges), Tailwind CSS
- **Backend:** FastAPI (Python), Anthropic Python SDK
- **Database:** Supabase (Postgres + built-in auth)
- **Deploy:** Vercel (frontend), Railway (backend)
- **AI:** claude-sonnet-4-20250514 for chat + merge synthesis

## Database schema (source of truth: /supabase/schema.sql)

```sql
-- Users managed by Supabase Auth (auth.users)

threads (
  id uuid primary key,
  owner_id uuid references auth.users,
  label text,
  fork_source_message_id uuid references messages(id), -- null = root thread
  created_at timestamptz
)

messages (
  id uuid primary key,
  thread_id uuid references threads(id),
  role text check (role in ('user', 'assistant')),
  content text,
  is_merge_artifact boolean default false,
  merge_source_thread_ids uuid[],  -- which branches fed this merge
  created_at timestamptz
)
```

## Critical architectural rule: Context Reconstructor
`/backend/services/context.py` is the most important service. It takes a `thread_id` and returns the full ordered message list for that thread by:
1. Walking up the fork chain (via `fork_source_message_id`) to the root thread
2. Collecting messages up to the fork point at each level
3. Appending this thread's own messages at the end

Every Claude API call MUST go through the Context Reconstructor. Never query messages directly for a thread without it — you will get wrong context.

## API routes
| Route | Method | Description |
|-------|--------|-------------|
| `/chat` | POST | Send message to a thread, stream response |
| `/fork` | POST | Fork at a message_id, returns new thread_id |
| `/tree` | GET | Returns full branch tree for a root thread |
| `/merge` | POST | Synthesize branch back into parent thread |

## Environment variables (never commit)
```
ANTHROPIC_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

## Code conventions
- Python: async everywhere in FastAPI, type hints on all function signatures
- TypeScript: strict mode on, no `any`
- All Supabase queries in the backend (service key), never from the frontend directly except auth
- Streaming: use FastAPI `StreamingResponse` + Anthropic stream helpers for chat
- Never copy message content between threads — always reconstruct via fork chain

## Current status
- [ ] Supabase schema deployed
- [ ] Context Reconstructor implemented and tested
- [ ] Chat Completion Service wired to Claude API
- [ ] Fork Handler working end-to-end
- [ ] Branch Tree API returning correct tree structure
- [ ] Merge Synthesizer (Scenario 1)
- [ ] Frontend wired to real backend (replacing Lovable dummy data)
- [ ] Deployed to Vercel + Railway

## Known gotchas
- React Flow nodes need stable IDs — use thread UUIDs as node IDs directly
- Supabase RLS (row level security) must be enabled — all queries should be scoped to `owner_id = auth.uid()`
- The merge prompt is sensitive to context window order — parent context must come before branch context in the prompt
- Fork chain walking can recurse deeply for long branch trees — add a depth limit of 20 to prevent runaway queries