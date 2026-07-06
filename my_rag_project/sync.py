# sync.py
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .config import UPLOAD_DIR, db  # Import from our config room

def sync_uploads_to_vector_db():
    if not UPLOAD_DIR.exists():
        return

    try:
        data = db.get()
        existing_sources = set()
        if data and "metadatas" in data:
            for meta in data["metadatas"]:
                if meta and "source" in meta:
                    existing_sources.add(meta["source"])
    except Exception:
        existing_sources = set()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

    for path in UPLOAD_DIR.glob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in [".summary.txt", ".content.txt"]:
            continue

        file_name = path.name
        if file_name in existing_sources:
            continue

        content = None
        if file_name.lower().endswith(".pdf"):
            content_path = path.with_suffix(".content.txt")
            if content_path.exists():
                try:
                    content = content_path.read_text(encoding="utf-8")
                except Exception:
                    pass
        else:
            try:
                content = path.read_text(encoding="utf-8")
            except Exception:
                pass

        if content and content.strip():
            chunks = text_splitter.split_text(content.strip())
            docs = [Document(page_content=chunk, metadata={"source": file_name}) for chunk in chunks]
            db.add_documents(docs)
            db.persist()
            print(f"Synced {file_name} to Chroma vector database.")