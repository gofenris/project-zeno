import json
from dataclasses import dataclass
from typing import Optional
from langchain_anthropic import ChatAnthropic

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


def parse_output_trace(json_str: str) -> dict:
    """
    Parse the output trace to extract messages content.
    Mimics: jq 'walk(if type == "object" then del(.artifact) else . end)' json_str |
            jq '{messages: .messages | map({type, content} + (if .tool_calls then {tool_calls: .tool_calls | map({name, args})} else {} end))}'
    """
    data = json.loads(json_str)

    # Collect all messages from the nested structure
    messages = []
    for item in data:
        # Get messages from whichever key exists (tools or agent)
        node = item.get("tools", item.get("agent", {}))
        for message in node.get("messages", []):
            msg_data = message.get("kwargs", message)

            processed_msg = {
                "type": msg_data.get("type"),
                "content": msg_data.get("content"),
                "name": msg_data.get("name"),
            }

            # Add tool_calls if present
            if "tool_calls" in msg_data:
                processed_msg["tool_calls"] = [
                    {"name": tc["name"], "args": tc["args"]}
                    for tc in msg_data["tool_calls"]
                ]

            messages.append(processed_msg)

    return {"messages": messages}


# Scoring
def score_answer(trace: dict, user_query: str, golden_answer: dict) -> float:
    """Score answer matches.

    TODO: Implement actual scoring logic
    """

    prompt = """Analyze the provided agentic system trace against the user query and golden answer.
    Determine if the system responded reasonably well to the query with respect to the expected
    answer. Be lenient in your assessment.
    Inputs:

    - <Trace>: System execution log showing tool calls and responses
    - <Query>: User's question
    - <Golden Answer>: Expected answer

    Evaluate whether the system:
    1. Made meaningful progress toward answering the query
    2. Retrieved relevant data or information
    3. Provided or approached the correct answer
    4. Handled errors reasonably

    Respond with a JSON containing:
    - "pass/fail": "pass" if the system adequately addressed the query (even partially), "fail" if it did not
    - "analysis": Brief explanation of your assessment, including what worked, what failed, and whether the golden answer was reached or approached
    """

    # Placeholder - return 0.0 for now
    return 0.0


# Main execution
langfuse = get_langfuse()
run_name = get_run_name()
dataset = langfuse.get_dataset("s5_t2_02_investigator")
chat_model = ChatAnthropic(
    model="claude-opus-4-20250514",
    max_tokens=20000,
    thinking={"type": "enabled", "budget_tokens": 10000},
)

print(f"Evaluating {len(dataset.items)} items...")

for item in dataset.items:
    if item.status != "ACTIVE":
        continue

    # Execute
    handler = item.get_langchain_handler(run_name=run_name)
    response = run_query(item.input, handler, "researcher", item.id)

    # Score
    actual = parse_output_trace(response)
    score = score_answer(actual, item.expected_output)

    # Upload
    langfuse.score(
        trace_id=handler.get_trace_id(),
        name="tree_cover_answer_score",
        value=score,
        comment=f"Actual: {actual}",
    )
    langfuse.flush()

    print(f"✓ {item.input} -> {score}")
