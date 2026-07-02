import json

from datasets import Dataset

from ragas import evaluate
from ragas.metrics import Faithfulness, AnswerRelevancy, ContextPrecision

from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper

from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings


# ----------------------------
# Load dataset
# ----------------------------

with open("evaluations/test_dataset.json", "r") as f:
    data = json.load(f)

dataset = Dataset.from_list(data)


# ----------------------------
# Ollama models
# ----------------------------

llm = ChatOllama(
    model="llama3.2:3b",
    temperature=0,
)

embeddings = OllamaEmbeddings(
    model="nomic-embed-text"
)


# Wrap for Ragas

ragas_llm = LangchainLLMWrapper(llm)

ragas_embeddings = LangchainEmbeddingsWrapper(embeddings)


# ----------------------------
# Evaluate
# ----------------------------

result = evaluate(
    dataset,
    metrics=[
        Faithfulness(),
        AnswerRelevancy(),
        ContextPrecision(),
    ],
    llm=ragas_llm,
    embeddings=ragas_embeddings,
)

print(result)

result.to_pandas().to_csv(
    "evaluations/results.csv",
    index=False,
)