from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings


async def response_node(user_message: str, plan: str) -> str:
    llm = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, temperature=0.4)
    result = await llm.ainvoke(
        [
            SystemMessage(content="You are a helpful chatbot. Follow the provided plan and answer clearly."),
            HumanMessage(content=f"Plan:\n{plan}\n\nUser:\n{user_message}"),
        ]
    )
    return result.content if isinstance(result.content, str) else str(result.content)
