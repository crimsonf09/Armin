from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import create_access_token, hash_password, verify_password
from app.db.models.user import UserCreate, UserLogin, base_user_doc


async def register_user(db: AsyncIOMotorDatabase, payload: UserCreate) -> dict:
    users = db["users"]
    existing = await users.find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
    doc = base_user_doc(payload.email, hash_password(payload.password))
    result = await users.insert_one(doc)
    return {"access_token": create_access_token(str(result.inserted_id))}


async def login_user(db: AsyncIOMotorDatabase, payload: UserLogin) -> dict:
    users = db["users"]
    user = await users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {"access_token": create_access_token(str(user["_id"]))}


async def get_user_profile(db: AsyncIOMotorDatabase, user_id: str) -> dict:
    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"id": str(user["_id"]), "email": user["email"], "created_at": user["created_at"]}
