from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from embedding import embedding


def load_faqs():

    with open(
        "my_rag_project/data/company_faqs.txt",
        "r",
        encoding="utf-8"
    ) as file:

        content = file.read()


    faq_blocks = content.split("---")


    documents = []


    for block in faq_blocks:

        block = block.strip()

        if block:

            documents.append(
                Document(
                    page_content=block
                )
            )


    return documents



docs = load_faqs()


print(f"Loaded {len(docs)} FAQ documents")


db = Chroma.from_documents(

    documents=docs,

    embedding=embedding,

    persist_directory="vector_db"

)


db.persist()


print(
    f"{len(docs)} FAQ chunks indexed."
)