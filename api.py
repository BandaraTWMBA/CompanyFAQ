from fastapi import FastAPI
from pydantic import BaseModel
from queue.rabbitmq import publish_task

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


def upload_file(filename:str):


    task={

        "file":filename,

        "task":"summarize"

    }


    publish_task(task)


    return {

        "status":"processing",

        "file":filename

    }