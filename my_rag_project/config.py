# config.py
from pathlib import Path
from embedding import embedding
from langchain_community.vectorstores import Chroma

# Where files live
FAQ_PATH = Path(__file__).resolve().parent.parent / "data" / "company_faqs.txt"
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"

class ChromaProxy:
    def _get_db(self):
        return Chroma(
            persist_directory=str(Path(__file__).resolve().parent.parent / "vector_db"),
            embedding_function=embedding
        )

    def similarity_search(self, *args, **kwargs):
        return self._get_db().similarity_search(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self._get_db().get(*args, **kwargs)

    def add_documents(self, *args, **kwargs):
        return self._get_db().add_documents(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._get_db().delete(*args, **kwargs)

    def persist(self, *args, **kwargs):
        return self._get_db().persist(*args, **kwargs)

db = ChromaProxy()