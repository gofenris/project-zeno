"""Investigator Tree Cover Evaluation Script"""

import json
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


def parse_output_trace(json_str: str) -> Optional[dict]:
    """
    Parse the output trace to extract messages content.
    Mimics: jq 'walk(if type == "object" then del(.artifact) else . end)' json_str | 
            jq '{messages: .messages | map({type, content} + (if .tool_calls then {tool_calls: .tool_calls | map({name, args})} else {} end))}'
    """
    try:
        data = json.loads(json_str)
        
        # Extract messages if they exist
        if not isinstance(data, dict) or 'messages' not in data:
            return None
            
        messages = data.get('messages', [])
        
        # Process messages to keep only type, content, and simplified tool_calls
        processed_messages = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue
                
            processed_msg = {
                'type': msg.get('type'),
                'content': msg.get('content')
            }
            
            # Add tool_calls if they exist
            if 'tool_calls' in msg and msg['tool_calls']:
                processed_msg['tool_calls'] = [
                    {'name': tc.get('name'), 'args': tc.get('args')}
                    for tc in msg['tool_calls']
                    if isinstance(tc, dict)
                ]
            
            processed_messages.append(processed_msg)
        
        # Return the distilled JSON structure
        return {'messages': processed_messages}
        
    except (json.JSONDecodeError, KeyError, TypeError):
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
    actual = parse_output_trace(response)
    score = score_answer(actual, item.expected_output)

    # Upload
    # langfuse.score(
    #     trace_id=handler.get_trace_id(),
    #     name="tree_cover_answer_score",
    #     value=score,
    #     comment=f"Expected: {item.expected_output}\nActual: {actual}",
    # )
    langfuse.flush()

    print(f"✓ {item.input} -> {score}")
