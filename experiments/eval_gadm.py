"""GADM Location Evaluation Script"""

from collections import Counter

from experiments.eval_utils import get_langfuse, get_run_name, run_query
from experiments.gadm_utils import parse_expected_output, parse_gadm_from_json


def score_gadm(actual, expected):
    """Score GADM matches."""
    expected = parse_expected_output(expected)

    if not actual and not expected:
        return 1.0
    if not actual or not expected:
        return 0.0

    matches = sum((Counter(actual) & Counter(expected)).values())
    return matches / max(len(actual), len(expected))


# Run evaluation
langfuse = get_langfuse()
run_name = get_run_name()
dataset = langfuse.get_dataset("gadm_location")

print(f"Evaluating {len(dataset.items)} items...")

for item in dataset.items:
    if item.status != "ACTIVE":
        continue

    # Execute
    handler = item.get_langchain_handler(run_name=run_name)
    response = run_query(item.input, handler, "researcher", item.id)

    # Score
    actual = parse_gadm_from_json(response)
    score = score_gadm(actual, item.expected_output)

    # Upload
    langfuse.score(
        trace_id=handler.get_trace_id(),
        name="gadm_matches_score",
        value=score,
        comment=f"Expected: {item.expected_output}\nActual: {actual}",
    )
    langfuse.flush()

    print(f"✓ {item.input} -> {score}")
