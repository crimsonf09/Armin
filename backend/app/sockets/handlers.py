import socketio

from app.core.security import decode_access_token
from app.db.mongo import get_db
from app.services.chat_service import create_user_message, get_conversation_or_404, run_assistant_reply

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")


@sio.event
async def connect(sid: str, environ: dict, auth: dict | None) -> bool:
    token = (auth or {}).get("token")
    user_id = decode_access_token(token) if token else None
    if not user_id:
        return False
    await sio.save_session(sid, {"user_id": user_id})
    return True


@sio.on("conversation.join")
async def conversation_join(sid: str, data: dict) -> None:
    session = await sio.get_session(sid)
    user_id = session["user_id"]
    conversation_id = data["conversation_id"]
    db = get_db()
    await get_conversation_or_404(db, user_id, conversation_id)
    await sio.enter_room(sid, f"conversation:{conversation_id}")


@sio.on("message.send")
async def message_send(sid: str, data: dict) -> None:
    session = await sio.get_session(sid)
    user_id = session["user_id"]
    conversation_id = data["conversation_id"]
    content = data["content"]
    db = get_db()

    user_message = await create_user_message(db, user_id, conversation_id, content)
    await sio.emit("message.created", user_message, room=f"conversation:{conversation_id}")
    await sio.emit("agent.step", {"conversation_id": conversation_id, "step": "planning"}, room=sid)

    assistant_message = await run_assistant_reply(db, user_id, conversation_id, content)
    await sio.emit("agent.final", assistant_message, room=f"conversation:{conversation_id}")
    await sio.emit("conversation.updated", {"conversation_id": conversation_id}, room=f"conversation:{conversation_id}")
