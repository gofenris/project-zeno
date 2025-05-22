from src.api.app import stream_chat

print("Starting evaluation...")

# Define parameters based on test_alerts.sh defaults
query = "Find disturbance alerts over Lisbon, Portugal for the year 2023"
user_persona = "researcher"
thread_id = "alerts"

print(f"Query: {query}")
print(f"User Persona: {user_persona}")
print(f"Thread ID: {thread_id}")
print("\nStreaming chat response:")

# Call stream_chat and iterate through the response
# Set metadata, session_id, user_id, and tags to None
for chunk in stream_chat(
    query=query,
    user_persona=user_persona,
    thread_id=thread_id,
    metadata=None,
    session_id=None,
    user_id=None,
    tags=None,
):
    print(chunk, end="")

print("\nEvaluation finished.")
