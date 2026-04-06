from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

client: AsyncIOMotorClient | None = None


async def connect_mongo() -> None:
    global client
    client = AsyncIOMotorClient(settings.mongodb_uri)


async def disconnect_mongo() -> None:
    global client
    if client:
        client.close()
    client = None


def get_db() -> AsyncIOMotorDatabase:
    if client is None:
        raise RuntimeError("MongoDB client is not connected")
    return client[settings.mongodb_db]
