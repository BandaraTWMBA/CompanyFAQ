import requests
import streamlit as st


st.title("🤖 Company FAQ Chatbot")

st.write(
    "Ask questions about the company. "
    "The chatbot remembers previous messages in this conversation."
)


# Initialize frontend chat history
if "messages" not in st.session_state:
    st.session_state.messages = []


# Display previous messages
for message in st.session_state.messages:

    if message["role"] == "user":

        with st.chat_message("user"):
            st.write(message["content"])

    else:

        with st.chat_message("assistant"):
            st.write(message["content"])



# Chat input box
question = st.chat_input(
    "Ask anything..."
)


if question:

    # Display user message immediately
    with st.chat_message("user"):
        st.write(question)


    # Save user message
    st.session_state.messages.append(
        {
            "role": "user",
            "content": question
        }
    )


    # Send request to backend
    response = requests.post(

        "http://127.0.0.1:8000/chat",

        json={
            "question": question
        }

    )


    if response.status_code == 200:

        answer = response.json()["answer"]


        # Display assistant response
        with st.chat_message("assistant"):

            st.write(answer)


        # Save assistant response
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer
            }
        )


    else:

        st.error(
            "Backend error occurred"
        )