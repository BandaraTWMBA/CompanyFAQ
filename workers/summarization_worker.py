import sys
import pika
import json
import re
from pathlib import Path
from io import BytesIO

# Add workspace root to python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Import LangChain components for vector database indexing
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from embedding import embedding
from llm import ask_llm

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Load/Initialize Chroma database
db = Chroma(persist_directory="vector_db", embedding_function=embedding)


def extract_text_from_upload(contents: bytes, filename: str) -> str:
    file_name = (filename or "").lower()

    if file_name.endswith(".pdf"):
        if PdfReader is None:
            return "PDF uploaded. Text extraction is unavailable until the PDF dependency is installed."

        try:
            reader = PdfReader(BytesIO(contents))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(page for page in pages if page).strip()
            if text:
                return text
        except Exception as exc:
            print(f"PDF extraction failed: {exc}")

        return "PDF uploaded but no readable text could be extracted."

    try:
        return contents.decode("utf-8")
    except UnicodeDecodeError:
        return contents.decode("utf-8", errors="ignore")


def summarize_text(text: str) -> str:
    cleaned_text = " ".join(text.split())
    if not cleaned_text:
        return "No content to summarize."

    # Use ask_llm for a high-quality summary if possible
    try:
        prompt = f"Write a brief one-sentence summary of the following document content:\n\n{cleaned_text[:4000]}"
        summary = ask_llm(prompt).strip()
        if summary:
            return summary
    except Exception as e:
        print(f"LLM summarization failed: {e}")

    # Rule-based fallback
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned_text) if part.strip()]
    if sentences:
        summary = sentences[0]
        if len(summary) > 220:
            summary = summary[:217] + "..."
        return summary

    words = cleaned_text.split()[:25]
    summary = " ".join(words)
    if len(words) == 25:
        summary += "..."
    return summary


def process(message):
    print("Processing message:", message)
    file_name = message.get("file_name")
    if not file_name:
        print("Error: No file_name provided in message.")
        return

    save_path = UPLOAD_DIR / file_name
    if not save_path.exists():
        print(f"Error: File does not exist at {save_path}")
        return

    try:
        # 1. Read file contents
        contents = save_path.read_bytes()

        # 2. Extract text content
        text_content = extract_text_from_upload(contents, file_name)

        # 3. Generate summary
        summary = summarize_text(text_content)
        summary_path = save_path.with_suffix(save_path.suffix + ".summary.txt")
        summary_path.write_text(summary, encoding="utf-8")

        # 4. Save extracted text content for PDFs
        if file_name.lower().endswith(".pdf"):
            content_path = save_path.with_suffix(".content.txt")
            content_path.write_text(text_content, encoding="utf-8")

        # 5. Chunk the text content and index in Chroma
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = text_splitter.split_text(text_content)

        # Add metadata for specific document retrieval
        documents = [Document(page_content=chunk, metadata={"source": file_name}) for chunk in chunks]

        # Add documents to Chroma database
        db.add_documents(documents)
        db.persist()

        print(f"Successfully processed and indexed {file_name} into vector database.")
    except Exception as e:
        print(f"Error processing file {file_name}: {e}")


if __name__ == "__main__":
    connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connection.channel()
    channel.queue_declare(queue="ai_tasks")

    def callback(ch, method, properties, body):
        data = json.loads(body)
        process(data)

    channel.basic_consume(
        queue="ai_tasks",
        on_message_callback=callback,
        auto_ack=True
    )

    print("Worker started")
    channel.start_consuming()