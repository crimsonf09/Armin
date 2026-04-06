from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.agents.graph import run_multi_agent
from app.db.models.conversation import base_conversation_doc
from app.db.models.message import base_message_doc


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db["conversations"].create_index([("user_id", 1), ("updated_at", -1)])
    await db["messages"].create_index([("conversation_id", 1), ("created_at", 1)])


async def list_conversations(db: AsyncIOMotorDatabase, user_id: str) -> list[dict]:
    cursor = db["conversations"].find({"user_id": user_id}).sort("updated_at", -1)
    docs = await cursor.to_list(length=200)
    return [
        {
            "id": str(doc["_id"]),
            "user_id": doc["user_id"],
            "title": doc["title"],
            "updated_at": doc["updated_at"],
            "created_at": doc["created_at"],
        }
        for doc in docs
    ]


async def create_conversation(db: AsyncIOMotorDatabase, user_id: str, title: str) -> dict:
    doc = base_conversation_doc(user_id, title)
    result = await db["conversations"].insert_one(doc)
    return {
        "id": str(result.inserted_id),
        "user_id": user_id,
        "title": title,
        "updated_at": doc["updated_at"],
        "created_at": doc["created_at"],
    }


async def rename_conversation(db: AsyncIOMotorDatabase, user_id: str, conversation_id: str, title: str) -> dict:
    convo = await get_conversation_or_404(db, user_id, conversation_id)
    await db["conversations"].update_one(
        {"_id": convo["_id"]},
        {"$set": {"title": title, "updated_at": datetime.now(timezone.utc)}},
    )
    convo["title"] = title
    return {
        "id": str(convo["_id"]),
        "user_id": convo["user_id"],
        "title": title,
        "updated_at": convo["updated_at"],
        "created_at": convo["created_at"],
    }


async def get_conversation_or_404(db: AsyncIOMotorDatabase, user_id: str, conversation_id: str) -> dict:
    convo = await db["conversations"].find_one({"_id": ObjectId(conversation_id), "user_id": user_id})
    if not convo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return convo


async def list_messages(db: AsyncIOMotorDatabase, user_id: str, conversation_id: str, limit: int = 50, skip: int = 0) -> list[dict]:
    await get_conversation_or_404(db, user_id, conversation_id)
    cursor = db["messages"].find({"conversation_id": conversation_id}).sort("created_at", 1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [
        {
            "id": str(doc["_id"]),
            "conversation_id": doc["conversation_id"],
            "user_id": doc["user_id"],
            "role": doc["role"],
            "content": doc["content"],
            "created_at": doc["created_at"],
            "agent_trace": doc.get("agent_trace", []),
        }
        for doc in docs
    ]


async def create_user_message(db: AsyncIOMotorDatabase, user_id: str, conversation_id: str, content: str) -> dict:
    await get_conversation_or_404(db, user_id, conversation_id)
    doc = base_message_doc(conversation_id, user_id, "user", content)
    result = await db["messages"].insert_one(doc)
    await db["conversations"].update_one(
        {"_id": ObjectId(conversation_id)},
        {"$set": {"updated_at": datetime.now(timezone.utc), "last_message_at": datetime.now(timezone.utc)}},
    )
    return {
        "id": str(result.inserted_id),
        "conversation_id": conversation_id,
        "user_id": user_id,
        "role": "user",
        "content": content,
        "created_at": doc["created_at"],
        "agent_trace": [],
    }


async def run_assistant_reply(db: AsyncIOMotorDatabase, user_id: str, conversation_id: str, content: str) -> dict:
    reply, trace = await run_multi_agent(content)
    doc = base_message_doc(conversation_id, user_id, "assistant", reply, trace)
    result = await db["messages"].insert_one(doc)
    await db["conversations"].update_one(
        {"_id": ObjectId(conversation_id)},
        {"$set": {"updated_at": datetime.now(timezone.utc), "last_message_at": datetime.now(timezone.utc)}},
    )
    return {
        "id": str(result.inserted_id),
        "conversation_id": conversation_id,
        "user_id": user_id,
        "role": "assistant",
        "content": reply,
        "created_at": doc["created_at"],
        "agent_trace": trace,
    }
