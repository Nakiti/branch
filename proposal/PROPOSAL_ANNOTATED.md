
## Title: Branch

### One Sentence Description
Branch is a generative AI chat applicaiton where users can split a single threaded chat into independent conversations that can be merged to provide a more intuitive chat interface (Ship it with auth + live URL, Generation as the point (maybe))

### Past project reference
None

### Planned Technologies

> **Status notes:**

Frontend: Next.js, React Flow for UI
> **(a) Implemented as written.** `frontend/package.json` lists `next@^14.2.29` and `reactflow@^11.11.4`. React Flow is used in `frontend/components/branch-canvas.tsx` to render the infinite canvas, thread nodes, and bezier branch edges.

Backend: FastAPI (Python)
> **(a) Implemented as written.** `backend/main.py` bootstraps the FastAPI app and registers all routers. Routes live in `backend/routes/` and are served via uvicorn.

Database: Supabase
> **(a) Implemented as written.** Schema defined in `supabase/schema.sql` (threads + messages tables, RLS policies). The Python `supabase-py` async client is initialized in `backend/db.py` and used in all routes.

AI: Anthropic Claude API
> **(a) Implemented as written.** `backend/routes/chat.py` uses `claude-sonnet-4-20250514` for streaming chat completions. `backend/services/merge.py` uses the same model for merge synthesis.

Deployment: Vercel (frontend), Railway (backend)
> **(b) Planned to be implemented.** The target deployment is still Vercel (frontend) and Railway (backend). Environment variable wiring is in place (`FRONTEND_URL` in backend CORS config, `NEXT_PUBLIC_BACKEND_URL` in frontend). Not yet confirmed live.


### First Deliverable
A logged in user can have a conversation with the LLM, fork any message into a new branch, continue both the original and new branches independently, and then trigger a "merge back" that synthesizes the the branch's conversation into a contextual message in the parent thread or new thread. 

> **(a) Implemented as written.** All four pieces are in place:
> - Auth: Supabase email auth at `frontend/app/auth/page.tsx`; JWT validated per-request in `backend/services/auth.py`.
> - Chat: `backend/routes/chat.py` streams responses via SSE; each thread's full context (including inherited parent history) is reconstructed before the Claude API call.
> - Fork: `backend/routes/fork.py` creates a new thread with `fork_source_message_id` pointing to the forked message; no messages are copied.
> - Merge back: `backend/routes/merge.py` + `backend/services/merge.py` reconstruct branch and parent contexts, call Claude to produce a 2–4 sentence synthesis, and insert it as a merge artifact message in the parent thread.
>
> One minor scope change: the merge artifact is always injected into the parent thread (the "or new thread" option was dropped — parent-only is cleaner and keeps context coherent).


### Architecture for First Deliverable

> **Status notes:**

1. Auth & Session Management
> **(a) Implemented as written.** Supabase email/password auth handles sessions on the frontend. `backend/services/auth.py` validates the Supabase JWT and extracts `user_id`. Every route uses `Depends(get_current_user)` and checks resource ownership before returning data.

2. Thread Storage in Supabase --> { id, owner_id, created_at, fork_source_message_id? }
> **(a) Implemented as written.** `supabase/schema.sql` defines `threads(id uuid PK, owner_id uuid, label text, fork_source_message_id uuid nullable, created_at timestamptz)` — matching the proposed shape exactly.

3. Chat Completion Service --> Fetches full message history up to current point, call Claude API, stream response back
> **(a) Implemented as written.** `backend/routes/chat.py` calls `reconstruct_context(thread_id)` to get the full ordered message history, appends the new user message, then streams the Claude response as SSE chunks. The completed assistant message is persisted after the stream closes.

4. Fork Creation --> create a new thread and the context is supplied through walking up the fork chain (context reconstruction)
> **(a) Implemented as written.** `backend/routes/fork.py` creates a new `threads` row with `fork_source_message_id` set to the target message. No messages are copied; context is reconstructed lazily at chat time via the Context Reconstructor.

5. Context Reconstruction --> this is an ordered list of messages representing the full context, follow the chain up, and append this thread's own messages
> **(a) Implemented as written.** `backend/services/context.py` implements this recursively: walk up the fork chain to the root, truncate each ancestor thread's messages at its fork point (inclusive), then append the current thread's own messages. A depth limit of 20 prevents runaway queries on deep trees.

6. Merge Synthesizer --> Calls Claude summarzing the new branch and the and then injecting it to the main thread
> **(a) Implemented as written.** `backend/services/merge.py` formats the parent and branch contexts and calls Claude with a prompt asking for a 2–4 sentence synthesis of the branch's most valuable takeaway. `backend/routes/merge.py` inserts the result into the parent thread as a message with `is_merge_artifact = true`.

7. Chat UI --> Renders message history for a given thread, branch here button where user can branch from any point in any conversation, This will be an intuitive UI that will likely take several repitions of modification
> **(a) Implemented as written.** `frontend/components/thread-node.tsx` is a custom React Flow node that renders the message list and chat input for a thread. Branch buttons appear on assistant messages. The canvas (`frontend/components/branch-canvas.tsx`) renders all threads in the active conversation tree as nodes with bezier edges connecting parent to child.


### After First Deliverable Goals

- Visual tree view
> **(a) Implemented — delivered ahead of schedule as part of the core.** The React Flow infinite canvas renders the full branch tree with one node per thread and bezier edges connecting each branch to its parent thread. Thread position on the canvas is persisted in the Zustand store and nodes are draggable. This ended up being central to the UX rather than a stretch goal.

- Auto suggested branch naming by Claude
> **(c) No longer planned.** Branches currently use null labels (displayed generically in the sidebar). Auto-naming was deprioritized in favor of getting core fork/merge functionality solid.

- Conflict detection - where the conversation of one branch contradicts the conversation of another branch
> **(c) No longer planned.** This would require comparing branch contexts pair-wise and adding latency per message. The multi-branch merge synthesizer (`services/merge.py` `synthesize_multi_merge`) surfaces divergence implicitly when merging, but explicit conflict detection is out of scope.

- Eval harness
> **(a) Implemented as written.** `backend/eval/` contains a dataset of hand-labeled examples (`dataset/`), an LLM-as-judge scorer (`judge.py`) that rates each synthesis on Coverage, Precision, and Coherence (1–5 each), and a harness entry point (`run_eval.py`).

- Branch suggestion - Claude detects when a chat within a conversation is a tangent and prompts the user to branch
> **(c) No longer planned.** Detecting conversational tangents would require a model call on every message, adding latency and cost. Deprioritized in favor of user-initiated branching.
