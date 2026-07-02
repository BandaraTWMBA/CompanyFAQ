from fastapi import FastAPI
from pydantic import BaseModel

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