from typing import Optional

from langchain_core.messages import HumanMessage

from src.agents import zeno
from src.api.app import langfuse_handler

print("Starting evaluation...")

# Define parameters based on test_alerts.sh defaults
query = "Find disturbance alerts over Lisbon, Portugal for the year 2023"
user_persona = "researcher"
thread_id = "alerts"

print(f"Query: {query}")
print(f"User Persona: {user_persona}")
print(f"Thread ID: {thread_id}")
print("\nStreaming chat response:")


# Copied over from api.app and truncated irrelevant parts
def stream_chat(
    query: str,
    user_persona: Optional[str] = None,
    thread_id: Optional[str] = None,
):
    config = {
        "configurable": {
            "thread_id": thread_id,
        },
        "callbacks": [langfuse_handler],
    }
    messages = [HumanMessage(content=query)]

    return zeno.stream(
        {
            "messages": messages,
            "user_persona": user_persona,
        },
        config=config,
        stream_mode="updates",
        subgraphs=False,
    )


# Call stream_chat and iterate through the response
# Set metadata, session_id, user_id, and tags to None
for chunk in stream_chat(
    query=query,
    user_persona=user_persona,
    thread_id=thread_id,
):
    print(chunk, end="")

print("\nEvaluation finished.")
