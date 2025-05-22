"""
Evaluation Code for GADM location evaluation
https://github.com/wri/project-zeno/issues/170

See: Evaluation Code for GADM location evaluation.

Functions:
- parse_JSON_trace_for_location_data(trace_json): Recursively extract GADM locations from agent output trace.
- score_single_location(location, expected_location): Returns 1.0 if gadm_id and gadm_level match exactly; else 0.0.
- eval_location_gadm(output_trace, expected_location): Extracts candidate locations and returns the highest match score.

---
usage: 

```
# example expected_output
expected_output = {
    "location_name": "Tehama",
    "gadm_id": "USA.5.52_1",
    "gadm_level": 2
}

# example trace
import json
with open("example_trace_full.json", "r") as f:
    example_json_trace_full = json.load(f)

# get evaluation score
output = example_json_trace_full
score = eval_location_gadm(output, expected_output)

print("Eval score:", score)
```
"""
import json 

def eval_location_gadm(output_trace, expected_location):
    """Evaluate the trace output against the expected location.

    Args:
    output_trace (str): A parsed JSON dict object containing the agent's full output trace.
    expected_location (dict): Dict with keys: location_name, gadm_id, gadm_level.

    Returns:
    float: highest score from locations provided in the trace. 
    """
    # TODO: error handling for output_trace

    candidate_locations = parse_JSON_trace_for_location_data(output_trace)

    if not candidate_locations:
        return 0.0

    scores = [
        score_single_location(loc, expected_location)
        for loc in candidate_locations
    ]

    return max(scores)

def score_single_location(location, expected_location): 
    """Score a single location dict against the expected location.

    Args:
        location (dict): A dict with keys location_name, gadm_id, gadm_level.
        expected_location (dict): Dict with same keys.

    example_location = {"location_name: "Maine-et-Loire", "gadm_id": "FRA.12.2_1", "gadm_level": 2}

    Computes a score
        1 if the GADM_ID is an exact match, and the gadm_level is an exact match. 
        0 otherwise. 
    The location_name is not used to compute the score. 

    Returns:
        float: A similarity score between 0 and 1. 
    """

    try:
        if (
            location["gadm_id"] == expected_location["gadm_id"] and
            location["gadm_level"] == expected_location["gadm_level"]
        ):
            score = 1.0
        else:
            score = 0.0
    except KeyError as e:
        print(f"Missing expected key: {e}")
        return False

    return score


def parse_JSON_trace_for_location_data(trace_json):
    """Recursively search the trace JSON for tool-type entries and extract location data.

    Args:
        trace_json (dict or list): The JSON trace returned by the agent.

    Returns:
        List[dict]: A list of location dictionaries with name, GADM ID, and level.
    """
    extracted_locations = []

    def recurse(node):
        if isinstance(node, dict):
            if (
                node.get("type") == "tool"
                and node.get("name") == "location-tool"
                and node.get("status") == "success"
                and isinstance(node.get("content"), list)
            ):
                for item in node["content"]:
                    if (
                        isinstance(item, list)
                        and len(item) == 3
                        and isinstance(item[0], str)
                        and isinstance(item[1], str)
                        and isinstance(item[2], int)
                    ):
                        extracted_locations.append({
                            "location_name": item[0],
                            "gadm_id": item[1],
                            "gadm_level": item[2],
                        })
            for value in node.values():
                recurse(value)
        elif isinstance(node, list):
            for item in node:
                recurse(item)

    recurse(trace_json)
    return extracted_locations


