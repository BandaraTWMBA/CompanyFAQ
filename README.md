
````markdown
# Company FAQ RAG Chatbot

A simple Retrieval-Augmented Generation (RAG) chatbot that answers company-related FAQs using vector embeddings, ChromaDB, FastAPI, and Ollama.

## Features

- FAQ document ingestion
- Vector embeddings using Sentence Transformers
- ChromaDB vector database
- FastAPI backend
- Streamlit chat interface
- Conversation history support
- Context-aware responses using RAG

## Tech Stack

- Python
- FastAPI
- Streamlit
- LangChain
- ChromaDB
- Ollama (Llama 3.2)
- Sentence Transformers (`BAAI/bge-small-en-v1.5`)

## Project Structure

```
company-faq-rag/
│── data/
│── vector_db/
│── app.py
│── api.py
│── ingest.py
│── rag.py
│── llm.py
│── embedding.py
│── memory.py
│── requirements.txt
```

## Installation

```bash
git clone <repository-url>
cd company-faq-rag

python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Build the Vector Database

```bash
python ingest.py
```

## Run the Backend

```bash
python -m uvicorn api:app --reload
```

## Run the Frontend

```bash
streamlit run app.py
```

Open:

```
http://localhost:8501
```

## Example Questions

- Do you offer internships?
- How long do they last?
- Can employees work remotely?
- How many days?
- What programming languages are used?
- How many annual leave days are given?

## Future Improvements

- PDF/CSV document ingestion
- Metadata filtering
- Conversation persistence
- Integration tests
- Hybrid search (keyword + vector search)
````

