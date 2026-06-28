from app.services.llm_service import generate_reply


async def run_multi_agent(user_message: str) -> tuple[str, list[str]]:
    reply = await generate_reply(user_message)
    return reply, ["llm: direct"]
