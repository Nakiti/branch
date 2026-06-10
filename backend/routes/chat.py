from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from db import get_db, get_anthropic
from models.schemas import SendMessageRequest
from services.auth import get_current_user
from services.context import reconstruct_context

router = APIRouter()

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 8192

_LABEL_PROMPT = """Generate a very short conversation title (2-5 words, title case) based on the user's first message. Capture the main topic or question. Reply with ONLY the title, nothing else.

Message:
{content}"""


async def _generate_label(content: str) -> str:
    client = get_anthropic()
    try:
        resp = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20,
            messages=[{"role": "user", "content": _LABEL_PROMPT.format(content=content[:500])}],
        )
        return resp.content[0].text.strip().strip('"').strip("'")
    except Exception:
        return "New Conversation"


async def _stream_chat(thread_id: str, user_content: str, label_needed: bool = False):
    db = await get_db()
    client = get_anthropic()

    context = await reconstruct_context(thread_id)
    messages = [{"role": m["role"], "content": m["content"]} for m in context]
    messages.append({"role": "user", "content": user_content})

    full_response: list[str] = []
    try:
        async with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                full_response.append(text)
                # SSE spec: each newline inside the payload must start a new
                # data: line, otherwise the client's data:-prefix filter drops
                # continuation lines (breaking code blocks, lists, etc.).
                encoded = text.replace('\n', '\ndata: ')
                yield f"data: {encoded}\n\n"
    except Exception as e:
        yield f"data: [ERROR] {str(e)}\n\n"
        return

    # Persist the completed assistant message
    assistant_text = "".join(full_response)
    try:
        await db.table("messages").insert(
            {"thread_id": thread_id, "role": "assistant", "content": assistant_text}
        ).execute()
    except Exception:
        pass

    # Generate and persist a label for root threads on their first message
    if label_needed:
        label = await _generate_label(user_content)
        try:
            await db.table("threads").update({"label": label}).eq("id", thread_id).execute()
            yield f"data: [LABEL:{label}]\n\n"
        except Exception:
            pass

    yield "data: [DONE]\n\n"


@router.post("/chat")
async def chat(
    request: SendMessageRequest,
    user_id: str = Depends(get_current_user),
) -> StreamingResponse:
    db = await get_db()

    # Ownership check — also fetch fork_source_message_id to detect root threads
    thread_resp = (
        await db.table("threads")
        .select("owner_id, fork_source_message_id")
        .eq("id", request.thread_id)
        .execute()
    )
    if not thread_resp.data or thread_resp.data[0]["owner_id"] != user_id:
        raise HTTPException(status_code=404, detail="Thread not found")

    thread = thread_resp.data[0]
    is_root = thread["fork_source_message_id"] is None

    # Check whether this is the first message in the thread
    existing = (
        await db.table("messages").select("id").eq("thread_id", request.thread_id).limit(1).execute()
    )
    label_needed = is_root and len(existing.data) == 0

    # Persist the user message before streaming
    try:
        await db.table("messages").insert(
            {"thread_id": request.thread_id, "role": "user", "content": request.content}
        ).execute()
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to save message")

    return StreamingResponse(
        _stream_chat(request.thread_id, request.content, label_needed),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
