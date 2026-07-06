# config.py
from pathlib import Path
from embedding import embedding
from langchain_community.vectorstores import Chroma

# Where files live
FAQ_PATH = Path(__file__).resolve().parent.parent / "data" / "company_faqs.txt"
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"

# The shared database brain
db = Chroma(persist_directory=str(Path(__file__).resolve().parent.parent / "vector_db"), embedding_function=embedding)