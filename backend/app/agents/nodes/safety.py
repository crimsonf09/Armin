async def safety_node(text: str) -> str:
    blocked = ["password", "credit card", "ssn"]
    lower = text.lower()
    if any(word in lower for word in blocked):
        return "Please avoid sharing sensitive information."
    return text
