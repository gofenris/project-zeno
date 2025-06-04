"""Investigator Tree Cover Evaluation Script"""

from dataclasses import dataclass
from typing import Optional

from experiments.eval_utils import get_langfuse, get_run_name, run_query


# Data structures
@dataclass
class InvestigatorAnswer:
    answer: str
    notes: Optional[str] = None


# Parsing utilities
def parse_expected_output(data: dict) -> InvestigatorAnswer:
    """Convert dict to InvestigatorAnswer object."""
    return InvestigatorAnswer(
        answer=data.get("answer", ""), notes=data.get("notes")
    )


def parse_answer_from_json(json_str: str) -> Optional[InvestigatorAnswer]:
    """Extracts answer from Langgraph json output.

    TODO: Implement actual parsing logic based on agent response format
    """
    # Placeholder - return None for now
    return None


# Scoring
def score_answer(
    actual: Optional[InvestigatorAnswer], expected: dict
) -> float:
    """Score answer matches.

    TODO: Implement actual scoring logic
    """
    # Placeholder - return 0.0 for now
    return 0.0


# Main execution
langfuse = get_langfuse()
run_name = get_run_name()
dataset = langfuse.get_dataset("s5_t2_02_investigator")

print(f"Evaluating {len(dataset.items)} items...")

for item in dataset.items:
    if item.status != "ACTIVE":
        continue

    # Execute
    handler = item.get_langchain_handler(run_name=run_name)
    response = run_query(item.input, handler, "researcher", item.id)

    # Score
    actual = parse_answer_from_json(response)
    score = score_answer(actual, item.expected_output)

    # Upload
    langfuse.score(
        trace_id=handler.get_trace_id(),
        name="tree_cover_answer_score",
        value=score,
        comment=f"Expected: {item.expected_output}\nActual: {actual}",
    )
    langfuse.flush()

    print(f"✓ {item.input} -> {score}")
