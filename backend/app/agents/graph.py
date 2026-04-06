from app.agents.nodes.planner import planner_node
from app.agents.nodes.responder import response_node
from app.agents.nodes.safety import safety_node


async def run_multi_agent(user_message: str) -> tuple[str, list[str]]:
    trace: list[str] = []
    plan = await planner_node(user_message)
    trace.append(f"planner: {plan[:120]}")
    draft = await response_node(user_message, plan)
    trace.append("response: generated")
    safe = await safety_node(draft)
    trace.append("safety: checked")
    return safe, trace
