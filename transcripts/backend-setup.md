Set up the FastAPI backend for Branch from scratch. Read CLAUDE.md and backend/CLAUDE.md before writing any code.
What to build
Scaffold and fully implement the backend so that all four routes work end-to-end and are manually testable with curl. Do not stub or leave placeholder implementations — every route should actually work.
Step 1: Project scaffold
Create the following file structure exactly as specified in backend/CLAUDE.md:
backend/
├── main.py
├── routes/
│   ├── __init__.py
│   ├── chat.py
│   ├── fork.py
│   ├── tree.py
│   └── merge.py
├── services/
│   ├── __init__.py
│   ├── context.py
│   ├── merge.py
│   └── auth.py
├── models/
│   ├── __init__.py
│   └── schemas.py
├── eval/
│   ├── dataset/
│   ├── judge.py
│   └── run_eval.py
├── requirements.txt
└── .env.example
Step 2: Dependencies
Write requirements.txt with pinned versions:

fastapi
uvicorn[standard]
anthropic
supabase
python-dotenv
pydantic
httpx

Step 3: Supabase schema
Create supabase/schema.sql at the repo root (not inside backend/) with the exact schema from the root CLAUDE.md. Include:

threads table
messages table
RLS policies: users can only select/insert/update their own threads and messages (owner_id = auth.uid())
Indexes on: messages.thread_id, threads.owner_id, threads.fork_source_message_id

Step 4: Implement in this exact order
4a. models/schemas.py
All Pydantic request and response models from backend/CLAUDE.md. Add a Message and Thread model matching the DB schema exactly.
4b. services/auth.py
get_current_user(request: Request) -> str FastAPI dependency. Extract the Bearer token from the Authorization header, verify it against Supabase using the Supabase admin client, return the user_id uuid as a string. Raise HTTPException 401 if missing or invalid.
4c. services/context.py
The Context Reconstructor. Implement exactly as specified in backend/CLAUDE.md:

reconstruct_context(thread_id: str) -> list[dict]
Walk the fork chain recursively up to root
Truncate parent context at the fork point (inclusive of the fork message)
Append this thread's own messages
Depth limit of 20
Batch fetch threads with a single IN query rather than N+1 lookups
Write a standalone test at the bottom under if __name__ == "__main__" that mocks a 3-level deep fork chain and asserts the output is correct

4d. routes/fork.py
POST /fork

Depends on get_current_user
Validate the user owns the thread containing message_id
Insert new Thread record with fork_source_message_id set
Return ForkResponse

4e. routes/tree.py
GET /tree?root_thread_id=<uuid>

Depends on get_current_user
Validate user owns root_thread_id
Fetch all threads for this user, build the tree by walking fork_source_message_id relationships
Return recursive TreeNode structure as JSON

4f. routes/chat.py
POST /chat

Depends on get_current_user
Validate user owns thread_id
Insert user message to DB
Call reconstruct_context(thread_id)
Append new user message to context
Stream response from Claude using anthropic.messages.stream()
Yield chunks as SSE: each chunk formatted as f"data: {chunk}\n\n", end with data: [DONE]\n\n
On stream complete, insert the full assistant message to DB
Return StreamingResponse with media_type="text/event-stream"
Model: claude-sonnet-4-20250514, max_tokens: 1024

4g. services/merge.py + routes/merge.py
POST /merge

Depends on get_current_user
Validate user owns branch_thread_id
Find parent thread (the thread that owns the message pointed to by branch.fork_source_message_id)
Reconstruct both contexts
Call Claude with the MERGE_PROMPT from backend/CLAUDE.md (non-streaming, single call)
Insert merge artifact message into parent thread with is_merge_artifact=true and merge_source_thread_ids set
Return MergeResponse

4h. main.py

Create FastAPI app with title "Branch API"
Add CORS middleware: allow origins ["http://localhost:3000"] plus the FRONTEND_URL env var
Register all four routers with prefix /api
Add a GET /health route that returns {"status": "ok"}

Step 5: .env.example
ANTHROPIC_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
FRONTEND_URL=http://localhost:3000
Step 6: Verify
After scaffolding, run through this checklist:

pip install -r requirements.txt completes without errors
python services/context.py runs the mock test and passes
uvicorn main:app --reload starts without import errors
curl http://localhost:8000/health returns {"status": "ok"}
Check that every route has an ownership check before any DB operation
Check that no route queries messages directly without going through reconstruct_context

Do not move on until all six checks pass. If any check fails, fix it before continuing.
What NOT to do

Do not use synchronous DB calls — everything must be async
Do not expose raw Supabase/Postgres errors to the client
Do not hardcode any credentials
Do not skip the ownership checks
Do not copy message content between threads in the fork handler
Do not define a route that calls Claude without first calling reconstruct_context