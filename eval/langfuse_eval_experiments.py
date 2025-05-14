"""
This is not working code. 

langfuse_eval_experiments.py
* calls evaluation functions to run experiments

TODO: 
* single_query_run() as written right now must return the full agent trace as a parsed JSON dict.
* load_dotenv() loads credentials from .env.
* implement single_query_run_trace() 

"""
import os
from dotenv import load_dotenv

from langfuse import Langfuse
# no longer used from langfuse.callback import CallbackHandler

from zeno.agents import single_query_run
from eval_location_gadm import eval_location_gadm

def run_experiment_gadm(experiment_name):
    load_dotenv()

    langfuse = Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=os.environ["LANGFUSE_HOST"],
    )

    # TODO: provide the right name of the dataset, or enable UI to select a dataset. 
    ds = langfuse.get_dataset("location-gadm-data-test-01")

    for idx, item in enumerate(ds.items):
        try:
            handler = item.get_langchain_handler(run_name=experiment_name)

            # Run the agent and get full trace output
            trace_output = single_query_run_trace(item.input, handler)

            # Evaluate trace output against expected result
            eval_score = eval_location_gadm(trace_output, item.expected_output)

            # Log score in Langfuse
            handler.trace.score(
                trace_id=handler.get_trace_id(),
                name="gadm_exact_match_score",
                value=eval_score,
            )
        except Exception as e:
            print(f"Error on item {idx}: {e}")
            continue

    langfuse.flush()

def single_query_run_trace(input, langfuse_handler):
    """Run the location agent and return the full trace output for evaluation.

    returns final_state as a dict, expected by eval_location_gadm()
    """
    location_agent = create_location_agent()

    agent_inputs = {"messages": [("user", input)]}
    agent_config = {
        "configurable": {"thread_id": str(uuid4())},
        "callbacks": [langfuse_handler],
    }

    # Run the agent to completion and return the full trace
    final_state = location_agent.get_state(agent_config)

    return final_state  # <-- this is a dict, expected by eval_location_gadm


if __name__ == "__main__":
    run_experiment_gadm("gadm-match-eval")

