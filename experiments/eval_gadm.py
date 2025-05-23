import json
import os
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
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


# I don't know what this does. So just copied over from test_alerts.sh defaults
USER_PERSONA = "researcher"


def get_git_short_hash() -> str:
    """Get the short git hash of the current commit."""
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
            .decode("ascii")
            .strip()
        )
    except Exception:
        return "nogit"


# Langfuse Configuration
DATASET_NAME = "gadm_location"
# Generate a human-readable run name with timestamp and git short hash
current_date_str = datetime.now().strftime("%Y%m%d")
git_short_hash = get_git_short_hash()
RUN_NAME = f"eval_{current_date_str}_{git_short_hash}"


print(f"Starting evaluation [run name: {RUN_NAME}] ...")


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

    return list(
        zeno.stream(
            {
                "messages": messages,
                "user_persona": user_persona,
            },
            config=config,
            stream_mode="updates",
            subgraphs=False,
        )
    )


# TODO: Refactor to process LangGraph object output from `stream_chat` instead of a JSON string.
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


def parse_expected_output(json_str: str) -> List[GadmLocation]:
    # example input json string (array of objects):
    # [
    #   { "name": "Brazil", "gadm_id": "BRA", "gadm_level": 0 },
    #   { "name": "Amazonas", "gadm_id": "BRA.3_1", "gadm_level": 1 }
    # ]
    # Assumes json_str is always a string representing a JSON array of GADM location objects.
    data_list = json.loads(json_str)
    results: List[GadmLocation] = []

    for item in data_list:
        location = GadmLocation(
            name=item.get("name"),
            gadm_id=item.get("gadm_id"),
            gadm_level=item.get("gadm_level"),
            admin_level=item.get("admin_level"),
        )
        results.append(location)
    return results


def score_gadm_matches(
    actual: List[GadmLocation], expected: List[GadmLocation]
) -> float:
    """Compare name and gadm_id of each actual and see if they match."""
    # Case 1: Both lists are empty.
    # This is considered a perfect match (or vacuously true).
    if not actual and not expected:
        return 1.0

    # Case 2: One list is empty, but the other is not.
    # This means either:
    #   - Nothing was expected, but something was returned (false positives).
    #   - Something was expected, but nothing was returned (false negatives).
    # In either scenario, the score is 0.0.
    if not actual or not expected:
        return 0.0

    # At this point, both `actual` and `expected` lists are non-empty.

    # Create lists of (name, gadm_id) tuples for comparison
    actual_tuples = [(loc.name, loc.gadm_id) for loc in actual]
    expected_tuples = [(loc.name, loc.gadm_id) for loc in expected]

    actual_counts = Counter(actual_tuples)
    expected_counts = Counter(expected_tuples)

    # Calculate the intersection of the two multisets
    # The '&' operator for Counters results in a new Counter where counts are min(count_in_actual, count_in_expected)
    intersection_counts = actual_counts & expected_counts

    # Sum of counts in the intersection gives the total number of matches
    matches = sum(intersection_counts.values())

    # The denominator is the length of the longer list, to penalize both false positives and false negatives.
    denominator = max(len(actual), len(expected))

    # Denominator will be > 0 here because empty list cases are handled above.
    return float(matches) / denominator


langfuse = Langfuse(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    host=os.getenv("LANGFUSE_HOST"),
)

dataset = langfuse.get_dataset(DATASET_NAME)
# Filter for active items
active_dataset_items = [
    item for item in dataset.items if item.status == "ACTIVE"
]
print(
    f"Fetched dataset {DATASET_NAME}. Processing {len(active_dataset_items)} active items."
)


actual_outputs = []
for item in active_dataset_items:
    print(f"Evaluating item: input=[{item.input}]")
    handler = item.get_langchain_handler(run_name=RUN_NAME)
    actual_output = stream_chat(
        query=item.input,
        user_persona=USER_PERSONA,
        thread_id=item.id,
        langfuse_handler=handler,
    )
    actual_outputs.append(actual_output)
    langfuse.score(trace_id=handler.get_trace_id(), name="fake_score", value=1)
