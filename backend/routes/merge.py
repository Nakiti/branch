from fastapi import APIRouter, Depends, HTTPException

from db import get_db
from models.schemas import MergeRequest, MergeResponse, MultiMergeRequest, MultiMergeResponse
from services.auth import get_current_user
from services.context import reconstruct_context, reconstruct_context_up_to_message
from services.merge import synthesize_merge, synthesize_multi_merge

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


@router.post("/multi-merge", response_model=MultiMergeResponse)
async def multi_merge_branches(
    request: MultiMergeRequest,
    user_id: str = Depends(get_current_user),
) -> MultiMergeResponse:
    if len(request.branch_thread_ids) < 2:
        raise HTTPException(status_code=400, detail="At least two branch thread IDs are required")

    db = await get_db()

    # Fetch and validate each branch thread
    branch_threads: list[dict] = []
    fork_source_ids: list[str] = []
    for tid in request.branch_thread_ids:
        resp = await db.table("threads").select("*").eq("id", tid).execute()
        if not resp.data or resp.data[0]["owner_id"] != user_id:
            raise HTTPException(status_code=404, detail=f"Branch thread not found: {tid}")
        thread = resp.data[0]
        if not thread.get("fork_source_message_id"):
            raise HTTPException(status_code=400, detail=f"Thread {tid} has no fork source — cannot merge a root thread")
        branch_threads.append(thread)
        fork_source_ids.append(thread["fork_source_message_id"])

    # All branches must share the same parent thread
    msg_resp = (
        await db.table("messages")
        .select("id, thread_id")
        .in_("id", fork_source_ids)
        .execute()
    )
    msg_lookup = {m["id"]: m["thread_id"] for m in (msg_resp.data or [])}
    parent_thread_ids = {msg_lookup[fid] for fid in fork_source_ids if fid in msg_lookup}
    if len(parent_thread_ids) != 1:
        raise HTTPException(status_code=400, detail="All branches must share the same parent thread")
    parent_thread_id = parent_thread_ids.pop()

    # Ownership check on parent
    parent_resp = await db.table("threads").select("owner_id").eq("id", parent_thread_id).execute()
    if not parent_resp.data or parent_resp.data[0]["owner_id"] != user_id:
        raise HTTPException(status_code=404, detail="Parent thread not found")

    # Find earliest fork point by message created_at
    fork_msgs_resp = (
        await db.table("messages")
        .select("id, created_at")
        .in_("id", fork_source_ids)
        .execute()
    )
    earliest = min(fork_msgs_resp.data, key=lambda m: m["created_at"])
    earliest_fork_msg_id = earliest["id"]

    # Build parent context up to the earliest fork point
    parent_context = await reconstruct_context_up_to_message(parent_thread_id, earliest_fork_msg_id)

    # Build each branch context with its label
    branches: list[tuple[str, list[dict]]] = []
    for thread in branch_threads:
        label = thread.get("label") or "Branch"
        ctx = await reconstruct_context(thread["id"])
        branches.append((label, ctx))

    # Synthesize
    try:
        synthesis = await synthesize_multi_merge(parent_context, branches)
    except Exception:
        raise HTTPException(status_code=500, detail="Multi-merge synthesis failed")

    # Insert merge artifact into parent thread
    try:
        insert_resp = await db.table("messages").insert(
            {
                "thread_id": parent_thread_id,
                "role": "assistant",
                "content": synthesis,
                "is_merge_artifact": True,
                "merge_source_thread_ids": request.branch_thread_ids,
            }
        ).execute()
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to save merge artifact")

    artifact = insert_resp.data[0]
    return MultiMergeResponse(message=artifact)
