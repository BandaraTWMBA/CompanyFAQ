from fastapi import FastAPI
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

import asyncio

try:
    from queue.rabbitmq import publish_task
except ImportError:
    def publish_task(task):
        print(f"Publish task stub called with: {task}")

from rag import answer


app = FastAPI()


class Question(BaseModel):
    question: str


class Response(BaseModel):
    answer: str


@app.post("/chat", response_model=Response)
def chat(req: Question):
    ans = answer(req.question)
    return Response(answer=ans)

@app.post("/upload")
def upload_file(filename: str):
    task = {
        "file": filename,
        "task": "summarize",
    }

    publish_task(task)

    return {
        "status": "processing",
        "file": filename,
    }


@app.get("/stream")
async def stream_answer(question: str):
    async def event_generator():
        answer_text = "This is generated response from RAG system"

        for word in answer_text.split():
            yield {"data": word}
            await asyncio.sleep(0.3)

    return EventSourceResponse(event_generator())