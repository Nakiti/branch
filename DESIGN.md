# Design Document — Branch

## Overview

Branch is a conversational AI app built on an infinite canvas. The core idea is that a chat is not a single linear thread — it is a tree. Any message can be forked into a new independent thread; both the original and the fork continue with their own context. Branches can also be "merged back" into the parent, where Claude synthesizes the branch's key insight and injects it as a special message.

The app is a two-service monorepo: a Next.js frontend and a FastAPI backend, backed by Supabase (Postgres + Auth) and the Anthropic API.

---

## Data Model

```
threads (
  id                    uuid  PK
  owner_id              uuid  → auth.users
  label                 text  nullable
  fork_source_message_id uuid nullable → messages(id)
  created_at            timestamptz
)

messages (
  id                    uuid  PK
  thread_id             uuid  → threads(id)
  role                  text  ("user" | "assistant")
  content               text
  is_merge_artifact     boolean
  merge_source_thread_ids uuid[]
  created_at            timestamptz
)
```

A thread with `fork_source_message_id = NULL` is a root conversation. A thread with a non-null value is a branch, pointing to the exact message it was forked from. **Messages are never copied between threads.** Context is reconstructed lazily at query time.

Row-level security is enabled on both tables so users can only read and write their own data.

---

## Critical Design Decision: The Context Reconstructor

When a branch thread sends a message to Claude, the model needs the full conversation history — not just the messages stored in that thread, but everything leading up to the fork point in the parent thread (and any grandparent threads above that).

The naive approach would be to copy all parent messages into the new thread at fork time. We don't do that. Instead, `backend/services/context.py` implements a recursive **Context Reconstructor** that builds the message list at query time:

```
reconstruct_context(thread_id):
  1. Load the thread record
  2. If fork_source_message_id is null → return this thread's messages
  3. Otherwise:
     a. Find which thread owns fork_source_message_id
     b. Recursively call reconstruct_context on that parent thread
     c. Truncate the result at fork_source_message_id (inclusive)
     d. Append this thread's own messages after the truncation point
     e. Return the assembled list
```

This has a depth limit of 20 to prevent runaway queries on pathological trees. The output maps directly to the `messages` array in the Anthropic API call — every Claude API call in the system goes through this function.

**Why not copy messages?** Copying creates data duplication and means edits or merges in the parent would not propagate. The pointer approach keeps a single source of truth.

---

## Backend Architecture

```
backend/
├── main.py               FastAPI app, CORS, router registration
├── db.py                 Lazy singletons for Supabase client and Anthropic client
├── routes/
│   ├── chat.py           POST /api/chat — streaming chat completion
│   ├── fork.py           POST /api/fork — create a branch thread
│   ├── tree.py           GET  /api/tree — return the full branch tree
│   ├── merge.py          POST /api/merge — synthesize branch into parent
│   └── threads.py        GET/POST /api/threads — list/create root threads
├── services/
│   ├── context.py        Context Reconstructor (described above)
│   ├── merge.py          Claude prompts and synthesis logic
│   └── auth.py           JWT validation, extract user_id from request
├── models/
│   └── schemas.py        Pydantic request/response models
└── eval/
    ├── dataset/          Hand-labeled (branch, parent, ideal_merge) JSON files
    ├── judge.py          LLM-as-judge scorer
    └── run_eval.py       Eval harness entry point
```

### Route Summary

| Route | Method | What it does |
|---|---|---|
| `/api/chat` | POST | Inserts user message, reconstructs context, streams Claude response, persists assistant message |
| `/api/fork` | POST | Validates ownership, creates a new thread with `fork_source_message_id` set — no message copy |
| `/api/tree` | GET | Fetches all user threads, batch-resolves fork message parents, returns recursive `TreeNode` JSON |
| `/api/merge` | POST | Reconstructs both branch and parent contexts, calls merge synthesizer, inserts merge artifact into parent thread |
| `/api/threads` | GET/POST | Lists root threads for the user; creates a new root thread |

Every route validates that the requesting user owns the resource before returning data.

### Streaming

Chat responses use FastAPI's `StreamingResponse` with `media_type="text/event-stream"`. Each token chunk is sent as `data: <chunk>\n\n`. The stream ends with `data: [DONE]\n\n`. After the stream completes, the full assistant message is persisted to the database.

### Merge Synthesis

The merge synthesizer (`services/merge.py`) calls Claude with a prompt that places the full parent conversation context first, followed by the branch conversation. Claude is asked to produce a 2–4 sentence synthesis that captures the single most valuable takeaway from the branch, framed to be useful in the parent conversation. The resulting message is inserted into the parent thread with `is_merge_artifact = true`.

---

## Frontend Architecture

```
frontend/
├── app/
│   ├── page.tsx          Redirects to /canvas
│   ├── auth/page.tsx     Login / signup (Supabase email auth)
│   └── canvas/page.tsx   Main app — sidebar + React Flow canvas
├── components/
│   ├── branch-app.tsx    Root component, loads conversations
│   ├── branch-canvas.tsx React Flow canvas; renders thread nodes and branch edges
│   ├── branch-edge.tsx   Custom bezier edge with a branch icon
│   ├── thread-node.tsx   Custom React Flow node: message list + chat input
│   └── conversation-sidebar.tsx  Left sidebar with root thread list
├── lib/
│   ├── api.ts            Typed fetch wrappers for all backend routes
│   └── supabase.ts       Supabase browser client (anon key)
├── store/
│   └── useStore.ts       Zustand store: threads, messages, canvas positions, streaming state
└── types/
    └── index.ts          Shared TypeScript types (Thread, Message, TreeNode)
```

### Canvas Layout

The infinite canvas is powered by React Flow. Each thread maps to one `ThreadNode` (custom React Flow node) identified by its UUID. Edges connect a parent thread node to a child thread node, with the `sourceHandle` set to `msg-<fork_message_id>` so the edge visually originates from the forked message.

When a conversation is loaded, the tree structure is fetched from `/api/tree`, laid out with a recursive algorithm (root at `{x: 100, y: 300}`, children spread 480px right and 340px apart vertically), and all thread messages are fetched in parallel. Nodes are draggable; positions are kept in the Zustand store.

`nodeTypes` and `edgeTypes` are defined outside the component to avoid infinite re-renders (a React Flow requirement).

### State Management

Zustand manages all client state:

- `conversations` — list of root threads (sidebar)
- `threads` — map of thread_id → Thread for the active conversation tree
- `messages` — map of thread_id → Message[] for all loaded threads
- `nodePositions` — canvas coordinates per thread
- `flowEdges` — React Flow edge descriptors derived from the tree structure
- `streamingThreadId` / `streamingContent` — accumulates in-flight SSE chunks

Streaming updates (`appendStreamChunk`) update only the streaming state; the thread's `messages` entry is replaced only when `finalizeStream` is called with the persisted message list. This avoids layout thrashing in React Flow during streaming.

### Auth

Supabase email/password auth. The frontend uses the `@supabase/ssr` package to read the session from cookies. The JWT access token is attached as a `Bearer` header on every request to the backend. The backend (`services/auth.py`) validates the JWT and extracts the user ID.

---

## Eval Harness

`backend/eval/` contains a dataset of hand-labeled examples (parent context, branch context, ideal merge synthesis) and an LLM-as-judge scorer that rates each synthesis on Coverage, Precision, and Coherence (1–5 each). The harness runs the merge synthesizer against each example and reports mean scores.

---

## Key Design Tradeoffs

**Lazy context reconstruction vs. eager message copy**
Reconstruction at query time adds latency (multiple DB round trips to walk the fork chain) but avoids data duplication and keeps parent/branch contexts in sync. The depth limit of 20 bounds worst-case query count.

**SSE streaming over WebSockets**
SSE is simpler to implement and sufficient for unidirectional server-to-client streaming. WebSockets would be needed for real-time multi-user collaboration, which is out of scope.

**Supabase service key in the backend only**
The backend uses the Supabase service key (which bypasses RLS) and manually enforces ownership in every route. The frontend uses only the anon key and relies on RLS for direct Supabase queries (auth only). This keeps the trust boundary clean.

**Merge artifact in parent thread, not branch**
When a branch is merged back, the synthesis is inserted into the parent thread. This makes the insight available in the main conversation context for future Claude calls, without polluting the branch.
