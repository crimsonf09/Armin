from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str = Field(default="New Chat", min_length=1, max_length=120)


class ConversationPatch(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class ConversationOut(BaseModel):
    id: str
    user_id: str
    title: str
    updated_at: datetime
    created_at: datetime


def base_conversation_doc(user_id: str, title: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "user_id": user_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
        "last_message_at": now,
    }
