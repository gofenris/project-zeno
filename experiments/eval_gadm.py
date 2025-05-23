import json
import os
from dataclasses import dataclass
from typing import List, Optional

from langchain_core.messages import HumanMessage
from langfuse import Langfuse
from langfuse.callback import CallbackHandler

from src.agents import zeno


@dataclass
class GadmLocation:
    name: str
    gadm_id: str
    gadm_level: Optional[int] = None
    admin_level: Optional[int] = None


print("Starting evaluation...")

# I don't know what this does. So just copied over from test_alerts.sh defaults
USER_PERSONA = "researcher"

# Langfuse Configuration
DATASET_NAME = "gadm_location"
RUN_NAME = "dev_test_003"


# Copied over from api.app because I don't want to mess with Devseed code. It'd be easier if we just
# refactor the parent method.
# TODO: perhaps add a langfuse_handler argument to api.app.stream_chat so we don't need to dup this
# here
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


def parse_gadm_from_json(json_str: str) -> List[GadmLocation]:
    """Extracts GADM location data from agent JSON output.

    Filters for "location-tool" messages and extracts GADM details
    (name, ID, level, admin_level) from their artifact properties.
    Equivalent to jq: '.messages[] | select(.type=="tool" and .name=="location-tool") | .artifact[].properties | {name, gadm_id, gadm_level, admin_level}'

    Args:
        json_str: The JSON string output from the agent.

    Returns:
        A list of GadmLocation objects.
    """

    data = json.loads(json_str)
    results: List[GadmLocation] = []
    for message in data.get("messages", []):
        if (
            message.get("type") == "tool"
            and message.get("name") == "location-tool"
        ):
            for artifact_item in message.get("artifact", []):
                properties = artifact_item.get("properties", {})
                location_info = GadmLocation(
                    name=properties.get("name"),
                    gadm_id=properties.get("gadm_id"),
                    gadm_level=properties.get("gadm_level"),
                    admin_level=properties.get("admin_level"),
                )
                results.append(location_info)
    return results


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
    list(
        stream_chat(
            query=item.input,
            user_persona=USER_PERSONA,
            thread_id=item.id,
            langfuse_handler=handler,
        )
    )
