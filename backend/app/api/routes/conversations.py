from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import db_dependency, get_current_user_id
from app.db.models.conversation import ConversationCreate, ConversationPatch
from app.db.models.message import MessageCreate
from app.services.chat_service import (
    create_conversation,
    create_user_message,
    list_conversations,
    list_messages,
    rename_conversation,
    run_assistant_reply,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("")
async def get_conversations(
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(db_dependency),
) -> list[dict]:
    return await list_conversations(db, user_id)


@router.post("")
async def post_conversation(
    payload: ConversationCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(db_dependency),
) -> dict:
    return await create_conversation(db, user_id, payload.title)


@router.patch("/{conversation_id}")
async def patch_conversation(
    conversation_id: str,
    payload: ConversationPatch,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(db_dependency),
) -> dict:
    return await rename_conversation(db, user_id, conversation_id, payload.title)


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(db_dependency),
) -> list[dict]:
    return await list_messages(db, user_id, conversation_id, limit, skip)


@router.post("/{conversation_id}/messages")
async def post_message(
    conversation_id: str,
    payload: MessageCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(db_dependency),
) -> dict:
    user_msg = await create_user_message(db, user_id, conversation_id, payload.content)
    assistant_msg = await run_assistant_reply(db, user_id, conversation_id, payload.content)
    return {"user_message": user_msg, "assistant_message": assistant_msg}
