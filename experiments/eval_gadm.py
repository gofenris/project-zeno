import os
from typing import Optional

from langchain_core.messages import HumanMessage
from langfuse import Langfuse
from langfuse.callback import CallbackHandler

from src.agents import zeno

print("Starting evaluation...")

# Define parameters based on test_alerts.sh defaults
USER_PERSONA = "researcher"
ZENO_THREAD_ID = "alerts"

# Langfuse Configuration
DATASET_NAME = "gadm_location"
RUN_NAME = "dev_test_002"


# Copied over from api.app and truncated irrelevant parts
def stream_chat(
    query: str,
    langfuse_handler: CallbackHandler,
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


langfuse = Langfuse(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    host=os.getenv("LANGFUSE_HOST"),
)

dataset = langfuse.get_dataset(DATASET_NAME)
print(f"Fetched dataset {DATASET_NAME} with {len(dataset.items)} items")


for item in dataset.items:
    print(f"Evaluating item: input=[{item.input}]")
    handler = item.get_langchain_handler(run_name=RUN_NAME)
    for chunk in stream_chat(
        query=item.input,
        user_persona=USER_PERSONA,
        thread_id=ZENO_THREAD_ID,
        langfuse_handler=handler,
    ):
        print(chunk, end="")
