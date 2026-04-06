from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.routes.auth import router as auth_router
from app.api.routes.conversations import router as conversation_router
from app.core.config import settings
from app.db.mongo import connect_mongo, disconnect_mongo, get_db
from app.services.chat_service import ensure_indexes
from app.sockets.handlers import sio

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await connect_mongo()
    await ensure_indexes(get_db())
    yield
    await disconnect_mongo()


api = FastAPI(title=settings.app_name, lifespan=lifespan)
api.state.limiter = limiter
api.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
api.include_router(auth_router, prefix=settings.api_prefix)
api.include_router(conversation_router, prefix=settings.api_prefix)


@api.get("/health")
async def health() -> dict:
    return {"status": "ok"}


app = socketio.ASGIApp(sio, other_asgi_app=api)
