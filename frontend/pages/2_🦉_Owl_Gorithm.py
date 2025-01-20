import json
import os
import uuid

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.environ.get("API_BASE_URL")

if "layerfinder_session_id" not in st.session_state:
    st.session_state.layerfinder_session_id = str(uuid.uuid4())
if "layerfinder_messages" not in st.session_state:
    st.session_state.layerfinder_messages = []

st.header("Owl Gorithm 🦉")
st.caption(
    "Zeno's Owl Gorithm is a wise, data-savvy agent for discovering relevant datasets."
)

with st.sidebar:
    st.header("🦉")
    st.write(
        """
    Owl Gorithm is expert at finding relevant datasets hosted by WRI & LCL. It tries its best to find the dataset & explain why it is relevant to your query. Give it a try!
    """
    )

    st.subheader("🧐 Try asking:")
    st.write(
        """
        - My interest is in understanding tree cover loss, what datasets are available?
        - Suggest datasets to understand deforestation in Brazil
        - What should I look at to better estimate above ground biomass in the Amazon?
    """
    )


def display_message(message):
    if message["role"] == "user":
        st.chat_message("user").write(message["content"])
    else:
        st.chat_message("assistant").write(message["content"])


def handle_stream_response(stream):
    for chunk in stream.iter_lines():
        data = json.loads(chunk.decode("utf-8"))
        message = {
            "role": "assistant",
            "type": "text",
            "content": data["content"],
        }
        st.session_state.layerfinder_messages.append(message)
        display_message(message)


# Display chat history
for message in st.session_state.layerfinder_messages:
    display_message(message)

if user_input := st.chat_input("Type your message here..."):
    message = {"role": "user", "content": user_input, "type": "text"}
    st.session_state.layerfinder_messages.append(message)
    display_message(message)

    with requests.post(
        f"{API_BASE_URL}/stream/layerfinder",
        json={
            "query": user_input,
            "thread_id": st.session_state.layerfinder_session_id,
        },
        stream=True,
    ) as stream:
        handle_stream_response(stream)
