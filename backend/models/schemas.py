from pydantic import BaseModel
from typing import Optional
import datetime


class Thread(BaseModel):
    id: str
    owner_id: str
    label: Optional[str] = None
    fork_source_message_id: Optional[str] = None
    created_at: Optional[datetime.datetime] = None


class Message(BaseModel):
    id: str
    thread_id: str
    role: str
    content: str
    is_merge_artifact: bool = False
    merge_source_thread_ids: Optional[list[str]] = None
    created_at: Optional[datetime.datetime] = None


class SendMessageRequest(BaseModel):
    thread_id: str
    content: str


class ForkRequest(BaseModel):
    message_id: str


class ForkResponse(BaseModel):
    thread_id: str


class MergeRequest(BaseModel):
    branch_thread_id: str


class MergeResponse(BaseModel):
    message: dict


class TreeNode(BaseModel):
    thread: Thread
    fork_message_id: Optional[str] = None
    children: list["TreeNode"] = []


TreeNode.model_rebuild()
