from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import db_dependency, get_current_user_id
from app.db.models.user import UserCreate, UserLogin
from app.services.auth_service import get_user_profile, login_user, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(payload: UserCreate, db: AsyncIOMotorDatabase = Depends(db_dependency)) -> dict:
    return await register_user(db, payload)


@router.post("/login")
async def login(payload: UserLogin, db: AsyncIOMotorDatabase = Depends(db_dependency)) -> dict:
    return await login_user(db, payload)


@router.get("/me")
async def me(
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(db_dependency),
) -> dict:
    return await get_user_profile(db, user_id)
