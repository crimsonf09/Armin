from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings


async def planner_node(user_message: str) -> str:
    llm = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, temperature=0.2)
    result = await llm.ainvoke(
        [
            SystemMessage(content="You are a planning agent. Return a short plan to answer the user safely."),
            HumanMessage(content=user_message),
        ]
    )
    return result.content if isinstance(result.content, str) else str(result.content)
