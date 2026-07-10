import asyncio
import re
from typing import List
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

app = FastAPI()

# Enable CORS configurations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Safe RabbitMQ import fallback
try:
    from task_queue.rabbitmq import publish_task
except ImportError:
    def publish_task(task):
        print(f"Publish task stub called with: {task}")

# RAG import
from my_rag_project.main import answer

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - fallback for environments without the dependency
    PdfReader = None

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


class Question(BaseModel):
    question: str
    file_name: str = None


class Response(BaseModel):
    answer: str


@app.get("/")
def read_root():
    return {"message": "Welcome to the API!"}
    
@app.post("/chat", response_model=Response)
def chat(req: Question):
    ans = answer(req.question, req.file_name)
    return Response(answer=ans)


@app.get("/files")
def list_files():
    if not UPLOAD_DIR.exists():
        return []
    files = []
    for path in sorted(UPLOAD_DIR.glob("*")):
        if path.is_file():
            name = path.name
            if name.endswith(".summary.txt") or name.endswith(".content.txt"):
                continue
            files.append(name)
    return files


@app.get("/files_summary")
def get_file_summary(file_name: str):
    if not UPLOAD_DIR.exists():
        return {"summary": "No uploads folder found."}
    
    save_path = UPLOAD_DIR / file_name
    summary_path = save_path.with_suffix(save_path.suffix + ".summary.txt")
    
    if summary_path.exists():
        try:
            return {"summary": summary_path.read_text(encoding="utf-8").strip()}
        except Exception as e:
            return {"summary": f"Error reading summary: {str(e)}"}
            
    return {"summary": "Summary is being generated in the background..."}


def summarize_text(text: str) -> str:
    cleaned_text = " ".join(text.split())
    if not cleaned_text:
        return "No content to summarize."

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
        except Exception as exc:  # pragma: no cover - runtime guard
            print(f"PDF extraction failed: {exc}")

        return "PDF uploaded but no readable text could be extracted."

    try:
        return contents.decode("utf-8")
    except UnicodeDecodeError:
        return contents.decode("utf-8", errors="ignore")


@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    results = []
    for file in files:
        safe_name = Path(file.filename or "uploaded_file").name
        save_path = UPLOAD_DIR / safe_name

        contents = await file.read()
        save_path.write_bytes(contents)

        # Publish background task to process the file (extract text, summarize, index in Chroma)
        task = {
            "file_name": safe_name,
            "task": "process_file"
        }
        publish_task(task)

        results.append({
            "status": "processing",
            "file": safe_name,
            "saved_to": str(save_path),
            "summary": "Summary is being generated in the background..."
        })

    return results


@app.get("/stream")
async def stream_answer(question: str, file_name: str = None):
    async def event_generator():
        # Get the actual answer from the RAG system
        answer_text = answer(question, file_name)

        for word in answer_text.split():
            yield {"data": str(word)}  # ensure string format for SSE
            await asyncio.sleep(3)

        yield {"event": "done", "data": ""}  # signal completion to the client

    return EventSourceResponse(event_generator())


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title="Company FAQ RAG API",
        version="1.0.0",
        routes=app.routes,
    )

    # Recursively look for any schema definitions that have items with contentMediaType
    def fix_schemas(d):
        if not isinstance(d, dict):
            return
        for k, v in list(d.items()):
            if isinstance(v, dict):
                if v.get("type") == "string" and v.get("contentMediaType") == "application/octet-stream":
                    del v["contentMediaType"]
                    v["format"] = "binary"
                else:
                    fix_schemas(v)
            elif isinstance(v, list):
                for item in v:
                    fix_schemas(item)

    fix_schemas(openapi_schema)
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi