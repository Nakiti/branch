from fastapi import APIRouter, Depends, HTTPException

from db import get_db
from models.schemas import MergeRequest, MergeResponse
from services.auth import get_current_user
from services.context import reconstruct_context
from services.merge import synthesize_merge

router = APIRouter()


@router.post("/merge", response_model=MergeResponse)
async def merge_branch(
    request: MergeRequest,
    user_id: str = Depends(get_current_user),
) -> MergeResponse:
    db = await get_db()

    # Ownership check on branch thread
    branch_resp = await db.table("threads").select("*").eq("id", request.branch_thread_id).execute()
    if not branch_resp.data or branch_resp.data[0]["owner_id"] != user_id:
        raise HTTPException(status_code=404, detail="Branch thread not found")

    branch_thread = branch_resp.data[0]
    fork_source_id = branch_thread.get("fork_source_message_id")
    if not fork_source_id:
        raise HTTPException(status_code=400, detail="Branch thread has no fork source — cannot merge a root thread")

    # Find the parent thread that owns the fork source message
    msg_resp = await db.table("messages").select("thread_id").eq("id", fork_source_id).execute()
    if not msg_resp.data:
        raise HTTPException(status_code=404, detail="Fork source message not found")

    parent_thread_id = msg_resp.data[0]["thread_id"]

    # Ownership check on parent thread (defensive — fork origin must also belong to user)
    parent_resp = await db.table("threads").select("owner_id").eq("id", parent_thread_id).execute()
    if not parent_resp.data or parent_resp.data[0]["owner_id"] != user_id:
        raise HTTPException(status_code=404, detail="Parent thread not found")

    # Reconstruct full contexts via Context Reconstructor
    branch_context = await reconstruct_context(request.branch_thread_id)
    parent_context = await reconstruct_context(parent_thread_id)

    # Synthesize via Claude
    try:
        synthesis = await synthesize_merge(parent_context, branch_context)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Merge synthesis failed")

    # Insert merge artifact into the PARENT thread
    try:
        insert_resp = await db.table("messages").insert(
            {
                "thread_id": parent_thread_id,
                "role": "assistant",
                "content": synthesis,
                "is_merge_artifact": True,
                "merge_source_thread_ids": [request.branch_thread_id],
            }
        ).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to save merge artifact")

    artifact = insert_resp.data[0]
    return MergeResponse(message=artifact)
