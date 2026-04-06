from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

MessageRole = Literal["user", "assistant", "system"]


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    user_id: str
    role: MessageRole
    content: str
    created_at: datetime
    agent_trace: list[str] = Field(default_factory=list)


def base_message_doc(conversation_id: str, user_id: str, role: MessageRole, content: str, agent_trace: list[str] | None = None) -> dict:
    return {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "role": role,
        "content": content,
        "agent_trace": agent_trace or [],
        "created_at": datetime.now(timezone.utc),
    }
