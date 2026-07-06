import requests
import streamlit as st

# ----------------------------------------
# Configuration
# ----------------------------------------

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Company AI Assistant",
    page_icon="🤖",
    layout="wide"
)

# ----------------------------------------
# Sidebar
# ----------------------------------------

with st.sidebar:

    st.title("⚙️ AI Assistant")

    st.markdown("---")

    st.subheader("📄 Upload Document")

    uploaded_files = st.file_uploader(
        "Choose files",
        type=["pdf", "txt", "csv", "json"],
        accept_multiple_files=True
    )

    if uploaded_files:

        if st.button("Upload"):

            with st.spinner("Uploading files..."):

                try:
                    files_payload = [
                        (
                            "files",
                            (
                                uf.name,
                                uf.getvalue(),
                                uf.type or "application/octet-stream"
                            )
                        )
                        for uf in uploaded_files
                    ]

                    response = requests.post(
                        f"{API_URL}/upload",
                        files=files_payload
                    )

                    if response.status_code == 200:

                        data_list = response.json()

                        st.success(f"✅ {len(data_list)} file(s) uploaded successfully!")

                        for data in data_list:
                            st.info(f"File: {data.get('file', '')} | Status: {data.get('status', 'processing')}")
                            st.caption(f"Saved to: {data.get('saved_to', '')}")
                            st.write(data.get("summary", ""))

                    else:

                        st.error(f"Upload failed: {response.text}")

                except requests.exceptions.ConnectionError:

                    st.error("❌ FastAPI server is not running.")

    st.markdown("---")

    st.subheader("💬 Chat Target")

    uploaded_files = ["Default (FAQs & All Documents)"]
    try:
        res = requests.get(f"{API_URL}/files")
        if res.status_code == 200:
            uploaded_files.extend(res.json())
    except Exception:
        pass

    selected_doc = st.selectbox(
        "Ask questions from:",
        options=uploaded_files,
        index=0
    )

    if selected_doc != "Default (FAQs & All Documents)":
        st.markdown("**Document Summary:**")
        try:
            res = requests.get(f"{API_URL}/files/{selected_doc}/summary")
            if res.status_code == 200:
                summary_text = res.json().get("summary", "")
                st.info(summary_text)
            else:
                st.warning("Could not fetch summary.")
        except Exception as e:
            st.error(f"Error: {e}")

    st.markdown("---")

    st.subheader("🟢 Backend Status")

    try:

        requests.get(API_URL)

        st.success("Backend Online")

    except:

        st.error("Backend Offline")

# ----------------------------------------
# Main Page
# ----------------------------------------

st.title("🤖 Company FAQ Chatbot")

st.write(
    "Ask questions about the company.\n"
    "The chatbot remembers previous messages."
)

# ----------------------------------------
# Session State
# ----------------------------------------

if "messages" not in st.session_state:

    st.session_state.messages = []

# ----------------------------------------
# Display Chat History
# ----------------------------------------

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.write(message["content"])

# ----------------------------------------
# Chat Input
# ----------------------------------------

question = st.chat_input("Ask anything...")

if question:

    # Display user message

    with st.chat_message("user"):

        st.write(question)

    st.session_state.messages.append(

        {
            "role": "user",
            "content": question
        }

    )

    # Call backend

    try:

        with st.spinner("Thinking..."):

            response = requests.post(

                f"{API_URL}/chat",

                json={
                    "question": question,
                    "file_name": selected_doc
                }

            )

        if response.status_code == 200:

            result = response.json()

            answer = result.get("answer", "")

            confidence = result.get("confidence", None)

            score = result.get("score", None)

            with st.chat_message("assistant"):

                st.write(answer)

                if confidence:

                    st.caption(
                        f"Confidence : {confidence}"
                    )

                if score is not None:

                    st.caption(
                        f"Retrieval Score : {score:.3f}"
                    )

                    st.progress(float(score))

            st.session_state.messages.append(

                {
                    "role": "assistant",
                    "content": answer
                }

            )

        else:

            st.error("Backend returned an error.")

    except requests.exceptions.ConnectionError:

        st.error("❌ Cannot connect to FastAPI server.")

    except Exception as e:

        st.error(str(e))