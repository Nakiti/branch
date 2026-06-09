from fastapi import APIRouter, Depends, HTTPException

from db import get_db, get_anthropic
from models.schemas import ForkRequest, ForkResponse
from services.auth import get_current_user

router = APIRouter()

_LABEL_PROMPT = """Generate a very short branch label (2-4 words, title case) for a conversation branch that starts from the following message. The label should capture the specific topic or question being explored. Reply with ONLY the label, nothing else.

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
        return "Branch"


@router.post("/fork", response_model=ForkResponse)
async def fork_thread(
    request: ForkRequest,
    user_id: str = Depends(get_current_user),
) -> ForkResponse:
    db = await get_db()

    # Look up the message to fork from (fetch content for label generation)
    msg_resp = await db.table("messages").select("id,thread_id,content").eq("id", request.message_id).execute()
    if not msg_resp.data:
        raise HTTPException(status_code=404, detail="Message not found")

    msg = msg_resp.data[0]
    parent_thread_id = msg["thread_id"]

    # Verify the user owns the thread containing that message
    thread_resp = await db.table("threads").select("owner_id").eq("id", parent_thread_id).execute()
    if not thread_resp.data or thread_resp.data[0]["owner_id"] != user_id:
        raise HTTPException(status_code=404, detail="Thread not found")

    label = await _generate_label(msg["content"])

    # Create the new branch thread — no message copying, context reconstructed lazily
    try:
        new_thread_resp = await db.table("threads").insert(
            {
                "owner_id": user_id,
                "fork_source_message_id": request.message_id,
                "label": label,
            }
        ).execute()
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to create branch thread")

    new_thread_id = new_thread_resp.data[0]["id"]
    return ForkResponse(thread_id=new_thread_id, label=label)
