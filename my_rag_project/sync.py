# sync.py
import re
from io import BytesIO
from pathlib import Path
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .config import UPLOAD_DIR, db  # Import from our config room
from llm import ask_llm

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from rapidocr_onnxruntime import RapidOCR
    from PIL import Image
except ImportError:
    RapidOCR = None
    Image = None

def extract_text_from_pdf_sync(path):
    if PdfReader is None:
        return ""
    try:
        reader = PdfReader(path)
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(page for page in pages if page).strip()
        if text:
            return text
            
        # OCR Fallback
        if RapidOCR is not None and Image is not None:
            engine = RapidOCR()
            ocr_pages = []
            for idx, page in enumerate(reader.pages):
                page_text = []
                for img_obj in page.images:
                    img = Image.open(BytesIO(img_obj.data))
                    result, _ = engine(img)
                    if result:
                        page_text.append("\n".join([line[1] for line in result]))
                if page_text:
                    ocr_pages.append("\n".join(page_text))
                else:
                    ocr_pages.append("")
            return "\n".join(ocr_pages).strip()
    except Exception as e:
        print(f"Error extracting text from PDF in sync: {e}")
    return ""

def summarize_text_sync(text: str) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return "No content."
    try:
        prompt = f"Write a brief one-sentence summary of the following document content:\n\n{cleaned[:4000]}"
        summary = ask_llm(prompt).strip()
        if summary:
            return summary
    except Exception:
        pass
    
    sentences = [p.strip() for p in re.split(r"(?<=[.!?])\s+", cleaned) if p.strip()]
    if sentences:
        s = sentences[0]
        return s[:217] + "..." if len(s) > 220 else s
    return " ".join(cleaned.split()[:25]) + "..."

def sync_uploads_to_vector_db():
    if not UPLOAD_DIR.exists():
        return

    # Clean up orphaned records (files that were deleted from UPLOAD_DIR)
    try:
        data = db.get(limit=10000)
        if data and "metadatas" in data:
            existing_sources = {meta["source"] for meta in data["metadatas"] if meta and "source" in meta}
            for src in existing_sources:
                if src == "company_faqs.txt":
                    continue
                src_path = UPLOAD_DIR / src
                if not src_path.exists():
                    db.delete(where={"source": src})
                    print(f"Cleaned up orphaned database records for deleted file: {src}")
    except Exception as e:
        print(f"Error cleaning up orphaned records: {e}")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

    for path in UPLOAD_DIR.glob("*"):
        if not path.is_file():
            continue
        # Skip double extension helper files (like .pdf.summary.txt or .content.txt)
        name_lower = path.name.lower()
        if ".summary.txt" in name_lower or ".content.txt" in name_lower:
            continue

        file_name = path.name
        
        # Check if already indexed specifically using where filter
        try:
            existing = db.get(where={"source": file_name})
            if existing and existing.get("ids"):
                continue
        except Exception:
            pass

        content = None
        if file_name.lower().endswith(".pdf"):
            content_path = path.with_suffix(".content.txt")
            if content_path.exists():
                try:
                    content = content_path.read_text(encoding="utf-8")
                except Exception:
                    pass
            else:
                # PDF content file is missing (e.g. background worker didn't run). Extract it synchronously!
                print(f"PDF content file for {file_name} missing. Extracting content synchronously...")
                content = extract_text_from_pdf_sync(path)
                if content:
                    try:
                        content_path.write_text(content, encoding="utf-8")
                    except Exception:
                        pass
                
                # Also generate summary synchronously
                summary_path = path.with_suffix(path.suffix + ".summary.txt")
                if not summary_path.exists() and content:
                    summary = summarize_text_sync(content)
                    try:
                        summary_path.write_text(summary, encoding="utf-8")
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