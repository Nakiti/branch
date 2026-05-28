from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from db import get_db, get_anthropic
from models.schemas import SendMessageRequest
from services.auth import get_current_user
from services.context import reconstruct_context

router = APIRouter()

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1024


async def _stream_chat(thread_id: str, user_content: str):
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
                yield f"data: {text}\n\n"
    except Exception as e:
        yield f"data: [ERROR] {str(e)}\n\n"
        return

    # Persist the completed assistant message
    assistant_text = "".join(full_response)
    try:
        await db.table("messages").insert(
            {
                "thread_id": thread_id,
                "role": "assistant",
                "content": assistant_text,
            }
        ).execute()
    except Exception:
        pass  # Don't break the stream if DB write fails

    yield "data: [DONE]\n\n"


@router.post("/chat")
async def chat(
    request: SendMessageRequest,
    user_id: str = Depends(get_current_user),
) -> StreamingResponse:
    db = await get_db()

    # Ownership check
    thread_resp = await db.table("threads").select("owner_id").eq("id", request.thread_id).execute()
    if not thread_resp.data or thread_resp.data[0]["owner_id"] != user_id:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Persist the user message before streaming
    try:
        await db.table("messages").insert(
            {"thread_id": request.thread_id, "role": "user", "content": request.content}
        ).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to save message")

    return StreamingResponse(
        _stream_chat(request.thread_id, request.content),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
