from fastapi import APIRouter, Depends, HTTPException

from db import get_db
from models.schemas import ForkRequest, ForkResponse
from services.auth import get_current_user

router = APIRouter()


@router.post("/fork", response_model=ForkResponse)
async def fork_thread(
    request: ForkRequest,
    user_id: str = Depends(get_current_user),
) -> ForkResponse:
    db = await get_db()

    # Look up the message to fork from
    msg_resp = await db.table("messages").select("id,thread_id").eq("id", request.message_id).execute()
    if not msg_resp.data:
        raise HTTPException(status_code=404, detail="Message not found")

    parent_thread_id = msg_resp.data[0]["thread_id"]

    # Verify the user owns the thread containing that message
    thread_resp = await db.table("threads").select("owner_id").eq("id", parent_thread_id).execute()
    if not thread_resp.data or thread_resp.data[0]["owner_id"] != user_id:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Create the new branch thread — no message copying, context reconstructed lazily
    try:
        new_thread_resp = await db.table("threads").insert(
            {
                "owner_id": user_id,
                "fork_source_message_id": request.message_id,
                "label": None,
            }
        ).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create branch thread")

    new_thread_id = new_thread_resp.data[0]["id"]
    return ForkResponse(thread_id=new_thread_id)
