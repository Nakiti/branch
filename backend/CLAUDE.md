# Backend CLAUDE.md

## Stack
- FastAPI (Python 3.11+)
- Anthropic Python SDK — chat completions + merge synthesis
- Supabase Python client (service key) — all DB access
- asyncpg / supabase-py — async Postgres queries
- Python-dotenv — env vars

## Directory structure
```
backend/
├── main.py                  # FastAPI app, CORS, router registration
├── routes/
│   ├── chat.py              # POST /chat — streaming chat completion
│   ├── fork.py              # POST /fork — create branch thread
│   ├── tree.py              # GET /tree — return branch tree for a root thread
│   └── merge.py             # POST /merge — synthesize branch back to parent
├── services/
│   ├── context.py           # Context Reconstructor (CRITICAL — read carefully)
│   ├── merge.py             # Merge Synthesizer logic + prompt
│   └── auth.py              # JWT validation, extract user_id from request
├── models/
│   └── schemas.py           # Pydantic request/response models
└── eval/
    ├── dataset/             # hand-labeled (branch, parent, ideal_merge) JSON files
    ├── judge.py             # LLM-as-judge scorer
    └── run_eval.py          # eval harness entry point
```

## Environment variables
```
ANTHROPIC_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=       # service key — bypasses RLS, only used server-side
```

## Pydantic schemas (source of truth: /backend/models/schemas.py)
```python
class SendMessageRequest(BaseModel):
    thread_id: str
    content: str

class ForkRequest(BaseModel):
    message_id: str          # the message to fork FROM

class ForkResponse(BaseModel):
    thread_id: str           # the new branch thread id

class TreeRequest(BaseModel):
    root_thread_id: str

class MergeRequest(BaseModel):
    branch_thread_id: str    # the branch to synthesize from

class MergeResponse(BaseModel):
    message: dict            # the merge artifact message that was inserted
```

## CRITICAL: Context Reconstructor (/backend/services/context.py)

This is the most important service. Read this before touching any route.

```python
async def reconstruct_context(thread_id: str) -> list[dict]:
    """
    Returns full ordered message list for a thread by walking the fork chain.

    Algorithm:
    1. Load the thread record for thread_id
    2. If fork_source_message_id is None: this is a root thread, return its messages
    3. If fork_source_message_id is set:
       a. Find which thread owns that message (parent_thread_id)
       b. Recursively call reconstruct_context(parent_thread_id)
       c. Truncate the result at fork_source_message_id (inclusive)
       d. Append this thread's own messages after the truncation point
    4. Return the assembled list

    NEVER skip this function and query messages directly.
    NEVER include messages from the parent that come AFTER the fork point.
    Add a recursion depth limit of 20 to prevent runaway queries.
    """
```

Every Claude API call must use this. The output maps directly to the `messages` array in the Anthropic API call:
```python
context = await reconstruct_context(thread_id)
messages = [{"role": m["role"], "content": m["content"]} for m in context]
# then append the new user message
messages.append({"role": "user", "content": new_content})
```

## Route implementations

### POST /chat (routes/chat.py)
```python
# 1. Validate user owns thread_id (auth check)
# 2. Insert user message to DB
# 3. Call reconstruct_context(thread_id)
# 4. Stream Claude API response using anthropic client.messages.stream()
# 5. On stream complete: insert assistant message to DB
# 6. Return StreamingResponse (text/event-stream)
# Use: anthropic.messages.stream() context manager, yield chunks as SSE
```

### POST /fork (routes/fork.py)
```python
# 1. Validate user owns the thread that contains message_id
# 2. Insert new Thread record:
#    { owner_id: user_id, fork_source_message_id: message_id, label: null }
# 3. Return { thread_id: new_thread.id }
# DO NOT copy any messages — context is reconstructed lazily
```

### GET /tree (routes/tree.py)
```python
# 1. Validate user owns root_thread_id
# 2. Fetch all threads owned by user where root is ancestor
#    (walk forward: find all threads whose fork chain leads to root_thread_id)
# 3. Build recursive TreeNode structure
# 4. Return as JSON
# TreeNode: { thread, fork_message_id, children: TreeNode[] }
```

### POST /merge (routes/merge.py)
```python
# 1. Validate user owns branch_thread_id
# 2. Find parent: thread where branch.fork_source_message_id is in parent's messages
# 3. Reconstruct branch context via reconstruct_context(branch_thread_id)
# 4. Reconstruct parent context via reconstruct_context(parent_thread_id)
#    (use current end of parent, not just up to fork point)
# 5. Call merge synthesizer — see services/merge.py
# 6. Insert merge artifact message into PARENT thread:
#    { role: 'assistant', is_merge_artifact: true,
#      merge_source_thread_ids: [branch_thread_id], content: synthesis }
# 7. Return the inserted message
```

## Merge synthesizer prompt (/backend/services/merge.py)

Scenario 1 (branch finished, parent may or may not have continued):
```python
MERGE_PROMPT = """You are synthesizing insights from a side conversation branch back into a main thread.

MAIN CONVERSATION (up to current point):
{parent_context}

BRANCH EXPLORATION (started from the main conversation, explored independently):
{branch_context}

Task: Write a single concise message (2-4 sentences) that captures the most important insight or conclusion from the branch exploration, framed in a way that's useful for continuing the main conversation. Focus on what the main conversation would benefit most from knowing. Do not summarize the branch exhaustively — identify the single most valuable takeaway."""
```

For cross-branch synthesis (Scenario 3, multiple branches from same fork):
```python
MULTI_MERGE_PROMPT = """You are synthesizing insights from multiple parallel explorations back into a main thread.

MAIN CONVERSATION (context up to the fork point):
{parent_context}

BRANCH EXPLORATIONS:
{branches}  # formatted as "--- Branch: {label} ---\n{context}\n" for each

Task: Write a structured synthesis (use brief headers) that:
1. Identifies conclusions that appeared across multiple branches (consensus)
2. Identifies where branches reached different conclusions (divergence)  
3. Surfaces the single strongest unique insight from each branch

Keep it concise — this will be injected into the main conversation as a reference point."""
```

## Auth (/backend/services/auth.py)
```python
async def get_current_user(request: Request) -> str:
    """Extract and validate Supabase JWT, return user_id (uuid string).
    Raise 401 if missing or invalid.
    Use as FastAPI dependency: user_id: str = Depends(get_current_user)
    """
```

Every route must use `Depends(get_current_user)` and verify ownership before any DB operation.

## Eval harness (/backend/eval/)

Dataset format (`/backend/eval/dataset/*.json`):
```json
{
  "id": "eval_001",
  "parent_context": [...],     // messages array
  "branch_context": [...],     // messages array
  "fork_point_index": 3,       // which message in parent was forked from
  "ideal_merge": "...",        // hand-written ideal synthesis
  "key_conclusions": ["...", "..."]  // must-include facts for recall scoring
}
```

Judge prompt (`/backend/eval/judge.py`):
```python
JUDGE_PROMPT = """Score this merge synthesis on three dimensions (1-5 each):

PARENT CONTEXT: {parent_context}
BRANCH CONTEXT: {branch_context}
SYNTHESIS TO SCORE: {synthesis}
IDEAL SYNTHESIS: {ideal}

Score:
1. Coverage: Did it capture the key conclusions from the branch? (1=missed most, 5=captured all)
2. Precision: Did it avoid injecting noise or irrelevant content? (1=lots of noise, 5=clean)
3. Coherence: Would this flow naturally in the main conversation? (1=jarring, 5=seamless)

Respond in JSON: {"coverage": N, "precision": N, "coherence": N, "reasoning": "..."}"""
```

## Code conventions
- All route handlers are `async def`
- All DB calls are async (use `await supabase.table(...).select(...)`)  
- Type hints on every function signature
- Pydantic models for all request bodies and response shapes
- Ownership check pattern: always verify `thread.owner_id == user_id` before returning data
- Never expose raw Postgres errors to the client — catch and return 400/404/500 with a message

## Known gotchas
- Supabase service key bypasses RLS — always manually check ownership in routes, don't rely on RLS as a safety net when using service key
- `anthropic.messages.stream()` is a context manager — use `async with client.messages.stream(...) as stream`
- SSE format for StreamingResponse: each chunk must be `f"data: {chunk}\n\n"`, end with `data: [DONE]\n\n`
- Recursion in Context Reconstructor: add `depth` param and raise after 20 levels to prevent stack overflow on pathological trees
- Fork chain queries: do NOT do N+1 queries walking the chain one thread at a time — batch fetch all threads in the chain with a single `IN` query after the first lookup