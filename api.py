from fastapi import FastAPI
from pydantic import BaseModel
try:
    from queue.rabbitmq import publish_task
except Exception:  # fallback when package/path is unavailable
    def publish_task(task: dict):
        """Fallback publish_task used when queue.rabbitmq cannot be imported.
        This stub simply logs the task to stdout. Replace with real implementation.
        """
        print("publish_task called with:", task)


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