# main.py
from memory import add_message, get_history
from llm import ask_llm
from .config import db  # Get the database from config
from .sync import sync_uploads_to_vector_db  # Get the sync tool

def answer(question, file_name=None):
    history = get_history()

    if not question or not question.strip():
        response = "Please ask a question about the company FAQ or your uploaded documents."
        add_message("User", question)
        add_message("Assistant", response)
        return response

    # Call our sync tool from the other file
    sync_uploads_to_vector_db()

    # Query the Chroma vector database
    try:
        if file_name and file_name != "Default (FAQs & All Documents)":
            results = db.similarity_search(question, k=4, filter={"source": file_name})
        else:
            results = db.similarity_search(question, k=4)

        if results:
            context = "\n\n".join([doc.page_content for doc in results])
        else:
            context = ""
    except Exception as e:
        print(f"Error querying Chroma: {e}")
        context = ""

    # Generate answer using context
    if context:
        doc_info = f' from the document "{file_name}"' if file_name else ""
        prompt = f"""You are a helpful assistant. Use the following context{doc_info} to answer the user's question.
If the context does not contain the answer, say "I cannot find the answer in the provided documents."

Context:
{context}

Question: {question}
Answer:"""
        try:
            response = ask_llm(prompt).strip()
        except Exception as e:
            response = f"Error querying LLM: {str(e)}"
    else:
        response = "I don't have information about that."

    add_message("User", question)
    add_message("Assistant", response)
    return response