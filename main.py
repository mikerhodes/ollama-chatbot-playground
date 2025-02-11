from io import StringIO
from textwrap import dedent

import ollama
import streamlit as st

PREFERRED_MODEL = "phi4:latest"

# 
# initialize state
# 

# Message history
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Retrieve the current models from ollama
# Set a preferred model as default if there's none set
models = [model["model"] for model in ollama.list()["models"]]
if "model" not in st.session_state and PREFERRED_MODEL in models:
    st.session_state["model"] = PREFERRED_MODEL

#
# Helpers
#

def clear_chat():
    """Clears the existing chat session"""
    st.session_state["messages"] = []
    st.success('Chat cleared!', icon="✅")

def stream_model_response():
    """Returns a generator that yields chunks of the models respose"""
    stream = ollama.chat(
        model=st.session_state["model"],
        messages=st.session_state["messages"],
        stream=True,
    )
    for chunk in stream:
        yield chunk["message"]["content"]

#
# Start rendering the app
#

with st.sidebar:
    "## Configuration"
    st.selectbox("Choose your model", models, key="model")
    "## Ollama Python Chatbot"
    st.button("New Chat", on_click=clear_chat)
    "## Summarise a file"
    uploaded_file = st.file_uploader("Upload a plain text document")
    # summarise_detail = st.pills("Level of detail", ["Brief", "Detailed"], default="Brief")
    summarise_detailed = st.toggle("Detailed summary")
    summarise_document = st.button("Go")


# Display chat messages from history on app rerun
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


if summarise_document and uploaded_file is not None:
    if summarise_detailed:
        prompt = dedent("""
            1. Analyze the input text and generate 5 essential questions that, when answered, capture the main points and core meaning of the text.
            2. When formulating your questions:
                1. Address the central theme or argument
                2. Identify key supporting ideas
                3. Highlight important facts or evidence
                4. Reveal the author's purpose or perspective
                5. Explore any significant implications or conclusions.
            3. Answer all of your generated questions one-by-one in detail.\n\n""")
    else:
        prompt = "Condense the content into a bullet point summary, emphasizing the main conclusion and its immediate importance. Use a maximum of four bullet points."
    
    stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
    string_data = stringio.read()
    user_query = {
        "role": "user",
        "content": prompt + string_data,
    }
    with st.chat_message("user"):

        summarisation_request = f"Requested summarisation of `{uploaded_file.name}` using the following prompt:\n\n {prompt}"
        st.markdown(summarisation_request)
        st.session_state["messages"].append({"role": "user", "content": summarisation_request})

    with st.chat_message("assistant"):

        def stream_summary_response(file_data):
            stream = ollama.chat(
                model=st.session_state["model"],
                messages=[
                        user_query
                ],
                stream=True,
            )
            for chunk in stream:
                yield chunk["message"]["content"]

        with st.spinner("Thinking...", show_time=False):
            message = st.write_stream(stream_summary_response(string_data))
        st.session_state["messages"].append({"role": "assistant", "content": message})

if prompt := st.chat_input("Enter prompt here..."):
    # add latest message to history in format {role, content}
    st.session_state["messages"].append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking...", show_time=False):
            message = st.write_stream(stream_model_response())
        st.session_state["messages"].append({"role": "assistant", "content": message})
